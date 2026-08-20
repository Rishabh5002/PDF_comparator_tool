"""Local PDF report writer using ReportLab."""
from __future__ import annotations
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


def _text(value):
    if value is None:
        return ""
    if isinstance(value, list):
        if len(value) > 12:
            return ", ".join(map(str, value[:12])) + f", ... (+{len(value)-12} more)"
        return ", ".join(map(str, value))
    return str(value)


def write_pdf_report(payload: dict, output_path: str | Path):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("BodySmall", parent=styles["BodyText"], fontSize=8, leading=10)
    doc = SimpleDocTemplate(str(output), pagesize=landscape(A4), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)
    story = [
        Paragraph("Form PDF Comparison Report", styles["Title"]),
        Paragraph("Processing mode: <b>Offline / Local</b>", styles["BodyText"]),
        Spacer(1, 8),
        Paragraph("PDF contents are processed locally. No external AI service is required by the comparison core.", body),
        Spacer(1, 12),
        Paragraph("Documents", styles["Heading2"]),
        Paragraph(f"Original: {_text(payload['old_document']['filename'])} — {payload['old_document']['pages']} pages, {payload['old_document']['questions']} questions", body),
        Paragraph(f"Revision: {_text(payload['new_document']['filename'])} — {payload['new_document']['pages']} pages, {payload['new_document']['questions']} questions", body),
        Spacer(1, 12),
        Paragraph("Summary", styles["Heading2"]),
    ]
    summary_data = [["Change type", "Count"]] + [[str(k), str(v)] for k, v in payload["comparison"]["summary"].items()]
    t = Table(summary_data, colWidths=[180, 80])
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.lightgrey), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("GRID", (0,0), (-1,-1), 0.5, colors.grey), ("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.extend([t, Spacer(1, 14), Paragraph("Differences", styles["Heading2"])])
    data = [["Type", "Q", "Original", "Revision", "Details", "Confidence"]]
    for d in payload["comparison"]["differences"]:
        conf = "" if d.get("confidence") is None else f"{d['confidence']:.2f}"
        data.append([Paragraph(_text(d.get("type")), body), Paragraph(_text(d.get("question_number")), body), Paragraph(_text(d.get("old_value")), body), Paragraph(_text(d.get("new_value")), body), Paragraph(_text(d.get("message")), body), conf])
    t2 = Table(data, repeatRows=1, colWidths=[90, 35, 150, 150, 300, 55])
    t2.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.lightgrey), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("GRID", (0,0), (-1,-1), 0.4, colors.grey), ("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.append(t2)
    doc.build(story)
    return output
