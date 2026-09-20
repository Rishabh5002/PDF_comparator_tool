"""Backend service functions for form PDF comparison and report generation."""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

import pymupdf

from src.comparator.comparator import FormComparator
from src.evaluation import evaluate_matching
from src.parser.form_parser import parse_pdf
from src.reporter.excel_report import write_excel_report
from src.reporter.html_report import write_html_report
from src.reporter.pdf_report import write_pdf_report
from src.security import (
    security_status,
    verify_offline_core,
)
from src.summary import build_local_summary
from src.matcher import (
    match_diagnostics,
    match_questions,
)


MAX_SIZE = 50 * 1024 * 1024


def question_to_dict(q):

    return {
        "number": q.number,
        "text": q.text,
        "field_type": q.field_type,
        "options": list(
            q.options or []
        ),
        "child_questions": list(
            q.child_questions or []
        ),
        "page": q.page,
        "y": q.y,
    }


def build_question_pairs(
    old_questions,
    new_questions,
    threshold: float,
):

    matches, removed, added = match_questions(
        old_questions,
        new_questions,
        threshold=threshold,
    )

    pairs = []

    for (
        old,
        new,
        score,
        signals,
    ) in matches:

        changed = (
            not FormComparator.cosmetic_text_equivalent(
                old.text,
                new.text,
            )
        )

        old_opts = {
            str(x).strip().lower()
            for x in old.options or []
            if str(x).strip()
        }

        new_opts = {
            str(x).strip().lower()
            for x in new.options or []
            if str(x).strip()
        }

        changed = (
            changed
            or old_opts != new_opts
            or old.field_type
            != new.field_type
            or set(
                old.child_questions or []
            )
            != set(
                new.child_questions or []
            )
            or old.number != new.number
        )

        pairs.append(
            {
                "matched": True,
                "changed": changed,
                "old": question_to_dict(old),
                "new": question_to_dict(new),
                "score": score,
                "signals": signals,
            }
        )

    for old in removed:

        pairs.append(
            {
                "matched": False,
                "side": "old",
                "old": question_to_dict(old),
                "new": None,
                "score": 0,
                "signals": {},
            }
        )

    for new in added:

        pairs.append(
            {
                "matched": False,
                "side": "new",
                "old": None,
                "new": question_to_dict(new),
                "score": 0,
                "signals": {},
            }
        )

    pairs.sort(
        key=lambda p: (
            p["old"]["number"]
            if p.get("old")
            else 10**9,

            p["new"]["number"]
            if p.get("new")
            else 10**9,
        )
    )

    return pairs


# ============================================================
# WHOLE PDF HIGHLIGHTING
# ============================================================


def _normalize_highlight_text(text):
    """Normalize text before comparing PDF words."""

    if text is None:
        return ""

    text = str(text)

    text = text.replace(
        "\xad",
        "-",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip().casefold()


def _element_token(element):
    """Return the normalized text used for word comparison."""

    return _normalize_highlight_text(
        getattr(
            element,
            "text",
            "",
        )
    )


def _highlight_rects(
    page,
    rects,
    color,
):
    """Apply PDF highlight annotations to supplied rectangles."""

    for rect in rects:

        try:

            if rect is None:
                continue

            annot = page.add_highlight_annot(
                rect
            )

            annot.set_colors(
                stroke=color
            )

            annot.update()

        except Exception as exc:

            print(
                f"Highlight annotation error: {exc}"
            )


def _highlight_elements(
    document,
    elements,
    color,
):
    """Highlight exact word coordinates in a PDF."""

    if not elements:
        return

    grouped = {}

    for element in elements:

        page_number = getattr(
            element,
            "page_number",
            None,
        )

        if page_number is None:
            continue

        try:

            page_index = int(
                page_number
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        if (
            page_index < 0
            or page_index >= len(document)
        ):
            continue

        x0 = getattr(
            element,
            "x0",
            None,
        )

        y0 = getattr(
            element,
            "y0",
            None,
        )

        x1 = getattr(
            element,
            "x1",
            None,
        )

        y1 = getattr(
            element,
            "y1",
            None,
        )

        if None in (
            x0,
            y0,
            x1,
            y1,
        ):
            continue

        try:

            rect = pymupdf.Rect(
                float(x0),
                float(y0),
                float(x1),
                float(y1),
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        grouped.setdefault(
            page_index,
            [],
        ).append(rect)

    for (
        page_index,
        rects,
    ) in grouped.items():

        page = document[
            page_index
        ]

        _highlight_rects(
            page,
            rects,
            color,
        )


def _group_elements_by_page(
    elements,
):
    """
    Group extracted text elements by PDF page.

    The parser stores page_number as a zero-based
    page index for RawTextElement.
    """

    grouped = {}

    for element in elements or []:

        page_number = getattr(
            element,
            "page_number",
            None,
        )

        if page_number is None:
            continue

        try:

            page_number = int(
                page_number
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        grouped.setdefault(
            page_number,
            [],
        ).append(element)

    for page_number in grouped:

        grouped[page_number].sort(
            key=lambda element: (
                float(
                    getattr(
                        element,
                        "y0",
                        0,
                    )
                ),
                float(
                    getattr(
                        element,
                        "x0",
                        0,
                    )
                ),
            )
        )

    return grouped


def _word_diff(
    old_elements,
    new_elements,
):
    """
    Compare words from a single page.

    Keeping the SequenceMatcher local to one page
    prevents changes on one page from cascading
    through the entire document.

    Returns:

        removed_elements
        added_elements
        modified_old_elements
        modified_new_elements
    """

    old_tokens = [
        _element_token(element)
        for element in old_elements
    ]

    new_tokens = [
        _element_token(element)
        for element in new_elements
    ]

    if not old_tokens and not new_tokens:
        return (
            [],
            [],
            [],
            [],
        )

    if not old_tokens:
        return (
            [],
            list(new_elements),
            [],
            [],
        )

    if not new_tokens:
        return (
            list(old_elements),
            [],
            [],
            [],
        )

    matcher = difflib.SequenceMatcher(
        None,
        old_tokens,
        new_tokens,
        autojunk=False,
    )

    removed = []
    added = []
    modified_old = []
    modified_new = []

    for (
        tag,
        i1,
        i2,
        j1,
        j2,
    ) in matcher.get_opcodes():

        if tag == "equal":

            continue

        elif tag == "delete":

            removed.extend(
                old_elements[
                    i1:i2
                ]
            )

        elif tag == "insert":

            added.extend(
                new_elements[
                    j1:j2
                ]
            )

        elif tag == "replace":

            old_chunk = old_elements[
                i1:i2
            ]

            new_chunk = new_elements[
                j1:j2
            ]

            old_count = len(
                old_chunk
            )

            new_count = len(
                new_chunk
            )

            common_count = min(
                old_count,
                new_count,
            )

            if old_count == new_count:

                modified_old.extend(
                    old_chunk
                )

                modified_new.extend(
                    new_chunk
                )

            else:

                modified_old.extend(
                    old_chunk[
                        :common_count
                    ]
                )

                modified_new.extend(
                    new_chunk[
                        :common_count
                    ]
                )

                if (
                    old_count
                    > common_count
                ):

                    removed.extend(
                        old_chunk[
                            common_count:
                        ]
                    )

                if (
                    new_count
                    > common_count
                ):

                    added.extend(
                        new_chunk[
                            common_count:
                        ]
                    )

    return (
        removed,
        added,
        modified_old,
        modified_new,
    )


def _compare_pages(
    old_elements,
    new_elements,
):
    """
    Compare the complete PDF page-by-page.

    This is the main performance optimization.

    Instead of comparing every word from both PDFs
    with one giant SequenceMatcher, each corresponding
    page is compared independently.
    """

    old_pages = _group_elements_by_page(
        old_elements
    )

    new_pages = _group_elements_by_page(
        new_elements
    )

    removed = []
    added = []
    modified_old = []
    modified_new = []

    max_page = max(
        max(old_pages.keys(), default=-1),
        max(new_pages.keys(), default=-1),
    )

    for page_number in range(
        max_page + 1
    ):

        old_page_elements = (
            old_pages.get(
                page_number,
                [],
            )
        )

        new_page_elements = (
            new_pages.get(
                page_number,
                [],
            )
        )

        (
            page_removed,
            page_added,
            page_modified_old,
            page_modified_new,
        ) = _word_diff(
            old_page_elements,
            new_page_elements,
        )

        removed.extend(
            page_removed
        )

        added.extend(
            page_added
        )

        modified_old.extend(
            page_modified_old
        )

        modified_new.extend(
            page_modified_new
        )

    return (
        removed,
        added,
        modified_old,
        modified_new,
    )


def _create_highlighted_pdfs(
    old_path: Path | str,
    new_path: Path | str,
    old_text_elements,
    new_text_elements,
    workdir: Path,
    old_password: str | None = None,
    new_password: str | None = None,
):
    """
    Create whole-document highlighted copies.

    Colors:

        RED    = removed
        GREEN  = added
        YELLOW = modified
    """

    workdir.mkdir(
        parents=True,
        exist_ok=True,
    )

    old_output = (
        workdir
        / "comparison_original_highlighted.pdf"
    )

    new_output = (
        workdir
        / "comparison_revised_highlighted.pdf"
    )

    old_doc = None
    new_doc = None

    try:

        # ========================================================
        # OPEN ORIGINAL PDF
        # ========================================================

        old_doc = pymupdf.open(
            str(old_path)
        )

        if old_doc.is_encrypted:

            if not old_password:
                raise ValueError(
                    "Original PDF is password protected. "
                    "A password is required for highlighting."
                )

            if not old_doc.authenticate(
                old_password
            ):
                raise ValueError(
                    "Unable to open encrypted original PDF."
                )

        # ========================================================
        # OPEN REVISED PDF
        # ========================================================

        new_doc = pymupdf.open(
            str(new_path)
        )

        if new_doc.is_encrypted:

            if not new_password:
                raise ValueError(
                    "Revised PDF is password protected. "
                    "A password is required for highlighting."
                )

            if not new_doc.authenticate(
                new_password
            ):
                raise ValueError(
                    "Unable to open encrypted revised PDF."
                )

        # ========================================================
        # COMPARE PDF PAGE-BY-PAGE
        # ========================================================

        (
            removed,
            added,
            modified_old,
            modified_new,
        ) = _compare_pages(
            old_text_elements,
            new_text_elements,
        )

        # ========================================================
        # REMOVED = RED
        # ========================================================

        _highlight_elements(
            old_doc,
            removed,
            (1.0, 0.0, 0.0),
        )

        # ========================================================
        # ADDED = GREEN
        # ========================================================

        _highlight_elements(
            new_doc,
            added,
            (0.0, 0.8, 0.0),
        )

        # ========================================================
        # MODIFIED = YELLOW
        # ========================================================

        _highlight_elements(
            old_doc,
            modified_old,
            (1.0, 0.8, 0.0),
        )

        _highlight_elements(
            new_doc,
            modified_new,
            (1.0, 0.8, 0.0),
        )

        # ========================================================
        # SAVE ORIGINAL HIGHLIGHTED PDF
        # ========================================================

        old_doc.save(
            str(old_output),
            garbage=4,
            deflate=True,
        )

        # ========================================================
        # SAVE REVISED HIGHLIGHTED PDF
        # ========================================================

        new_doc.save(
            str(new_output),
            garbage=4,
            deflate=True,
        )

        print(
            "Whole-PDF highlighting completed."
        )

        print(
            f"Original highlighted PDF: {old_output}"
        )

        print(
            f"Revised highlighted PDF: {new_output}"
        )

        print(
            "Highlighting statistics:"
        )

        print(
            f"  Removed words: {len(removed)}"
        )

        print(
            f"  Added words: {len(added)}"
        )

        print(
            "  Modified original words: "
            f"{len(modified_old)}"
        )

        print(
            "  Modified revised words: "
            f"{len(modified_new)}"
        )

        return {
            "old_highlighted_pdf": old_output,
            "new_highlighted_pdf": new_output,
        }

    except Exception as exc:

        print(
            f"Whole-PDF highlighting error: {exc}"
        )

        return {}

    finally:

        if old_doc is not None:

            try:
                old_doc.close()

            except Exception:
                pass

        if new_doc is not None:

            try:
                new_doc.close()

            except Exception:
                pass


# ============================================================
# GITHUB-STYLE SIDE-BY-SIDE SEQUENCE DIFF
# ============================================================


def _clean_diff_line(text: str) -> str:
    text = (text or "").replace("\xa0", " ").replace("\xad", "-")
    return re.sub(r"\s+", " ", text).strip()


def _compute_word_diff(old_text: str, new_text: str):
    words_old = re.findall(r"\S+|\s+", old_text)
    words_new = re.findall(r"\S+|\s+", new_text)
    sm = difflib.SequenceMatcher(None, words_old, words_new)
    old_chunks = []
    new_chunks = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        sub_old = "".join(words_old[i1:i2])
        sub_new = "".join(words_new[j1:j2])
        if tag == "equal":
            if sub_old:
                old_chunks.append({"type": "equal", "text": sub_old})
            if sub_new:
                new_chunks.append({"type": "equal", "text": sub_new})
        elif tag == "delete":
            if sub_old:
                old_chunks.append({"type": "del", "text": sub_old})
        elif tag == "insert":
            if sub_new:
                new_chunks.append({"type": "add", "text": sub_new})
        elif tag == "replace":
            if sub_old:
                old_chunks.append({"type": "del", "text": sub_old})
            if sub_new:
                new_chunks.append({"type": "add", "text": sub_new})
    return {"old_chunks": old_chunks, "new_chunks": new_chunks}


def build_side_by_side_diff(old_elements, new_elements):
    from src.parser.form_parser import build_visual_rows
    from src.matcher import text_similarity

    v_rows1 = build_visual_rows(old_elements or [])
    v_rows2 = build_visual_rows(new_elements or [])

    lines1 = []
    for r in v_rows1:
        txt = _clean_diff_line(r.get_text())
        if txt:
            lines1.append({
                "line_no": len(lines1) + 1,
                "page": r.page_number + 1,
                "y": round(r.y0, 1),
                "text": txt,
            })

    lines2 = []
    for r in v_rows2:
        txt = _clean_diff_line(r.get_text())
        if txt:
            lines2.append({
                "line_no": len(lines2) + 1,
                "page": r.page_number + 1,
                "y": round(r.y0, 1),
                "text": txt,
            })

    M, N = len(lines1), len(lines2)
    GAP = -0.5
    dp = [[0.0] * (N + 1) for _ in range(M + 1)]
    for i in range(M + 1):
        dp[i][0] = i * GAP
    for j in range(N + 1):
        dp[0][j] = j * GAP

    for i in range(1, M + 1):
        t1 = lines1[i - 1]["text"]
        for j in range(1, N + 1):
            t2 = lines2[j - 1]["text"]
            sim = text_similarity(t1, t2)
            if sim >= 0.90:
                score = 3.0
            elif sim >= 0.40:
                score = 2.5 * sim - 0.5
            else:
                score = -1.5

            dp[i][j] = max(
                dp[i - 1][j - 1] + score,
                dp[i - 1][j] + GAP,
                dp[i][j - 1] + GAP,
            )

    aligned = []
    i, j = M, N
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            t1 = lines1[i - 1]["text"]
            t2 = lines2[j - 1]["text"]
            sim = text_similarity(t1, t2)
            score = 3.0 if sim >= 0.90 else (2.5 * sim - 0.5 if sim >= 0.40 else -1.5)
            if abs(dp[i][j] - (dp[i - 1][j - 1] + score)) < 1e-4:
                kind = "unchanged" if sim >= 0.95 else "modified"
                word_diff = _compute_word_diff(t1, t2) if kind == "modified" else None
                aligned.append({
                    "status": kind,
                    "similarity": round(sim, 2),
                    "old": lines1[i - 1],
                    "new": lines2[j - 1],
                    "word_diff": word_diff,
                })
                i -= 1
                j -= 1
                continue
        if i > 0 and abs(dp[i][j] - (dp[i - 1][j] + GAP)) < 1e-4:
            aligned.append({
                "status": "deleted",
                "old": lines1[i - 1],
                "new": None,
                "word_diff": None,
            })
            i -= 1
        else:
            aligned.append({
                "status": "added",
                "old": None,
                "new": lines2[j - 1],
                "word_diff": None,
            })
            j -= 1

    aligned.reverse()
    return aligned


# ============================================================
# EXISTING COMPARISON PAYLOAD
# ============================================================


def build_payload(
    old_path: Path | str,
    new_path: Path | str,
    old_password: str | None,
    new_password: str | None,
    threshold: float,
):

    old = parse_pdf(
        old_path,
        old_password,
        max_size_bytes=MAX_SIZE,
    )

    new = parse_pdf(
        new_path,
        new_password,
        max_size_bytes=MAX_SIZE,
    )

    result = FormComparator(
        match_threshold=threshold
    ).compare(
        old["questions"],
        new["questions"],
    )

    side_by_side = build_side_by_side_diff(
        old.get("all_text_elements"),
        new.get("all_text_elements"),
    )

    return {

        "mode": "offline",

        "security": security_status(),

        "offline_verification": (
            verify_offline_core()
        ),

        "old_document": {
            "filename": old["filename"],
            "pages": old["page_count"],
            "questions": len(old["questions"]),
            "sections": len(old["questions"]),
            "items": len(old["questions"]),
            "encrypted": old["encrypted"],
        },

        "new_document": {
            "filename": new["filename"],
            "pages": new["page_count"],
            "questions": len(new["questions"]),
            "sections": len(new["questions"]),
            "items": len(new["questions"]),
            "encrypted": new["encrypted"],
        },

        "comparison": result.to_dict(),

        "side_by_side_diff": side_by_side,

        "local_summary": (
            build_local_summary(
                result
            )
        ),

        "question_pairs": (
            build_question_pairs(
                old["questions"],
                new["questions"],
                threshold,
            )
        ),

        "matching_diagnostics": (
            match_diagnostics(
                old["questions"],
                new["questions"],
                threshold=threshold,
            )
        ),

        "evaluation": (
            evaluate_matching(
                old["questions"],
                new["questions"],
                threshold=threshold,
            )
        ),

        # ========================================================
        # INTERNAL DATA
        # ========================================================

        "_old_questions": old[
            "questions"
        ],

        "_new_questions": new[
            "questions"
        ],

        "_old_text_elements": old[
            "all_text_elements"
        ],

        "_new_text_elements": new[
            "all_text_elements"
        ],
    }


def write_reports(
    payload: dict,
    workdir: Path,
) -> dict[str, Path]:

    base = workdir / "comparison"

    paths = {}

    jsonp = base.with_suffix(
        ".json"
    )

    htmlp = base.with_suffix(
        ".html"
    )

    pdfp = base.with_suffix(
        ".pdf"
    )

    xlsx = base.with_suffix(
        ".xlsx"
    )

    # ========================================================
    # JSON
    # ========================================================

    try:

        json_payload = {
            key: value
            for key, value
            in payload.items()
            if not key.startswith("_")
        }

        jsonp.write_text(
            json.dumps(
                json_payload,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        paths["json"] = jsonp

    except Exception as e:

        print(
            f"JSON report error: {e}"
        )

    # ========================================================
    # HTML
    # ========================================================

    try:

        write_html_report(
            payload,
            htmlp,
        )

        paths["html"] = htmlp

    except Exception as e:

        print(
            f"HTML report error: {e}"
        )

    # ========================================================
    # PDF REPORT
    # ========================================================

    try:

        write_pdf_report(
            payload,
            pdfp,
        )

        paths["pdf"] = pdfp

    except Exception as e:

        print(
            f"PDF report generation skipped: {e}"
        )

    # ========================================================
    # EXCEL
    # ========================================================

    try:

        write_excel_report(
            payload,
            xlsx,
        )

        paths["xlsx"] = xlsx

    except Exception as e:

        print(
            f"Excel report error: {e}"
        )

    return paths