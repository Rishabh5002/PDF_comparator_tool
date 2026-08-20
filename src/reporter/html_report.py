"""Self-contained local HTML comparison report."""

from __future__ import annotations

import html
from pathlib import Path


def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, list):
        # Keep the report readable when a PDF exposes a large lookup list
        # (e.g. hundreds of countries). The JSON report retains the full set.
        if len(value) > 12:
            preview = ", ".join(str(x) for x in value[:12])
            return f"{preview}, ... (+{len(value) - 12} more)"
        return ", ".join(str(x) for x in value)
    return str(value)


def write_html_report(payload: dict, output_path: str | Path):
    comparison = payload["comparison"]
    rows = []
    for d in comparison["differences"]:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(d['type']))}</td>"
            f"<td>{html.escape(str(d.get('question_number') or ''))}</td>"
            f"<td>{html.escape(_fmt(d.get('old_value')))}</td>"
            f"<td>{html.escape(_fmt(d.get('new_value')))}</td>"
            f"<td>{html.escape(str(d.get('message') or ''))}</td>"
            f"<td>{html.escape('' if d.get('confidence') is None else f"{d['confidence']:.2f}")}</td>"
            "</tr>"
        )

    summary_items = "".join(
        f"<li><strong>{html.escape(k)}</strong>: {v}</li>"
        for k, v in comparison["summary"].items()
    )

    doc1 = payload["old_document"]
    doc2 = payload["new_document"]
    document_html = (
        f"<p><strong>Original:</strong> {html.escape(doc1['filename'])} "
        f"({doc1['pages']} pages, {doc1['questions']} questions)</p>"
        f"<p><strong>Revision:</strong> {html.escape(doc2['filename'])} "
        f"({doc2['pages']} pages, {doc2['questions']} questions)</p>"
    )

    report = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Offline Form PDF Comparison Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 32px; color: #222; }}
h1 {{ margin-bottom: 4px; }}
.note {{ padding: 12px; background: #f2f7f2; border: 1px solid #c8ddc8; border-radius: 6px; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; text-align: left; }}
th {{ background: #f5f5f5; }}
code {{ background: #f3f3f3; padding: 2px 4px; }}
</style>
</head>
<body>
<h1>Form PDF Comparison Report</h1>
<p>Processing mode: <strong>Offline / Local</strong></p>
<div class="note">PDF contents are processed by the local extraction, parsing, matching and comparison pipeline. No external AI service is required for this report.</div>
<h2>Documents</h2>
{document_html}
<h2>Summary</h2>
<ul>{summary_items}</ul>
<h2>Differences</h2>
<table>
<thead><tr><th>Type</th><th>Question</th><th>Original</th><th>Revision</th><th>Details</th><th>Match confidence</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</body>
</html>
"""

    output = Path(output_path)
    output.write_text(report, encoding="utf-8")
    return output
