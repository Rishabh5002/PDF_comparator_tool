"""Local PDF report writer using ReportLab."""
import re
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


def _clean_doc_name(name: str | None) -> str:
    if not name:
        return ""
    # Strip random hex token prefix if present (e.g. 16 hex chars + _)
    return re.sub(r"^[0-9a-fA-F]{16}_", "", str(name))


def _safe_cell(text, max_len=300, style=None):
    """Truncate cell text and wrap in a Paragraph so ReportLab wraps properly across pages."""
    if text is None:
        text_str = ""
    elif isinstance(text, list):
        if len(text) > 12:
            text_str = ", ".join(map(str, text[:12])) + f", ... (+{len(text)-12} more)"
        else:
            text_str = ", ".join(map(str, text))
    else:
        text_str = str(text)

    if len(text_str) > max_len:
        text_str = text_str[:max_len] + "..."
    # Escape HTML special characters for ReportLab Paragraph
    text_str = text_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if style is None:
        styles = getSampleStyleSheet()
        style = ParagraphStyle(
            'SafeCell',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
        )
    return Paragraph(text_str, style)


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

    old_raw = payload.get("old_document", {}).get("filename", "")
    new_raw = payload.get("new_document", {}).get("filename", "")
    clean_old_name = _clean_doc_name(old_raw) or "document.pdf"
    clean_new_name = _clean_doc_name(new_raw) or "document_revision.pdf"

    pdf_stem = Path(clean_old_name).stem if clean_old_name else "pdf_name"
    pdf_report_name = f"{pdf_stem}_comparison_report"

    doc = SimpleDocTemplate(
        str(output),
        pagesize=landscape(A4),
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
        title=f"{pdf_report_name}.pdf",
    )
    story = [
        Paragraph(f"{pdf_report_name}", styles["Title"]),
        Spacer(1, 12),
        Paragraph("Documents", styles["Heading2"]),
        Paragraph(f"Original: {_text(clean_old_name)} — {payload['old_document']['pages']} pages, {payload['old_document']['questions']} questions", body),
        Paragraph(f"Revision: {_text(clean_new_name)} — {payload['new_document']['pages']} pages, {payload['new_document']['questions']} questions", body),
        Spacer(1, 12),
        Paragraph("Summary", styles["Heading2"]),
    ]
    summary_data = [["Change type", "Count"]] + [[str(k), str(v)] for k, v in payload["comparison"]["summary"].items()]
    t = Table(summary_data, colWidths=[180, 80])
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.lightgrey), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("GRID", (0,0), (-1,-1), 0.5, colors.grey), ("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.extend([t, Spacer(1, 14), Paragraph("Differences", styles["Heading2"])])

    hdr_style = ParagraphStyle(
        "DiffHdr",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        alignment=TA_LEFT,
    )
    hdr_conf_style = ParagraphStyle(
        "DiffHdrConf",
        parent=hdr_style,
        alignment=TA_CENTER,
    )
    conf_cell_style = ParagraphStyle(
        "DiffConfCell",
        parent=body,
        alignment=TA_CENTER,
    )

    data = [[
        Paragraph("Type", hdr_style),
        Paragraph("Q", hdr_style),
        Paragraph("Original", hdr_style),
        Paragraph("Revision", hdr_style),
        Paragraph("Details", hdr_style),
        Paragraph("Confidence", hdr_conf_style),
    ]]
    for d in payload["comparison"]["differences"]:
        conf = "" if d.get("confidence") is None else f"{d['confidence']:.2f}"
        data.append([
            _safe_cell(d.get("type"), max_len=100, style=body),
            _safe_cell(d.get("question_number"), max_len=30, style=body),
            _safe_cell(d.get("old_value"), max_len=300, style=body),
            _safe_cell(d.get("new_value"), max_len=300, style=body),
            _safe_cell(d.get("message"), max_len=500, style=body),
            Paragraph(conf, conf_cell_style) if conf else Paragraph("", conf_cell_style)
        ])
    # Total landscape usable width is 793.89pt; colWidths sum to 780pt.
    # Confidence column increased from 55pt to 90pt so "Confidence" never overflows.
    t2 = Table(data, repeatRows=1, colWidths=[90, 35, 145, 145, 275, 90])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (5, 0), (5, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t2)
    story.extend([
        Spacer(1, 16),
        Paragraph("© Vibhor, Rishab and Sayan", body),
    ])
    doc.build(story)
    return output
