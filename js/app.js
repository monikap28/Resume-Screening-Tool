/* ================================================================
   app.js – RecruitIQ Frontend Logic
   Calls real Flask backend /api/screen with uploaded files
   ================================================================ */

'use strict';

// ── Navbar scroll effect ─────────────────────────────────────────
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
  navbar.classList.toggle('scrolled', window.scrollY > 40);
}, { passive: true });

// ── Hamburger ─────────────────────────────────────────────────────
const hamburger = document.getElementById('hamburger');
const navLinks  = document.getElementById('navLinks');
hamburger.addEventListener('click', () => {
  navLinks.classList.toggle('open');
});

// ── File input handlers ──────────────────────────────────────────
const jdFile      = document.getElementById('jdFile');
const resumeFiles = document.getElementById('resumeFiles');

jdFile.addEventListener('change', () => {
  const el = document.getElementById('jdChosen');
  if (jdFile.files.length) {
    el.textContent = '✓ ' + jdFile.files[0].name;
    el.style.color = 'var(--green)';
  } else {
    el.textContent = '';
  }
});

resumeFiles.addEventListener('change', () => {
  const el = document.getElementById('resumesChosen');
  const count = resumeFiles.files.length;
  if (count > 10) {
    el.textContent = '⚠ Max 10 resumes. Only first 10 will be used.';
    el.style.color = 'var(--amber)';
  } else if (count > 0) {
    const names = Array.from(resumeFiles.files).map(f => f.name).join(', ');
    el.textContent = `✓ ${count} file${count > 1 ? 's' : ''} selected`;
    el.title = names;
    el.style.color = 'var(--green)';
  } else {
    el.textContent = '';
  }
});

// ── Drag-and-drop ─────────────────────────────────────────────────
function setupDragDrop(zoneId, inputId) {
  const zone  = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  zone.addEventListener('dragover',  (e) => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', ()  => zone.classList.remove('dragover'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('dragover');
    try {
      const dataTransfer = new DataTransfer();
      Array.from(e.dataTransfer.files).forEach(f => dataTransfer.items.add(f));
      input.files = dataTransfer.files;
      input.dispatchEvent(new Event('change'));
    } catch(err) {
      console.warn('Drag-drop file assignment not supported; use Choose File button.');
    }
  });
}
setupDragDrop('jdZone', 'jdFile');
setupDragDrop('resumesZone', 'resumeFiles');

// ── Composite Score ───────────────────────────────────────────────
function composite(c) {
  return c.composite !== undefined
    ? c.composite
    : Math.round(c.skills * 0.45 + c.experience * 0.35 + c.culture * 0.20);
}

function getRankMedalClass(rank) {
  if (rank === 1) return 'rank-medal-1';
  if (rank === 2) return 'rank-medal-2';
  if (rank === 3) return 'rank-medal-3';
  return 'rank-medal-n';
}
function getRankCardClass(rank) {
  if (rank === 1) return 'rank-1';
  if (rank === 2) return 'rank-2';
  if (rank === 3) return 'rank-3';
  return '';
}

// ── Build Leaderboard ─────────────────────────────────────────────
function buildLeaderboard(candidates) {
  const container = document.getElementById('leaderboard');
  container.innerHTML = '';

  // Already sorted by backend — just render in order
  candidates.forEach((c, idx) => {
    const rank = idx + 1;
    const comp = Math.round(composite(c));
    const avatarHue = (idx * 47 + 200) % 360;

    const card = document.createElement('div');
    card.className = `candidate-card ${getRankCardClass(rank)}`;
    card.innerHTML = `
      <div class="candidate-header" onclick="toggleCandidate(this)"
           role="button" aria-expanded="false" id="cand-header-${rank}">
        <div class="candidate-rank ${getRankMedalClass(rank)}">${rank}</div>
        <div class="candidate-avatar" style="background:hsl(${avatarHue},55%,42%)">${c.initials || c.name.slice(0,2).toUpperCase()}</div>
        <div class="candidate-info">
          <div class="candidate-name">${c.name}</div>
          <div class="candidate-meta">${c.role || 'Applicant'}</div>
        </div>
        <div class="candidate-scores-inline">
          <div class="score-pill">
            <span class="score-pill-value" style="color:#818cf8">${Math.round(c.skills)}%</span>
            <span class="score-pill-label">Skills</span>
          </div>
          <div class="score-pill">
            <span class="score-pill-value" style="color:#a78bfa">${Math.round(c.experience)}%</span>
            <span class="score-pill-label">Exp</span>
          </div>
          <div class="score-pill">
            <span class="score-pill-value" style="color:#22d3ee">${Math.round(c.culture)}%</span>
            <span class="score-pill-label">Culture</span>
          </div>
        </div>
        <div class="candidate-composite">
          <div class="composite-value">${comp}%</div>
          <div class="composite-label">Overall Score</div>
        </div>
        <svg class="expand-icon" width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M19 9l-7 7-7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div class="candidate-details" id="cand-details-${rank}">
        <div class="detail-bars">
          <div class="detail-bar-row">
            <span class="detail-bar-label">Skills Match</span>
            <div class="detail-bar-track">
              <div class="detail-bar-fill" style="width:${c.skills}%;--grad:linear-gradient(90deg,#6366f1,#818cf8)"></div>
            </div>
            <span class="detail-bar-val" style="color:#818cf8">${Math.round(c.skills)}%</span>
          </div>
          <div class="detail-bar-row">
            <span class="detail-bar-label">Experience</span>
            <div class="detail-bar-track">
              <div class="detail-bar-fill" style="width:${c.experience}%;--grad:linear-gradient(90deg,#8b5cf6,#a78bfa)"></div>
            </div>
            <span class="detail-bar-val" style="color:#a78bfa">${Math.round(c.experience)}%</span>
          </div>
          <div class="detail-bar-row">
            <span class="detail-bar-label">Culture Fit</span>
            <div class="detail-bar-track">
              <div class="detail-bar-fill" style="width:${c.culture}%;--grad:linear-gradient(90deg,#06b6d4,#22d3ee)"></div>
            </div>
            <span class="detail-bar-val" style="color:#22d3ee">${Math.round(c.culture)}%</span>
          </div>
        </div>
        <div class="rationale-box">
          <h4>🧠 AI Rationale</h4>
          <p>${c.rationale}</p>
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

// ── Build Bias Report ─────────────────────────────────────────────
function buildBiasReport(biasData) {
  const data = biasData;
  const container = document.getElementById('biasReport');
  const statusClass = data.status === 'LOW' ? 'audit-pass' : 'audit-fail';

  container.innerHTML = `
    <div class="bias-report-header">
      <h4>🔍 Bias Audit Report – Name Variation Analysis</h4>
      <span class="audit-badge ${statusClass}">${data.status} BIAS</span>
    </div>
    <div class="bias-summary-grid">
      <div class="bias-summary-card">
        <div class="bias-summary-val" style="color:var(--indigo)">${data.testsRun}</div>
        <div class="bias-summary-label">Tests Run</div>
      </div>
      <div class="bias-summary-card">
        <div class="bias-summary-val" style="color:var(--amber)">${data.flagged}</div>
        <div class="bias-summary-label">Flags Raised</div>
      </div>
      <div class="bias-summary-card">
        <div class="bias-summary-val" style="color:var(--green)">${data.overallIndex}%</div>
        <div class="bias-summary-label">Bias Index</div>
      </div>
      <div class="bias-summary-card">
        <div class="bias-summary-val" style="color:var(--green)">✓</div>
        <div class="bias-summary-label">Audit Status</div>
      </div>
    </div>
    <div class="bias-detail-table">
      <div class="bias-table-header">
        <span>Candidate</span>
        <span>Original</span>
        <span>Varied</span>
        <span>Delta</span>
        <span>Status</span>
      </div>
      ${data.candidates.map(c => {
        const flagClass = c.flag === 'clear' ? 'flag-clear' : c.flag === 'warn' ? 'flag-warn' : 'flag-high';
        const flagLabel = c.flag === 'clear' ? 'Clear' : c.flag === 'warn' ? 'Watch' : 'Flag';
        return `
          <div class="bias-table-row">
            <span>${c.name}</span>
            <span>${c.original}</span>
            <span>${c.varied}</span>
            <span>Δ ${c.delta}%</span>
            <span><span class="bias-flag ${flagClass}">${flagLabel}</span></span>
          </div>`;
      }).join('')}
    </div>
    <div class="bias-card" style="margin-top:0">
      <div class="bias-card-header" style="margin-bottom:12px">📋 Methodology</div>
      <p style="font-size:0.88rem;color:var(--text-secondary);line-height:1.7">
        The Bias Audit module substitutes each candidate's detected name with 6 culturally diverse
        alternative names while keeping all professional details identical. The scoring model
        re-runs for each name variant and any score delta &gt;1.0% is flagged as a potential
        bias indicator. A delta &gt;3.0% raises a high-priority flag.
      </p>
    </div>
  `;
}

// ── Toggle Candidate Details ──────────────────────────────────────
function toggleCandidate(header) {
  const rank    = header.id.replace('cand-header-', '');
  const details = document.getElementById(`cand-details-${rank}`);
  const icon    = header.querySelector('.expand-icon');
  const isOpen  = details.classList.contains('open');
  if (isOpen) {
    details.classList.remove('open');
    icon.classList.remove('open');
    header.setAttribute('aria-expanded', 'false');
  } else {
    details.classList.add('open');
    icon.classList.add('open');
    header.setAttribute('aria-expanded', 'true');
  }
}

// ── Tab Switching ─────────────────────────────────────────────────
function showTab(tab) {
  document.getElementById('leaderboardTab').style.display  = tab === 'leaderboard' ? 'block' : 'none';
  document.getElementById('biasAuditTab').style.display    = tab === 'biasAudit'   ? 'block' : 'none';
  document.getElementById('tabLeaderboard').classList.toggle('tab-active', tab === 'leaderboard');
  document.getElementById('tabBiasAudit').classList.toggle('tab-active',   tab === 'biasAudit');
}

// ── Processing Steps ──────────────────────────────────────────────
const STEPS = [
  { id: 'procStep1', label: '📄 Parsing documents' },
  { id: 'procStep2', label: '🧠 Running semantic analysis' },
  { id: 'procStep3', label: '📊 Computing scores' },
  { id: 'procStep4', label: '🔍 Running bias audit' },
];
const STATUS_MESSAGES = [
  'Extracting text from PDFs...',
  'Analysing semantic similarity against JD...',
  'Computing composite scores...',
  'Running name-variation bias audit...',
];

let stepTimer = null;

function startProcessingAnimation() {
  let stepIdx = 0;
  const statusEl = document.getElementById('processingStatus');

  function advanceStep() {
    STEPS.forEach((s, j) => {
      const el = document.getElementById(s.id);
      if (j < stepIdx)       el.className = 'proc-step done';
      else if (j === stepIdx) el.className = 'proc-step active';
      else                   el.className = 'proc-step';
    });
    if (stepIdx < STATUS_MESSAGES.length) {
      statusEl.textContent = STATUS_MESSAGES[stepIdx];
    }
    stepIdx++;
    if (stepIdx <= STEPS.length) {
      stepTimer = setTimeout(advanceStep, 1800);
    }
  }
  advanceStep();
}

function stopProcessingAnimation() {
  if (stepTimer) clearTimeout(stepTimer);
  STEPS.forEach(s => { document.getElementById(s.id).className = 'proc-step done'; });
  document.getElementById('processingStatus').textContent = '✅ Analysis complete!';
}

// ── Store last result for export ──────────────────────────────────
let lastResult = null;

// ── Main Run Screening (calls real backend) ───────────────────────
async function runScreening() {
  const hasJD      = jdFile.files.length > 0;
  const hasResumes = resumeFiles.files.length > 0;

  if (!hasJD) {
    showNotification('Please upload a Job Description file (PDF or TXT).', 'warn');
    return;
  }
  if (!hasResumes) {
    showNotification('Please upload at least one resume (PDF).', 'warn');
    return;
  }

  // Build FormData
  const formData = new FormData();
  formData.append('jd', jdFile.files[0]);
  const files = Array.from(resumeFiles.files).slice(0, 10);
  files.forEach(f => formData.append('resumes', f));

  // Show processing UI
  document.getElementById('uploadPanel').style.display       = 'none';
  document.getElementById('processingOverlay').style.display = 'flex';
  document.getElementById('resultsPanel').style.display      = 'none';
  startProcessingAnimation();

  try {
    const response = await fetch('/api/screen', {
      method: 'POST',
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || `Server error ${response.status}`);
    }

    stopProcessingAnimation();
    await sleep(500);

    lastResult = data;
    buildLeaderboard(data.candidates);
    buildBiasReport(data.bias);

    document.getElementById('processingOverlay').style.display = 'none';
    document.getElementById('resultsPanel').style.display      = 'block';
    document.getElementById('resultsPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    stopProcessingAnimation();
    document.getElementById('processingOverlay').style.display = 'none';
    document.getElementById('uploadPanel').style.display       = 'block';
    showNotification(`Error: ${err.message}`, 'warn');
    console.error(err);
  }
}

// ── Reset ─────────────────────────────────────────────────────────
function resetTool() {
  document.getElementById('uploadPanel').style.display       = 'block';
  document.getElementById('processingOverlay').style.display = 'none';
  document.getElementById('resultsPanel').style.display      = 'none';
  document.getElementById('jdChosen').textContent            = '';
  document.getElementById('resumesChosen').textContent       = '';
  jdFile.value      = '';
  resumeFiles.value = '';
  lastResult        = null;
  showTab('leaderboard');
}

// ── Export Report ─────────────────────────────────────────────────
function exportReport() {
  if (!lastResult) { showNotification('No results to export yet.', 'warn'); return; }

  const now = new Date();
  const { candidates, bias } = lastResult;
  let report = `RecruitIQ – Candidate Screening Report\nGenerated: ${now.toLocaleString()}\n${'='.repeat(48)}\n\nCANDIDATE LEADERBOARD\n${'='.repeat(48)}\n`;

  candidates.forEach((c, i) => {
    report += `\n#${i+1} ${c.name}\n   Skills:     ${Math.round(c.skills)}%\n   Experience: ${Math.round(c.experience)}%\n   Culture:    ${Math.round(c.culture)}%\n   Overall:    ${Math.round(composite(c))}%\n\n   AI Rationale:\n   ${c.rationale}\n\n   ${'─'.repeat(46)}\n`;
  });

  report += `\nBIAS AUDIT SUMMARY\n${'='.repeat(48)}\nOverall Bias Index: ${bias.overallIndex}% (${bias.status})\nTests Run:  ${bias.testsRun}\nFlags:      ${bias.flagged}\n\nName Variation Results:\n`;
  bias.candidates.forEach(c => {
    report += `  ${c.name}: Original ${c.original} → Varied ${c.varied} (Δ ${c.delta}%) [${c.flag.toUpperCase()}]\n`;
  });
  report += `\n${'='.repeat(48)}\nRecruitIQ v1.0 | Ambitious NLP Project`;

  const blob = new Blob([report], { type: 'text/plain' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `RecruitIQ_Report_${now.toISOString().slice(0,10)}.txt`;
  a.click();
  URL.revokeObjectURL(url);
  showNotification('Report downloaded!', 'success');
}

// ── Notification Toast ────────────────────────────────────────────
function showNotification(message, type = 'info') {
  document.querySelector('.toast-notification')?.remove();
  const colors = {
    info:    { bg: 'rgba(99,102,241,0.15)', border: 'rgba(99,102,241,0.3)', text: '#818cf8' },
    warn:    { bg: 'rgba(245,158,11,0.15)', border: 'rgba(245,158,11,0.3)', text: '#fbbf24' },
    success: { bg: 'rgba(16,185,129,0.15)', border: 'rgba(16,185,129,0.3)', text: '#34d399' },
  };
  const c = colors[type] || colors.info;
  const toast = document.createElement('div');
  toast.className = 'toast-notification';
  toast.textContent = message;
  Object.assign(toast.style, {
    position: 'fixed', bottom: '28px', right: '28px', zIndex: '999',
    padding: '14px 22px', borderRadius: '12px',
    background: c.bg, border: `1px solid ${c.border}`, color: c.text,
    fontWeight: '500', fontSize: '0.88rem',
    boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
    backdropFilter: 'blur(12px)',
    transition: 'opacity 0.3s ease',
  });
  document.body.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3500);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── Intersection Observer Animations ──────────────────────────────
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity  = '1';
      entry.target.style.transform = 'translateY(0)';
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.feature-card, .step, .bias-card').forEach(el => {
  el.style.opacity   = '0';
  el.style.transform = 'translateY(24px)';
  el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
  observer.observe(el);
});

// ── Expose globals ────────────────────────────────────────────────
window.runScreening    = runScreening;
window.resetTool       = resetTool;
window.exportReport    = exportReport;
window.toggleCandidate = toggleCandidate;
window.showTab         = showTab;
