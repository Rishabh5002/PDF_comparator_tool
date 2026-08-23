"""Backend service functions for form PDF comparison and report generation."""
from __future__ import annotations

import json
import secrets
from pathlib import Path

from src.comparator.comparator import FormComparator
from src.evaluation import evaluate_matching
from src.parser.form_parser import parse_pdf
from src.reporter.excel_report import write_excel_report
from src.reporter.html_report import write_html_report
from src.reporter.pdf_report import write_pdf_report
from src.security import security_status, verify_offline_core
from src.summary import build_local_summary
from src.matcher import match_diagnostics, match_questions

MAX_SIZE = 50 * 1024 * 1024


def question_to_dict(q):
    return {
        'number': q.number,
        'text': q.text,
        'field_type': q.field_type,
        'options': list(q.options or []),
        'child_questions': list(q.child_questions or []),
        'page': q.page,
        'y': q.y,
    }


def build_question_pairs(old_questions, new_questions, threshold: float):
    matches, removed, added = match_questions(old_questions, new_questions, threshold=threshold)
    pairs = []
    for old, new, score, signals in matches:
        changed = not FormComparator.cosmetic_text_equivalent(old.text, new.text)
        old_opts = {str(x).strip().lower() for x in old.options or [] if str(x).strip()}
        new_opts = {str(x).strip().lower() for x in new.options or [] if str(x).strip()}
        changed = (
            changed
            or old_opts != new_opts
            or old.field_type != new.field_type
            or set(old.child_questions or []) != set(new.child_questions or [])
            or old.number != new.number
        )
        pairs.append({
            'matched': True,
            'changed': changed,
            'old': question_to_dict(old),
            'new': question_to_dict(new),
            'score': score,
            'signals': signals,
        })
    for old in removed:
        pairs.append({
            'matched': False,
            'side': 'old',
            'old': question_to_dict(old),
            'new': None,
            'score': 0,
            'signals': {},
        })
    for new in added:
        pairs.append({
            'matched': False,
            'side': 'new',
            'old': None,
            'new': question_to_dict(new),
            'score': 0,
            'signals': {},
        })
    pairs.sort(
        key=lambda p: (
            p['old']['number'] if p.get('old') else 10**9,
            p['new']['number'] if p.get('new') else 10**9,
        )
    )
    return pairs


def build_payload(old_path: Path | str, new_path: Path | str, old_password: str | None, new_password: str | None, threshold: float):
    old = parse_pdf(old_path, old_password, max_size_bytes=MAX_SIZE)
    new = parse_pdf(new_path, new_password, max_size_bytes=MAX_SIZE)
    result = FormComparator(match_threshold=threshold).compare(old['questions'], new['questions'])
    return {
        'mode': 'offline',
        'security': security_status(),
        'offline_verification': verify_offline_core(),
        'old_document': {
            'filename': old['filename'],
            'pages': old['page_count'],
            'questions': len(old['questions']),
            'encrypted': old['encrypted'],
        },
        'new_document': {
            'filename': new['filename'],
            'pages': new['page_count'],
            'questions': len(new['questions']),
            'encrypted': new['encrypted'],
        },
        'comparison': result.to_dict(),
        'local_summary': build_local_summary(result),
        'question_pairs': build_question_pairs(old['questions'], new['questions'], threshold),
        'matching_diagnostics': match_diagnostics(old['questions'], new['questions'], threshold=threshold),
        'evaluation': evaluate_matching(old['questions'], new['questions'], threshold=threshold),
    }


def write_reports(payload: dict, workdir: Path) -> dict[str, Path]:
    base = workdir / 'comparison'
    paths = {}
    jsonp = base.with_suffix('.json')
    htmlp = base.with_suffix('.html')
    pdfp = base.with_suffix('.pdf')
    xlsx = base.with_suffix('.xlsx')

    try:
        jsonp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        paths['json'] = jsonp
    except Exception as e:
        print(f"JSON report error: {e}")

    try:
        write_html_report(payload, htmlp)
        paths['html'] = htmlp
    except Exception as e:
        print(f"HTML report error: {e}")

    try:
        write_pdf_report(payload, pdfp)
        paths['pdf'] = pdfp
    except Exception as e:
        print(f"PDF report generation skipped: {e}")

    try:
        write_excel_report(payload, xlsx)
        paths['xlsx'] = xlsx
    except Exception as e:
        print(f"Excel report error: {e}")

    return paths
