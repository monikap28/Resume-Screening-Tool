"""
RecruitIQ – Flask Backend
=========================
Parses uploaded Job Description + Resumes (PDF/TXT),
runs real NLP scoring (TF-IDF cosine similarity + keyword matching),
performs a bias audit, and returns ranked candidates as JSON.
"""

import os, re, string, json, random, copy
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import pdfplumber
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# ── Download NLTK data (first-run only) ──────────────────────────
for pkg in ['punkt', 'stopwords', 'punkt_tab']:
    try:
        nltk.data.find(f'tokenizers/{pkg}' if 'punkt' in pkg else f'corpora/{pkg}')
    except LookupError:
        nltk.download(pkg, quiet=True)

# ── Flask App ─────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')

ALLOWED_EXTENSIONS = {'pdf', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ── Text Extraction ───────────────────────────────────────────────
def extract_text_from_pdf(filepath):
    """Extract all text from a PDF using pdfplumber."""
    text = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
    except Exception as e:
        print(f"[WARN] Could not read PDF {filepath}: {e}")
    return '\n'.join(text)

def extract_text_from_txt(filepath):
    """Read plain text file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        print(f"[WARN] Could not read TXT {filepath}: {e}")
        return ''

def extract_text(filepath):
    ext = filepath.rsplit('.', 1)[-1].lower()
    if ext == 'pdf':
        return extract_text_from_pdf(filepath)
    elif ext == 'txt':
        return extract_text_from_txt(filepath)
    return ''

# ── Text Preprocessing ────────────────────────────────────────────
def preprocess(text):
    """Lowercase, remove punctuation, remove stopwords."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    tokens = text.split()
    try:
        stop = set(stopwords.words('english'))
        tokens = [t for t in tokens if t not in stop and len(t) > 1]
    except Exception:
        pass
    return ' '.join(tokens)

# ── Skill Keywords ────────────────────────────────────────────────
SKILL_KEYWORDS = [
    # Programming Languages
    'python','java','javascript','typescript','c++','c#','r','scala','go','rust','sql',
    # ML / AI
    'tensorflow','pytorch','keras','scikit','sklearn','huggingface','transformers',
    'bert','gpt','llm','nlp','natural language','machine learning','deep learning',
    'computer vision','reinforcement learning','neural network','xgboost','lightgbm',
    # Data
    'pandas','numpy','matplotlib','seaborn','spark','hadoop','sql','nosql','mongodb',
    'postgresql','mysql','bigquery','dbt','airflow',
    # MLOps / Engineering
    'docker','kubernetes','mlflow','aws','gcp','azure','ci/cd','git','github','linux',
    'fastapi','flask','django','rest','api','microservices',
    # Soft Skills
    'communication','leadership','collaboration','teamwork','agile','scrum',
    'mentoring','presentation','problem solving','critical thinking',
    # Education
    'computer science','engineering','mathematics','statistics','phd','masters',
    'bachelor','research','published','thesis',
]

EXPERIENCE_PATTERNS = [
    r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
    r'(\d+)\+?\s*yrs?\s*(?:of\s*)?experience',
    r'experience\s*[:\-]?\s*(\d+)\+?\s*years?',
]

CULTURE_KEYWORDS = [
    'team','collaborate','communication','leadership','mentor','agile','scrum',
    'cross-functional','stakeholder','present','documentation','async','remote',
    'initiative','proactive','ownership','impact','growth','diverse','inclusive',
    'pair programming','open source','contribute','community',
]

# ── Scoring Functions ─────────────────────────────────────────────
def tfidf_similarity(jd_text, resume_text):
    """TF-IDF cosine similarity between JD and resume (0–100)."""
    try:
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True
        )
        jd_clean     = preprocess(jd_text)
        resume_clean = preprocess(resume_text)
        if not jd_clean.strip() or not resume_clean.strip():
            return 0.0
        tfidf_matrix = vectorizer.fit_transform([jd_clean, resume_clean])
        sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return round(float(sim) * 100, 2)
    except Exception as e:
        print(f"[WARN] TF-IDF error: {e}")
        return 0.0

def keyword_score(jd_text, resume_text):
    """What fraction of JD skill-keywords appear in the resume (0–100)."""
    jd_lower     = jd_text.lower()
    resume_lower = resume_text.lower()
    # Collect keywords that appear in the JD
    jd_skills = [kw for kw in SKILL_KEYWORDS if kw in jd_lower]
    if not jd_skills:
        jd_skills = SKILL_KEYWORDS[:20]  # fallback: check general skills
    matched = sum(1 for kw in jd_skills if kw in resume_lower)
    score = (matched / len(jd_skills)) * 100 if jd_skills else 0
    return round(min(score * 1.25, 100), 2)  # small boost, capped at 100

def compute_skills_score(jd_text, resume_text):
    """Blend TF-IDF similarity (60%) + keyword overlap (40%)."""
    tfidf = tfidf_similarity(jd_text, resume_text)
    kw    = keyword_score(jd_text, resume_text)
    score = tfidf * 0.6 + kw * 0.4
    # Scale to a 40–95 range to reflect realistic scores
    score = 40 + (score / 100) * 55
    return round(min(score, 100), 1)

def compute_experience_score(jd_text, resume_text):
    """Extract years-of-experience from resume, compare to JD requirement."""
    # Find required years from JD
    jd_years = 0
    for pat in EXPERIENCE_PATTERNS:
        m = re.search(pat, jd_text, re.IGNORECASE)
        if m:
            jd_years = int(m.group(1))
            break

    # Find candidate's years from resume
    resume_years = 0
    for pat in EXPERIENCE_PATTERNS:
        m = re.search(pat, resume_text, re.IGNORECASE)
        if m:
            resume_years = max(resume_years, int(m.group(1)))

    # Score based on meeting/exceeding requirement
    if jd_years == 0:
        # No explicit JD requirement — score by resume years found
        base = min(resume_years * 8, 80) + 15
    else:
        ratio = resume_years / jd_years if jd_years else 1
        if ratio >= 1.5:
            base = 92
        elif ratio >= 1.0:
            base = 80 + (ratio - 1.0) * 24
        elif ratio >= 0.7:
            base = 60 + ratio * 28
        else:
            base = 45 + resume_years * 5

    # Bonus: job titles indicating seniority
    seniority_words = ['senior', 'lead', 'principal', 'staff', 'head', 'director', 'manager', 'architect']
    bonus = sum(4 for w in seniority_words if w in resume_text.lower())
    return round(min(base + bonus, 100), 1)

def compute_culture_score(resume_text):
    """Count culture-signal keywords in resume."""
    resume_lower = resume_text.lower()
    hits = sum(1 for kw in CULTURE_KEYWORDS if kw in resume_lower)
    # Normalise: 10+ hits = ~90%
    raw = (hits / 10) * 85 + 10
    return round(min(raw, 95), 1)

def composite_score(skills, experience, culture):
    return round(skills * 0.45 + experience * 0.35 + culture * 0.20, 1)

# ── Name Extraction ───────────────────────────────────────────────
def extract_candidate_name(resume_text, filename):
    """Try to extract name from first 3 lines of the resume."""
    lines = [l.strip() for l in resume_text.split('\n') if l.strip()]
    for line in lines[:5]:
        # Skip lines that look like headings or emails
        if any(w in line.lower() for w in ['resume', 'curriculum', 'vitae', 'cv', '@', 'http', 'phone']):
            continue
        # Likely a name: 2-3 words, each capitalised, no digits
        words = line.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w) and not any(c.isdigit() for c in line):
            return line
    # Fallback: use filename without extension
    name = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
    return name

def name_initials(name):
    parts = name.split()
    return ''.join(p[0].upper() for p in parts[:2]) if parts else '??'

# ── Bias Audit ────────────────────────────────────────────────────
BIAS_NAME_VARIANTS = {
    'default': [
        'Emily Johnson', 'Mohammed Al-Hassan', 'Priya Sharma',
        'Dmitri Volkov',  'Yuki Tanaka',        'Aisha Okonkwo',
    ]
}

def run_bias_audit(jd_text, resume_text, original_name, original_composite):
    """
    Replace name in resume text with diverse alternatives, re-score, track delta.
    Returns a list of {name, composite, delta} dicts.
    """
    results = []
    for alt_name in BIAS_NAME_VARIANTS['default']:
        # Substitute original name with alt name in resume text
        modified = re.sub(re.escape(original_name), alt_name, resume_text, flags=re.IGNORECASE)
        s = compute_skills_score(jd_text, modified)
        e = compute_experience_score(jd_text, modified)
        c = compute_culture_score(modified)
        comp = composite_score(s, e, c)
        delta = round(abs(comp - original_composite), 2)
        results.append({
            'name':      alt_name,
            'composite': comp,
            'delta':     delta,
            'flag':      'high' if delta > 3 else ('warn' if delta > 1 else 'clear'),
        })
    max_delta     = max(r['delta'] for r in results) if results else 0
    overall_index = round(sum(r['delta'] for r in results) / len(results), 2) if results else 0
    return {
        'variants':     results,
        'max_delta':    max_delta,
        'overall_index': overall_index,
        'status':       'HIGH' if max_delta > 3 else ('MEDIUM' if max_delta > 1 else 'LOW'),
        'flagged':      sum(1 for r in results if r['flag'] != 'clear'),
    }

# ── Generate AI Rationale ─────────────────────────────────────────
def generate_rationale(name, skills, experience, culture, composite, resume_text, jd_text):
    """
    Template-based rationale (no external LLM required).
    Generates a paragraph summarising the candidate's fit.
    """
    # Determine skill level descriptors
    def level(score):
        if score >= 85: return 'strong'
        if score >= 70: return 'moderate'
        return 'limited'

    # Pull a few matched keywords for specificity
    jd_lower  = jd_text.lower()
    res_lower = resume_text.lower()
    matched_kws = [kw for kw in SKILL_KEYWORDS if kw in jd_lower and kw in res_lower][:5]
    kw_str = ', '.join(matched_kws) if matched_kws else 'general industry skills'

    # Experience years
    resume_years = 0
    for pat in EXPERIENCE_PATTERNS:
        m = re.search(pat, resume_text, re.IGNORECASE)
        if m:
            resume_years = max(resume_years, int(m.group(1)))

    seniority_hit = any(w in res_lower for w in ['senior', 'lead', 'principal', 'head', 'manager'])
    seniority_str = 'senior-level background' if seniority_hit else 'professional background'

    culture_hits = [kw for kw in CULTURE_KEYWORDS if kw in res_lower][:3]
    culture_str  = ', '.join(culture_hits) if culture_hits else 'professional conduct'

    if composite >= 80:
        opening = f"{name} is a highly competitive candidate for this role."
    elif composite >= 65:
        opening = f"{name} presents a solid fit for this role with some areas to explore."
    else:
        opening = f"{name} shows potential but may not fully meet the role's current requirements."

    rationale = (
        f"{opening} "
        f"Their skills alignment score of {skills}% reflects a {level(skills)} match, "
        f"with demonstrable proficiency in {kw_str}. "
        f"{'An estimated ' + str(resume_years) + ' years of experience supports' if resume_years else 'Their'} "
        f"a {seniority_str} that scores {experience}% against the role's seniority expectations. "
        f"Culture-signal indicators — including references to {culture_str} — contribute a culture score of {culture}%. "
        f"Overall, the composite score of {composite}% places this candidate "
        f"{'in the top tier of applicants' if composite >= 80 else 'within a competitive mid-range' if composite >= 65 else 'below the recommended threshold for this role'}."
    )
    return rationale

# ── Routes ─────────────────────────────────────────────────────────
@app.route('/')
def serve_index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(BASE_DIR, path)

@app.route('/api/screen', methods=['POST'])
def screen():
    """
    POST /api/screen
    Form data:
      jd      : file  (PDF or TXT) — Job Description
      resumes : files (PDF, up to 10) — Applicant resumes
    Returns JSON with ranked candidates + bias audit.
    """
    # ── Validate inputs ──────────────────────────────────────────
    if 'jd' not in request.files:
        return jsonify({'error': 'No job description file uploaded (field: jd)'}), 400

    jd_file = request.files['jd']
    if jd_file.filename == '':
        return jsonify({'error': 'Job description file is empty'}), 400
    if not allowed_file(jd_file.filename):
        return jsonify({'error': 'JD must be PDF or TXT'}), 400

    resume_files = request.files.getlist('resumes')
    if not resume_files or all(f.filename == '' for f in resume_files):
        return jsonify({'error': 'No resume files uploaded (field: resumes)'}), 400

    resume_files = [f for f in resume_files if f.filename != ''][:10]

    # ── Save & Extract JD ────────────────────────────────────────
    jd_filename = secure_filename(jd_file.filename)
    jd_path     = os.path.join(UPLOAD_DIR, 'jd_' + jd_filename)
    jd_file.save(jd_path)
    jd_text = extract_text(jd_path)

    if not jd_text.strip():
        return jsonify({'error': 'Could not extract text from job description. Ensure the PDF is not scanned/image-only.'}), 422

    # ── Process Each Resume ──────────────────────────────────────
    candidates = []
    bias_rows  = []

    for rf in resume_files:
        if not allowed_file(rf.filename):
            continue
        filename     = secure_filename(rf.filename)
        resume_path  = os.path.join(UPLOAD_DIR, filename)
        rf.save(resume_path)
        resume_text = extract_text(resume_path)

        if not resume_text.strip():
            # Skip unreadable PDFs but note them
            candidates.append({
                'name':       os.path.splitext(filename)[0],
                'initials':   '??',
                'role':       'Could not parse resume',
                'skills':     0,
                'experience': 0,
                'culture':    0,
                'composite':  0,
                'rationale':  'This resume could not be parsed — it may be a scanned image PDF. Please provide a text-based PDF.',
                'error':      True,
            })
            continue

        # Scoring
        skills_score = compute_skills_score(jd_text, resume_text)
        exp_score    = compute_experience_score(jd_text, resume_text)
        cult_score   = compute_culture_score(resume_text)
        comp         = composite_score(skills_score, exp_score, cult_score)

        # Name
        name     = extract_candidate_name(resume_text, filename)
        initials = name_initials(name)

        # Rationale
        rationale = generate_rationale(name, skills_score, exp_score, cult_score, comp, resume_text, jd_text)

        # Bias audit for this candidate
        audit = run_bias_audit(jd_text, resume_text, name, comp)

        candidates.append({
            'name':       name,
            'initials':   initials,
            'role':       filename.replace('_', ' ').replace('-', ' '),
            'skills':     skills_score,
            'experience': exp_score,
            'culture':    cult_score,
            'composite':  comp,
            'rationale':  rationale,
        })
        bias_rows.append({
            'name':          name,
            'original':      comp,
            'variants':      audit['variants'],
            'max_delta':     audit['max_delta'],
            'overall_index': audit['overall_index'],
            'status':        audit['status'],
            'flagged':       audit['flagged'],
        })

    if not candidates:
        return jsonify({'error': 'No valid resumes could be processed.'}), 422

    # ── Sort by composite score ──────────────────────────────────
    candidates.sort(key=lambda c: c['composite'], reverse=True)

    # ── Aggregate Bias Stats ─────────────────────────────────────
    total_flagged   = sum(r['flagged'] for r in bias_rows)
    overall_bias    = round(sum(r['overall_index'] for r in bias_rows) / len(bias_rows), 2) if bias_rows else 0
    max_delta_all   = max((r['max_delta'] for r in bias_rows), default=0)
    bias_status     = 'HIGH' if max_delta_all > 3 else ('MEDIUM' if max_delta_all > 1 else 'LOW')

    # Build simple per-candidate bias summary table
    bias_summary = []
    for r in bias_rows:
        best_variant = min(r['variants'], key=lambda v: v['delta']) if r['variants'] else {}
        worst_variant = max(r['variants'], key=lambda v: v['delta']) if r['variants'] else {}
        bias_summary.append({
            'name':     r['name'],
            'original': r['original'],
            'varied':   round(r['original'] - (worst_variant.get('delta', 0) / 2), 2),
            'delta':    worst_variant.get('delta', 0),
            'flag':     worst_variant.get('flag', 'clear'),
        })

    return jsonify({
        'candidates': candidates,
        'bias': {
            'overallIndex': overall_bias,
            'status':       bias_status,
            'testsRun':     len(bias_rows) * len(BIAS_NAME_VARIANTS['default']),
            'flagged':      total_flagged,
            'candidates':   bias_summary,
        }
    })

# ── Run ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("\nRecruitIQ Backend starting...")
    print("Upload folder:", UPLOAD_DIR)
    print("Visit: http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
