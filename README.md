# Resume Screening Tool

A lightweight web application that automates the screening of resumes using natural language processing (NLP). The tool parses resume PDFs or text files, extracts key information (skills, experience, education), and matches candidates against job descriptions to rank the most suitable applicants.

---

## Features

- **Resume Parsing**: Supports PDF and plain text formats.
- **Skill Extraction**: Utilizes spaCy and custom keyword matching.
- **Job Matching**: Scores candidates based on relevance to a job description.
- **Web Interface**: Simple UI built with HTML, CSS, and JavaScript.
- **API Backend**: Python Flask server (`app.py`) handling file uploads and processing.

---

## Getting Started

### Prerequisites

- Python 3.9 or newer
- pip (Python package manager)
- Node.js (optional, for frontend tooling)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/monikap28/Resume-Screening-Tool.git
   cd Resume-Screening-Tool
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```
3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
4. (Optional) Install frontend dependencies if you plan to extend the UI:
   ```bash
   npm install
   ```

---

## Usage

Run the Flask development server:
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000`. You can then:
- Upload a resume file.
- Enter a job description.
- View the matching score and extracted information.

---

## Project Structure

```
│   README.md               # This file
│   index.html              # Front‑end entry point
│   app.py                  # Flask backend
│   requirements.txt        # Python dependencies
│
├───css
│       styles.css          # Styling for the UI
│
├───js
│       app.js             # Front‑end logic
│
└───templates
        results.html       # Jinja2 template for results page
```

---

## Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Commit your changes and push to your fork.
4. Open a pull request describing your changes.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## Acknowledgements

- **spaCy** – Industrial‑strength NLP library.
- **Flask** – Lightweight web framework for Python.
- **Bootstrap** – UI components and styling.

---

*Created on 2026‑07‑02*
