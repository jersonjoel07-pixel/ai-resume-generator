# AI Resume Generator

A small Flask web app that turns a five-step form into a clean, two-column, ATS-friendly PDF resume.

- **Five-step wizard**: personal details, experience, education, skills, summary. Required fields block "Next".
- **Rule-based "AI"** (plain Python, no paid API): weak openers such as "worked on..." or "responsible for..." become action-verb bullets, and a blank summary is written from your role, experience level and skills.
- **PDF built in memory** with ReportLab. Nothing is stored on the server.

## Run locally

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python app.py                 # http://127.0.0.1:5000
pytest                        # 10 tests
```

## Layout

| File | Purpose |
|---|---|
| `app.py` | Flask routes: `/`, `/preview`, `/generate`, `/health` |
| `resume_logic.py` | validation, action-verb formatter, summary builder |
| `pdf_builder.py` | ReportLab two-column PDF |
| `templates/`, `static/` | wizard UI |
| `tests/` | pytest suite (validation, verbs, summary, PDF) |

## Deploy (Render, free tier)

1. Push this repo to GitHub.
2. On render.com: **New > Blueprint** (or **Web Service**), pick the repo. `render.yaml` sets everything.
3. Open the `.onrender.com` URL. The free tier sleeps when idle, so the first load can take ~30 s.

GitHub Pages cannot host this app because it needs a Python server.
