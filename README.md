# AI Resume Generator

**Live demo: https://ai-resume-generator-tpba.onrender.com/**
(Free hosting sleeps when idle, so the first load can take about 30 seconds.)

A web app that turns a five-step form into a clean, two-column, ATS-friendly PDF resume. No sign-up, nothing is stored.

Try it fast: open the demo and click **Fill with sample data**, then go to the last step and press **Generate PDF**.

## What it does

1. **Five-step wizard**: personal details, experience, education, skills, summary. Required fields (name, email, role, one technical skill, and title/company or degree/institution for any row you start) block the Next button until filled.
2. **Action-verb formatter**: each experience task is rewritten to start with a strong verb.
   - "worked on sales dashboard" becomes "Developed sales dashboard"
   - "Responsible for cleaning the dataset" becomes "Cleaned the dataset"
   - "Helped with unit tests" becomes "Assisted with unit tests" (it never inflates helping into leading)
   - bullets that already start with a strong verb are left alone
3. **Auto summary**: if the summary box is blank, one is written from the target role, years of experience (calculated from the dates), the top skills, the latest job and the degree.
4. **Preview**: shows the rewritten bullets and summary before you download.
5. **PDF output**: a two-column layout (experience on the left, skills, education and certifications in a sidebar on the right). It shrinks the font slightly, then falls back to a multi-page single column, if the content is long.

## How it works

The "AI" is a set of plain Python rules, not a paid model or external API, so it is free, instant and predictable.

- `resume_logic.py`: cleans and size-limits input, validates it, and holds the verb rules (a list of weak openers, an ordered keyword-to-verb table, and a gerund-to-past-tense map).
- `pdf_builder.py`: builds the PDF with ReportLab Platypus entirely in memory (`io.BytesIO`), using the fonts bundled with ReportLab. User text is escaped so characters like `<` and `&` cannot break the layout.
- `app.py`: Flask routes. `/` serves the wizard, `/preview` and `/generate` take JSON and return the processed text or the PDF, `/health` is for the host. Bad input returns HTTP 400 with per-field errors. Request size is capped at 256 KB.
- `templates/` and `static/`: the wizard in plain HTML, CSS and JavaScript (no framework). Light and dark themes follow the system setting.

Limits: the rules cover common phrasing, not every sentence. Unknown phrases get a sensible fallback verb, so review the preview and edit anything that reads wrong.

## Run locally

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python app.py                 # http://127.0.0.1:5000
pytest                        # 10 tests
```

## Tests

`tests/test_resume.py` covers the project's test plan:

| Case | Checks |
|---|---|
| TC01 | required fields are enforced, and the server rejects an empty payload |
| TC02 | action verbs are inserted and fixed correctly |
| TC03 | a blank summary is generated, and a typed summary is kept |
| TC04 | the PDF is produced and downloads with a proper filename |
| extra | markup and unicode survive, and a very long resume still compiles |

## Deploy

Hosted on Render (free web service) from this repo using `render.yaml` (gunicorn, health check at `/health`). To deploy your own copy: Render, New, Blueprint, pick the repo. GitHub Pages cannot host it because it needs a Python server.

## Tech

Python 3.10, Flask, ReportLab, gunicorn, pytest, vanilla JavaScript.
