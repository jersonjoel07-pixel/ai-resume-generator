"""PDF engine layer: turns the processed resume data into an A4 PDF held in memory (io.BytesIO).

Layout: header band, left column (summary + experience), right sidebar (education, skills,
certifications). If the content is too long for one two-column page it falls back to a plain
single-column flow so nothing is ever cut off. Only the standard text hierarchy is used, so the
file stays readable by applicant-tracking systems.
"""
from __future__ import annotations

import io
import os
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, FrameBreak, NextPageTemplate, PageTemplate,
                                Paragraph, Spacer)

from resume_logic import enhance

NAVY, BLUE, GREY, LIGHT, RULE = HexColor("#0f172a"), HexColor("#2563eb"), HexColor("#475569"), HexColor("#f1f5f9"), HexColor("#cbd5e1")
PAGE_W, PAGE_H = A4
MARGIN, HEADER_H, GUTTER = 36, 104, 18
SIDEBAR_W = 190

_FONTS_READY = False


def _register_fonts() -> None:
    """ReportLab ships the Vera family (accents and Latin-extended); the built-in Helvetica does not."""
    global _FONTS_READY
    if _FONTS_READY:
        return
    folder = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
    for name, file in (("Vera", "Vera.ttf"), ("Vera-Bold", "VeraBd.ttf"), ("Vera-Italic", "VeraIt.ttf")):
        pdfmetrics.registerFont(TTFont(name, os.path.join(folder, file)))
    pdfmetrics.registerFontFamily("Vera", normal="Vera", bold="Vera-Bold", italic="Vera-Italic", boldItalic="Vera-Bold")
    _FONTS_READY = True


def _styles(scale: float = 1.0) -> dict[str, ParagraphStyle]:
    def style(name, size=9.0, leading=None, **kw):
        kw.setdefault("fontName", "Vera")
        kw.setdefault("textColor", NAVY)
        kw.setdefault("alignment", TA_LEFT)
        return ParagraphStyle(name, fontSize=round(size * scale, 2), leading=round((leading or size * 1.35) * scale, 2), **kw)

    return {
        "section": style("section", fontName="Vera-Bold", size=9.5, leading=12, textColor=BLUE, spaceBefore=12, spaceAfter=2),
        "body": style("body", size=8.8, leading=12.2, spaceAfter=2),
        "role": style("role", fontName="Vera-Bold", size=9.4, leading=12, spaceBefore=6),
        "meta": style("meta", size=8, leading=10.5, textColor=GREY, spaceAfter=2),
        "bullet": style("bullet", size=8.8, leading=12, leftIndent=11, bulletIndent=1, spaceAfter=1.5),
        "side": style("side", size=8.4, leading=11.4, spaceAfter=1.5),
        "sidebold": style("sidebold", fontName="Vera-Bold", size=8.8, leading=11.5, spaceBefore=5),
        "label": style("label", fontName="Vera-Bold", size=8, leading=10, textColor=GREY, spaceBefore=3),
    }


def _p(text: str, style: ParagraphStyle, **kw) -> Paragraph:
    return Paragraph(escape(text), style, **kw)       # user text is escaped: ReportLab parses markup


def _dates(exp: dict) -> str:
    start, end = exp.get("start", ""), exp.get("end", "")
    if not start and not end:
        return ""
    return f"{start or ''} - {end or 'Present'}".strip()


def _left_story(processed: dict, st: dict) -> list:
    story = [Paragraph("PROFESSIONAL SUMMARY", st["section"]), _p(processed["summary"], st["body"])]
    if processed["experience"]:
        story.append(Paragraph("EXPERIENCE", st["section"]))
        for exp in processed["experience"]:
            story.append(_p(f"{exp['title']}  |  {exp['company']}", st["role"]))
            if _dates(exp):
                story.append(_p(_dates(exp), st["meta"]))
            for bullet in exp["bullets"]:
                story.append(_p(bullet, st["bullet"], bulletText="•"))
    return story


def _right_story(data: dict, st: dict) -> list:
    story: list = []
    if data["education"]:
        story.append(Paragraph("EDUCATION", st["section"]))
        for edu in data["education"]:
            story.append(_p(edu["degree"], st["sidebold"]))
            story.append(_p(edu["institution"], st["side"]))
            extra = "  |  ".join(x for x in (edu["year"], edu["grade"]) if x)
            if extra:
                story.append(_p(extra, st["meta"]))
    skills = data["skills"]
    if skills["technical"] or skills["soft"]:
        story.append(Paragraph("SKILLS", st["section"]))
        if skills["technical"]:
            story += [_p("Technical", st["label"]), _p(", ".join(skills["technical"]), st["side"])]
        if skills["soft"]:
            story += [_p("Soft skills", st["label"]), _p(", ".join(skills["soft"]), st["side"])]
    if data["certifications"]:
        story.append(Paragraph("CERTIFICATIONS", st["section"]))
        story += [_p(c, st["side"], bulletText="•") for c in data["certifications"]]
    return story


def _page_decor(canvas, doc, data: dict, sidebar: bool) -> None:
    canvas.saveState()
    if sidebar:
        top = PAGE_H - HEADER_H
        canvas.setFillColor(LIGHT)
        canvas.rect(PAGE_W - MARGIN - SIDEBAR_W - 8, 0, SIDEBAR_W + 8 + MARGIN, top + 6, stroke=0, fill=1)
    if doc.page == 1:
        p = data["personal"]
        canvas.setFillColor(NAVY)
        canvas.setFont("Vera-Bold", 24)
        canvas.drawString(MARGIN, PAGE_H - 52, p["name"])
        canvas.setFillColor(BLUE)
        canvas.setFont("Vera-Bold", 11)
        canvas.drawString(MARGIN, PAGE_H - 70, p["role"])
        canvas.setFillColor(GREY)
        canvas.setFont("Vera", 8.4)
        contact = "   |   ".join(x for x in (p["email"], p["phone"], p["location"], p["link"]) if x)
        while contact and pdfmetrics.stringWidth(contact, "Vera", 8.4) > PAGE_W - 2 * MARGIN:
            contact = contact[:-2]
        canvas.drawString(MARGIN, PAGE_H - 86, contact)
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.8)
        canvas.line(MARGIN, PAGE_H - HEADER_H + 6, PAGE_W - MARGIN, PAGE_H - HEADER_H + 6)
    canvas.restoreState()


def _fits(story: list, width: float, height: float) -> bool:
    used = 0.0
    for flowable in story:
        _, h = flowable.wrap(width, height)
        used += h + flowable.getSpaceBefore() + flowable.getSpaceAfter()
    return used <= height


def _frame(x, y, w, h, ident) -> Frame:
    return Frame(x, y, w, h, id=ident, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)


def _compile(data: dict, processed: dict, scale: float, two_column: bool) -> bytes:
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN,
                          title=f"{data['personal']['name']} - Resume", author=data["personal"]["name"])
    st = _styles(scale)
    left_w = PAGE_W - 2 * MARGIN - SIDEBAR_W - GUTTER
    first_h, later_h = PAGE_H - HEADER_H - MARGIN, PAGE_H - 2 * MARGIN
    left, right = _left_story(processed, st), _right_story(data, st)

    if two_column:
        doc.addPageTemplates([PageTemplate(
            id="first",
            frames=[_frame(MARGIN, MARGIN, left_w, first_h, "left"),
                    _frame(PAGE_W - MARGIN - SIDEBAR_W, MARGIN, SIDEBAR_W, first_h, "right")],
            onPage=lambda c, d: _page_decor(c, d, data, True))])
        story = left + [FrameBreak()] + right
    else:
        doc.addPageTemplates([
            PageTemplate(id="first", frames=[_frame(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, first_h, "full1")],
                         onPage=lambda c, d: _page_decor(c, d, data, False)),
            PageTemplate(id="later", frames=[_frame(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, later_h, "full2")],
                         onPage=lambda c, d: _page_decor(c, d, data, False))])
        story = [NextPageTemplate("later")] + left + [Spacer(1, 4)] + right
    doc.build(story)
    return buf.getvalue()


def build_pdf(data: dict) -> bytes:
    """Compile the resume in memory. `data` must already be normalised and validated."""
    _register_fonts()
    processed = enhance(data)
    left_w = PAGE_W - 2 * MARGIN - SIDEBAR_W - GUTTER
    height = PAGE_H - HEADER_H - MARGIN
    for scale in (1.0, 0.94, 0.88, 0.82):                     # shrink type a little before spilling over
        st = _styles(scale)
        if _fits(_left_story(processed, st), left_w, height) and _fits(_right_story(data, st), SIDEBAR_W, height):
            return _compile(data, processed, scale, two_column=True)
    return _compile(data, processed, 1.0, two_column=False)
