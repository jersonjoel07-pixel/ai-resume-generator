"""Rule-based content processing for the AI Resume Generator.

No paid or external API is used: everything here is plain Python rules.
  * format_bullets()  - action-verb formatter for experience descriptions
  * build_summary()   - professional-summary synthesizer (used when the summary is blank)
  * validate()        - server-side mirror of the form checks
  * normalise()       - trims input and caps sizes before it reaches the PDF engine
"""
from __future__ import annotations

import re
from datetime import date

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_ROWS, MAX_TEXT, MAX_DESC = 12, 200, 2500

ACTION_VERBS = {
    "achieved", "administered", "analyzed", "analysed", "architected", "assisted", "automated", "built",
    "collaborated", "configured", "conducted", "coordinated", "created", "debugged", "delivered", "deployed",
    "designed", "developed", "documented", "drove", "enhanced", "established", "evaluated", "executed",
    "implemented", "improved", "integrated", "launched", "led", "maintained", "managed", "mentored",
    "migrated", "monitored", "optimized", "optimised", "organized", "performed", "planned", "prepared",
    "presented", "reduced", "refactored", "researched", "resolved", "reviewed", "scaled", "secured",
    "streamlined", "supported", "tested", "trained", "translated", "upgraded", "validated", "wrote",
}
WEAK_STARTS = (
    "responsible for", "worked on", "work on", "worked with", "helped with", "helped in", "helped to",
    "involved in", "was part of", "part of", "duties included", "in charge of", "tasked with", "handled",
)
# "-ing" word at the start of a task -> the past-tense action verb it describes
GERUNDS = {
    "analyzing": "Analyzed", "automating": "Automated", "building": "Built", "cleaning": "Cleaned",
    "configuring": "Configured", "coordinating": "Coordinated", "creating": "Created", "debugging": "Debugged",
    "deploying": "Deployed", "designing": "Designed", "developing": "Developed", "documenting": "Documented",
    "fixing": "Fixed", "handling": "Managed", "implementing": "Implemented", "integrating": "Integrated",
    "maintaining": "Maintained", "managing": "Managed", "merging": "Merged", "migrating": "Migrated",
    "monitoring": "Monitored", "optimizing": "Optimized", "optimising": "Optimized", "organizing": "Organized",
    "preparing": "Prepared", "researching": "Researched", "reviewing": "Reviewed", "supporting": "Supported",
    "testing": "Tested", "training": "Trained", "updating": "Updated", "writing": "Wrote",
}
# (pattern found anywhere in the line, verb to prefix) - first match wins, so specific rules come first
VERB_RULES = (
    (r"\b(unit test\w*|test cases?|testing|qa)\b", "Tested"),
    (r"\b(bug\w*|fix\w*|issue\w*|error\w*)\b", "Resolved"),
    (r"\b(automat\w*|script\w*|cron|workflow)\b", "Automated"),
    (r"\b(speed|faster|performance|optimi[sz]\w*|efficien\w*|reduce\w*)\b", "Streamlined"),
    (r"\b(dashboard\w*|report\w*|page\w*|app|website|portal|api|module\w*|feature\w*)\b", "Developed"),
    (r"\b(data|dataset\w*|analysis|analytics|model\w*)\b", "Analyzed"),
    (r"\b(design\w*|ui|ux|layout|wireframe\w*)\b", "Designed"),
    (r"\b(team|mentor\w*|lead|intern\w*|train\w*)\b", "Coordinated"),
    (r"\b(document\w*|readme|manual|guide)\b", "Documented"),
    (r"\b(deploy\w*|release\w*|host\w*|server)\b", "Deployed"),
)
FALLBACK_VERBS = ("Developed", "Implemented", "Delivered", "Built", "Improved", "Streamlined")


def _clean_line(text: str) -> str:
    text = re.sub(r"^[\s\-\*•●▪>]+", "", text)           # leading bullet markers
    text = re.sub(r"^\d+[.)]\s+", "", text)                                  # "1. " numbering
    return text.strip().rstrip(".;, ").strip()


def _split_lines(text: str) -> list[str]:
    out: list[str] = []
    for raw in re.split(r"[\r\n]+", text or ""):
        line = _clean_line(raw)
        if not line:
            continue
        # several sentences on one line become several bullets
        parts = re.split(r"(?<=[a-z0-9\)])\.\s+(?=[A-Z])", line)
        out.extend(p.strip().rstrip(".") for p in parts if p.strip())
    return out


def _lower_first(text: str) -> str:
    if not text:
        return text
    first = text.split(" ", 1)[0]
    if first.isupper() and len(first) > 1:      # keep acronyms: API, SQL
        return text
    return text[0].lower() + text[1:]


def _pick_verb(text: str, index: int) -> str:
    low = text.lower()
    for pattern, verb in VERB_RULES:
        if re.search(pattern, low):
            return verb
    return FALLBACK_VERBS[index % len(FALLBACK_VERBS)]


def _is_action_start(line: str) -> bool:
    first = re.sub(r"[^a-z]", "", line.split(" ", 1)[0].lower())
    if first in ACTION_VERBS:
        return True
    return len(first) > 4 and first.endswith("ed") and first not in {"speed", "need", "seed", "feed"}


def _past_tense_gerunds(text: str) -> str:
    """'cleaning and merging the data' -> 'Cleaned and merged the data' (known verbs only)."""
    words = text.split(" ")
    first = words[0].lower()
    if first not in GERUNDS:
        return text
    words[0] = GERUNDS[first]
    for i in range(1, len(words) - 1):                    # "... and merging ..." / "..., testing ..."
        if words[i - 1].lower().strip(",") in {"and", "or", "&"} and words[i].lower().strip(",") in GERUNDS:
            words[i] = GERUNDS[words[i].lower().strip(",")].lower() + ("," if words[i].endswith(",") else "")
    return " ".join(words)


def format_bullets(text: str) -> list[str]:
    """Return experience bullets that all start with an active verb."""
    bullets = []
    for i, line in enumerate(_split_lines(text)):
        low = line.lower()
        weak = next((w for w in WEAK_STARTS if low.startswith(w)), None)
        if weak:
            rest = line[len(weak):].strip()
            if weak.startswith("helped") and rest:
                line = f"Assisted with {rest}"                      # stay faithful: helping is not leading
            elif rest and rest.split(" ")[0].lower() in GERUNDS:
                line = _past_tense_gerunds(rest)
            else:
                line = f"{_pick_verb(rest, i)} {rest}" if rest else _pick_verb(line, i)
        elif not _is_action_start(line):
            if line.split(" ")[0].lower() in GERUNDS:
                line = _past_tense_gerunds(line)
            else:
                line = f"{_pick_verb(line, i)} {_lower_first(line)}"
        bullets.append(line[0].upper() + line[1:])
    return bullets


def _month_index(value: str) -> int | None:
    """'2024-05' -> months since year 0, '2023' -> January of that year, 'Present' -> today."""
    value = (value or "").strip().lower()
    if value in {"present", "current", "now", "till date", "ongoing"}:
        today = date.today()
        return today.year * 12 + today.month - 1
    m = re.search(r"(\d{4})(?:[-/](\d{1,2}))?", value)
    if m:
        year, month = int(m.group(1)), int(m.group(2) or 1)
    else:
        m = re.search(r"(\d{1,2})[-/](\d{4})", value)
        if not m:
            return None
        month, year = int(m.group(1)), int(m.group(2))
    return year * 12 + max(1, min(month, 12)) - 1


def total_years(experience: list[dict]) -> float:
    months = 0
    for exp in experience:
        start = _month_index(exp.get("start", ""))
        end = _month_index(exp.get("end", "") or "present")
        if start is not None and end is not None and end > start:
            months += end - start
    return round(months / 12, 1)


def _join(items: list[str]) -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def build_summary(data: dict) -> str:
    """Compose a tailored summary from role, experience level and key skills."""
    personal = data.get("personal", {})
    role = personal.get("role", "professional")
    experience = data.get("experience", [])
    skills = (data.get("skills", {}).get("technical") or []) + (data.get("skills", {}).get("soft") or [])
    years = total_years(experience)
    level = "Entry-level" if years < 1 else "Early-career" if years < 3 else "Experienced" if years < 7 else "Senior"
    exp_phrase = ("hands-on project experience" if years < 1
                  else f"{years:g} year{'s' if years != 1 else ''} of professional experience")
    sentences = [f"{level} {role} with {exp_phrase}" + (f" in {_join(skills[:4])}." if skills else ".")]
    if experience and experience[0].get("title") and experience[0].get("company"):
        sentences.append(f"Most recently worked as {experience[0]['title']} at {experience[0]['company']}.")
    if data.get("education"):
        edu = data["education"][0]
        if edu.get("degree") and edu.get("institution"):
            sentences.append(f"Holds a {edu['degree']} from {edu['institution']}.")
    sentences.append(f"Seeking a {role} position to apply technical skills, learn quickly and contribute to team goals.")
    return " ".join(sentences)


def _s(value, limit=MAX_TEXT) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _split_list(value) -> list[str]:
    items = value if isinstance(value, list) else re.split(r"[,\n;]+", str(value or ""))
    return [_s(i, 80) for i in items if _s(i, 80)][:30]


def normalise(raw: dict) -> dict:
    """Clean and cap everything the client sent; drop completely empty rows."""
    raw = raw if isinstance(raw, dict) else {}
    p = raw.get("personal") or {}
    experience = []
    for row in (raw.get("experience") or [])[:MAX_ROWS]:
        row = row or {}
        item = {"title": _s(row.get("title")), "company": _s(row.get("company")), "start": _s(row.get("start"), 20),
                "end": _s(row.get("end"), 20), "desc": str(row.get("desc") or "")[:MAX_DESC]}
        if any(v.strip() for v in item.values()):
            experience.append(item)
    education = []
    for row in (raw.get("education") or [])[:MAX_ROWS]:
        row = row or {}
        item = {"degree": _s(row.get("degree")), "institution": _s(row.get("institution")),
                "year": _s(row.get("year"), 20), "grade": _s(row.get("grade"), 40)}
        if any(item.values()):
            education.append(item)
    skills = raw.get("skills") or {}
    return {
        "personal": {k: _s(p.get(k)) for k in ("name", "email", "phone", "location", "role", "link")},
        "experience": experience,
        "education": education,
        "skills": {"technical": _split_list(skills.get("technical")), "soft": _split_list(skills.get("soft"))},
        "certifications": _split_list(raw.get("certifications")),
        "summary": str(raw.get("summary") or "").strip()[:1200],
    }


def validate(data: dict) -> dict[str, str]:
    """Return {field: message}; an empty dict means the payload is valid."""
    errors: dict[str, str] = {}
    p = data["personal"]
    if not p["name"]:
        errors["personal.name"] = "Full name is required."
    if not p["email"]:
        errors["personal.email"] = "Email is required."
    elif not EMAIL_RE.match(p["email"]):
        errors["personal.email"] = "Enter a valid email address."
    if not p["role"]:
        errors["personal.role"] = "Target role is required."
    for i, e in enumerate(data["experience"]):
        if not e["title"]:
            errors[f"experience.{i}.title"] = "Job title is required."
        if not e["company"]:
            errors[f"experience.{i}.company"] = "Company is required."
    for i, e in enumerate(data["education"]):
        if not e["degree"]:
            errors[f"education.{i}.degree"] = "Degree is required."
        if not e["institution"]:
            errors[f"education.{i}.institution"] = "Institution is required."
    if not data["skills"]["technical"]:
        errors["skills.technical"] = "Add at least one technical skill."
    return errors


def enhance(data: dict) -> dict:
    """What the processing layer adds: formatted bullets per job and the final summary."""
    return {
        "summary": data["summary"] or build_summary(data),
        "summary_generated": not data["summary"],
        "experience": [{**e, "bullets": format_bullets(e["desc"])} for e in data["experience"]],
    }
