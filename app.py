"""AI Resume Generator - Flask application.

Routes
  GET  /          the 5-step wizard (HTML)
  POST /preview   JSON in -> the formatted bullets and the summary the PDF will contain
  POST /generate  JSON in -> an A4 PDF resume, compiled in memory and streamed to the browser
  GET  /health    liveness check for hosting platforms
"""
import io
import re

from flask import Flask, jsonify, render_template, request, send_file

from pdf_builder import build_pdf
from resume_logic import enhance, normalise, validate

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024          # a resume payload is a few KB


def _payload():
    """Parse + clean the JSON body; returns (data, error_response)."""
    raw = request.get_json(silent=True)
    if not isinstance(raw, dict):
        return None, (jsonify({"errors": {"_": "Send the resume data as a JSON object."}}), 400)
    data = normalise(raw)
    errors = validate(data)
    if errors:
        return None, (jsonify({"errors": errors}), 400)
    return data, None


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/preview")
def preview():
    data, error = _payload()
    if error:
        return error
    processed = enhance(data)
    return jsonify({
        "summary": processed["summary"],
        "summary_generated": processed["summary_generated"],
        "experience": [{"title": e["title"], "company": e["company"], "bullets": e["bullets"]}
                       for e in processed["experience"]],
    })


@app.post("/generate")
def generate():
    data, error = _payload()
    if error:
        return error
    buf = io.BytesIO(build_pdf(data))
    slug = re.sub(r"[^a-z0-9]+", "_", data["personal"]["name"].lower()).strip("_") or "resume"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=f"{slug}_resume.pdf")


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
