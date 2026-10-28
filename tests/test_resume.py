"""Test cases from the project's test plan (TC01-TC04), plus a few safety checks."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import app
from resume_logic import build_summary, format_bullets, normalise, validate

GOOD = {
    "personal": {"name": "Asha Verma", "email": "asha@example.com", "phone": "+91 90000 00000",
                 "location": "Chennai, India", "role": "Data Analyst", "link": "github.com/asha"},
    "experience": [{"title": "Data Intern", "company": "Acme Analytics", "start": "2025-06", "end": "2025-12",
                    "desc": "worked on sales dashboard\nResponsible for cleaning the dataset\nBuilt a Flask API"}],
    "education": [{"degree": "BCA Data Science", "institution": "Sample University", "year": "2026", "grade": "8.4 CGPA"}],
    "skills": {"technical": "Python, SQL, Pandas", "soft": "Communication, Teamwork"},
    "certifications": "Python Basics\nSQL Fundamentals",
    "summary": "",
}


@pytest.fixture()
def client():
    return app.test_client()


# TC01 - form validation: required fields block generation (the browser blocks the step transition)
def test_tc01_required_fields_are_enforced():
    errors = validate(normalise({"personal": {"name": "", "email": "not-an-email", "role": ""}, "skills": {}}))
    assert {"personal.name", "personal.email", "personal.role", "skills.technical"} <= set(errors)


def test_tc01_server_rejects_empty_payload(client):
    r = client.post("/generate", json={})
    assert r.status_code == 400 and "errors" in r.get_json()


# TC02 - verb insertion: every bullet starts with an action verb
def test_tc02_verb_insertion():
    bullets = format_bullets("worked on sales dashboard\nResponsible for cleaning the dataset\nBuilt a Flask API")
    assert bullets[0] == "Developed sales dashboard"                 # weak "worked on" replaced by a fitting verb
    assert bullets[1] == "Cleaned the dataset"                        # "Responsible for cleaning" -> "Cleaned"
    assert bullets[2] == "Built a Flask API"                          # already starts with a strong verb: untouched


def test_tc02_helping_stays_honest_and_gerunds_become_past_tense():
    assert format_bullets("Helped with unit tests for the pipeline") == ["Assisted with unit tests for the pipeline"]
    assert format_bullets("cleaning and merging the customer dataset") == ["Cleaned and merged the customer dataset"]


def test_tc02_bullet_markers_are_removed_and_a_verb_is_prefixed():
    (line,) = format_bullets("- login page for admins")
    assert line.split(" ")[0] in {"Designed", "Developed", "Implemented", "Built", "Delivered", "Improved", "Streamlined"}
    assert "login page for admins" in line and not line.startswith("-")


# TC03 - auto summary fallback when the summary is blank
def test_tc03_summary_is_generated_when_blank():
    summary = build_summary(normalise(GOOD))
    assert "Data Analyst" in summary and "Python" in summary and "Sample University" in summary


def test_tc03_user_summary_is_kept(client):
    r = client.post("/preview", json={**GOOD, "summary": "My own words."})
    assert r.get_json()["summary"] == "My own words." and r.get_json()["summary_generated"] is False


# TC04 - PDF compilation delivers a downloadable byte stream
def test_tc04_pdf_is_returned(client):
    r = client.post("/generate", json=GOOD)
    assert r.status_code == 200 and r.mimetype == "application/pdf"
    assert r.data.startswith(b"%PDF") and len(r.data) > 3000
    assert "asha_verma_resume.pdf" in r.headers["Content-Disposition"]


def test_pdf_survives_markup_and_unicode(client):
    nasty = {**GOOD, "personal": {**GOOD["personal"], "name": "Zoë <b>Núñez</b> & Co"},
             "experience": [{"title": "Dev <script>", "company": "A&B", "start": "", "end": "",
                             "desc": "built <i>things</i> & more"}]}
    r = client.post("/generate", json=nasty)
    assert r.status_code == 200 and r.data.startswith(b"%PDF")


def test_very_long_resume_still_compiles(client):
    many = {**GOOD, "experience": [{"title": f"Role {i}", "company": f"Company {i}", "start": "2020-01", "end": "2021-01",
                                    "desc": "\n".join(f"Handled task number {j} for the team" for j in range(8))}
                                   for i in range(10)]}
    r = client.post("/generate", json=many)
    assert r.status_code == 200 and r.data.startswith(b"%PDF")
