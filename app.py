"""Command-line entry point for the offline form PDF comparison engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.comparator.comparator import FormComparator
from src.evaluation import evaluate_matching
from src.parser.form_parser import parse_pdf
from src.reporter.html_report import write_html_report
from src.reporter.pdf_report import write_pdf_report
from src.reporter.excel_report import write_excel_report
from src.summary import build_local_summary
from src.matcher import match_diagnostics
from src.security import security_status, verify_offline_core


def main():
    parser = argparse.ArgumentParser(description="Offline Form PDF Comparison Tool")
    parser.add_argument("old_pdf", help="Original/older PDF")
    parser.add_argument("new_pdf", help="Revised/newer PDF")
    parser.add_argument("--old-password", default=None, help="Password for encrypted old PDF")
    parser.add_argument("--new-password", default=None, help="Password for encrypted new PDF")
    parser.add_argument("--threshold", type=float, default=0.45, help="Question matching threshold (0-1)")
    parser.add_argument("--max-size-mb", type=int, default=50, help="Maximum PDF size processed locally (MB)")
    parser.add_argument("--json", dest="json_path", help="Write comparison result as JSON")
    parser.add_argument("--html", dest="html_path", help="Write self-contained HTML report")
    parser.add_argument("--diagnostics", dest="diagnostics_path", help="Write ranked local matching diagnostics as JSON")
    parser.add_argument("--pdf", dest="pdf_path", help="Write PDF comparison report")
    parser.add_argument("--excel", dest="excel_path", help="Write Excel comparison report")
    args = parser.parse_args()

    old = parse_pdf(args.old_pdf, args.old_password, max_size_bytes=args.max_size_mb * 1024 * 1024)
    new = parse_pdf(args.new_pdf, args.new_password, max_size_bytes=args.max_size_mb * 1024 * 1024)

    comparator = FormComparator(match_threshold=args.threshold)
    result = comparator.compare(old["questions"], new["questions"])

    payload = {
        "mode": "offline",
        "security": security_status(),
        "offline_verification": verify_offline_core(),
        "old_document": {
            "filename": old["filename"],
            "pages": old["page_count"],
            "questions": len(old["questions"]),
            "encrypted": old["encrypted"],
        },
        "new_document": {
            "filename": new["filename"],
            "pages": new["page_count"],
            "questions": len(new["questions"]),
            "encrypted": new["encrypted"],
        },
        "comparison": result.to_dict(),
        "local_summary": build_local_summary(result),
        "matching_diagnostics": match_diagnostics(old["questions"], new["questions"], threshold=args.threshold),
        "evaluation": evaluate_matching(old["questions"], new["questions"], threshold=args.threshold),
    }

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if args.json_path:
        Path(args.json_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved report: {args.json_path}")
    if args.html_path:
        write_html_report(payload, args.html_path)
        print(f"Saved HTML report: {args.html_path}")
    if args.pdf_path:
        write_pdf_report(payload, args.pdf_path)
        print(f"Saved PDF report: {args.pdf_path}")
    if args.excel_path:
        write_excel_report(payload, args.excel_path)
        print(f"Saved Excel report: {args.excel_path}")
    if args.diagnostics_path:
        Path(args.diagnostics_path).write_text(
            json.dumps(payload["matching_diagnostics"], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Saved matching diagnostics: {args.diagnostics_path}")


if __name__ == "__main__":
    main()
