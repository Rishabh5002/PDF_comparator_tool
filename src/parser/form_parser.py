"""Deterministic PDF form extraction and parsing.

This module intentionally does not call an external AI service. It converts a
PDF into spatially ordered rows and then into Question objects that can be
compared locally.
"""

from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from src.models.parsed_line import ParsedLine
from src.models.question import Question
from src.models.raw_text_element import RawTextElement
from src.models.visual_row import VisualRow
from src.security import validate_pdf_input, DEFAULT_MAX_PDF_BYTES


QUESTION_RE = re.compile(r"^\s*(\d+)\s*\.?\s+(.+?)\s*$")

CHECKBOX_CHAR = "\uf06f"

BULLET_CHARS = (
    "\u2022",
    "\u25cf",
    "\u25cb",
    "\u25aa",
    "\u25a0",
    "\u25c6",
    "•",
    "●",
    "○",
    "▪",
    "■",
    "◆",
    "➢",
    "",
    "\uf06f",
)

Y_TOLERANCE = 3.0

HEADER_MARGIN = 45
FOOTER_MARGIN = 75


KNOWN_SECTION_KEYWORDS = {
    "profile",
    "summary",
    "professional summary",
    "about me",
    "about",
    "career objective",
    "objective",
    "personal details",
    "contact",
    "contact information",
    "education",
    "academic background",
    "academics",
    "technical skills",
    "skills",
    "skills & competencies",
    "core competencies",
    "technologies",
    "projects",
    "technical projects",
    "key projects",
    "academic projects",
    "personal projects",
    "experience",
    "work experience",
    "professional experience",
    "employment history",
    "internships",
    "certifications",
    "certifications & workshops",
    "licenses & certifications",
    "workshops",
    "courses",
    "training",
    "soft skills",
    "strengths",
    "languages",
    "languages known",
    "achievements",
    "awards",
    "honors",
    "publications",
    "interests",
    "hobbies",
    "declarations",
    "references",
    "overview",
    "background",
    "scope",
    "introduction",
    "conclusion",
}


MAX_PDF_SIZE_BYTES = DEFAULT_MAX_PDF_BYTES


def open_pdf(
    path: str | Path,
    password: str | None = None,
    max_size_bytes: int = MAX_PDF_SIZE_BYTES,
):
    """Open a PDF locally and authenticate encrypted PDFs when a password is supplied."""

    pdf_path = validate_pdf_input(
        path,
        max_size_bytes=max_size_bytes,
    )

    document = pymupdf.open(str(pdf_path))

    if not document.is_encrypted:
        return document

    if not password:
        document.close()
        raise ValueError(
            "PDF is password protected. A password is required."
        )

    if not document.authenticate(password):
        document.close()
        raise ValueError(
            "Unable to open encrypted PDF: incorrect password."
        )

    return document


def extract_text_elements(
    document,
    header_margin: float = HEADER_MARGIN,
    footer_margin: float = FOOTER_MARGIN,
):
    elements = []

    for page in document:
        elements.extend(
            get_content_elements(
                page,
                header_margin=header_margin,
                footer_margin=footer_margin,
            )
        )

    return elements


def get_content_elements(
    page,
    header_margin: float = HEADER_MARGIN,
    footer_margin: float = FOOTER_MARGIN,
):
    page_height = page.rect.height
    footer_limit = page_height - footer_margin

    elements = []

    for word in page.get_text("words", sort=True):

        (
            x0,
            y0,
            x1,
            y1,
            text,
            block_number,
            line_number,
            word_number,
        ) = word

        if not text.strip():
            continue

        if y0 < header_margin or y0 > footer_limit:
            continue

        elements.append(
            RawTextElement(
                text=text,
                page_number=page.number,
                x0=x0,
                y0=y0,
                x1=x1,
                y1=y1,
                block_number=block_number,
                line_number=line_number,
                word_number=word_number,
            )
        )

    return elements


def build_parsed_lines(elements):
    grouped = {}

    for element in elements:

        key = (
            element.page_number,
            element.block_number,
            element.line_number,
        )

        grouped.setdefault(
            key,
            [],
        ).append(element)

    parsed = []

    for (
        page_number,
        block_number,
        line_number,
    ), line_elements in grouped.items():

        line_elements.sort(
            key=lambda e: e.x0
        )

        text = " ".join(
            e.text
            for e in line_elements
            if e.text.strip()
        )

        parsed.append(
            ParsedLine(
                text=text,
                page_number=page_number,
                block_number=block_number,
                line_number=line_number,
                x0=min(
                    e.x0
                    for e in line_elements
                ),
                y0=min(
                    e.y0
                    for e in line_elements
                ),
                x1=max(
                    e.x1
                    for e in line_elements
                ),
                y1=max(
                    e.y1
                    for e in line_elements
                ),
            )
        )

    return sorted(
        parsed,
        key=lambda line: (
            line.page_number,
            line.y0,
            line.x0,
        ),
    )


def build_visual_rows(elements):

    elements = sorted(
        elements,
        key=lambda e: (
            e.page_number,
            e.y0,
            e.x0,
        ),
    )

    rows = []

    for element in elements:

        matching = None

        for row in rows:

            if (
                row.page_number
                == element.page_number
                and abs(
                    row.y0 - element.y0
                )
                <= Y_TOLERANCE
            ):
                matching = row
                break

        if matching is None:

            matching = VisualRow(
                page_number=element.page_number,
                y0=element.y0,
            )

            rows.append(matching)

        matching.add_element(element)

    for row in rows:

        row.elements.sort(
            key=lambda e: e.x0
        )

    return rows


def is_question_row(row):

    text = row.get_text().strip()

    match = QUESTION_RE.match(text)

    if not match:
        return None

    return (
        int(match.group(1)),
        clean_question_text(
            match.group(2)
        ),
    )


def clean_question_text(text: str) -> str:

    text = text.replace(
        "\xad",
        "-",
    )

    text = re.sub(
        r"_{2,}",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    text = text.strip(" -")

    return text


def group_rows_by_question(rows):

    blocks = []

    current = None

    for row in rows:

        question = is_question_row(row)

        if question is not None:

            number, text = question

            current = {
                "number": number,
                "text": text,
                "rows": [],
                "page": row.page_number + 1,
                "y": row.y0,
                "is_form": True,
            }

            blocks.append(current)

        elif current is not None:

            current["rows"].append(row)

    return blocks


def is_section_header_text(text: str) -> bool:

    cleaned = text.strip()

    if not cleaned or len(cleaned) > 60:
        return False

    norm = re.sub(
        r"[^\w\s&]",
        "",
        cleaned,
    ).strip().lower()

    if norm in KNOWN_SECTION_KEYWORDS:
        return True

    if re.match(
        r"^(section|article|clause|part|chapter)\s+[0-9a-zA-Z\.]+",
        cleaned,
        re.I,
    ):
        return True

    letters = [
        c
        for c in cleaned
        if c.isalpha()
    ]

    if (
        len(letters) >= 3
        and cleaned.isupper()
        and not cleaned.endswith(
            (".", ",", ";")
        )
    ):
        return True

    if (
        cleaned.endswith(":")
        and len(letters) >= 3
        and len(cleaned.split()) <= 4
    ):
        return True

    return False


def is_section_header_row(
    row: VisualRow,
    prev_row: VisualRow | None = None,
) -> bool:

    text = row.get_text().strip()

    return is_section_header_text(text)


def extract_section_items(rows):
    """Extract discrete items from a section."""

    items = []

    pending_index = None

    for row in rows:

        text = row.get_text().strip()

        if not text:
            continue

        cleaned = _clean_option(text)

        if not cleaned:
            continue

        is_bullet = (
            any(
                text.startswith(b)
                for b in BULLET_CHARS
            )
            or bool(
                re.match(
                    r"^[-•*▪●]\s+",
                    text,
                )
            )
            or bool(
                re.match(
                    r"^\(?\d+[\.\)]\s+",
                    text,
                )
            )
        )

        is_key_value = bool(
            re.match(
                r"^[A-Za-z\s/&]+:\s*.+",
                cleaned,
            )
        )

        is_split_line = (
            " | " in cleaned
            or " – " in cleaned
        )

        if (
            is_bullet
            or is_key_value
            or is_split_line
        ):

            items.append(cleaned)

            pending_index = len(items) - 1

        elif (
            pending_index is not None
            and len(cleaned) < 80
            and not is_bullet
        ):

            items[pending_index] = (
                f"{items[pending_index]} {cleaned}"
            ).strip()

        else:

            items.append(cleaned)

            pending_index = len(items) - 1

    return items


def group_rows_by_sections_or_paragraphs(
    document,
    rows,
    elements,
):
    """Universal structural extractor for resumes, CVs, sectional documents and reports."""

    blocks = []

    current_block = None

    section_index = 1

    for i, row in enumerate(rows):

        text = row.get_text().strip()

        if not text:
            continue

        prev_row = (
            rows[i - 1]
            if i > 0
            else None
        )

        if is_section_header_row(
            row,
            prev_row,
        ):

            header_text = clean_question_text(
                text.rstrip(":")
            )

            current_block = {
                "number": section_index,
                "text": header_text,
                "rows": [],
                "page": row.page_number + 1,
                "y": row.y0,
                "field_type": "section",
                "is_form": False,
            }

            blocks.append(
                current_block
            )

            section_index += 1

        elif current_block is not None:

            current_block["rows"].append(row)

        else:

            if not blocks:

                current_block = {
                    "number": section_index,
                    "text": clean_question_text(
                        text
                    ),
                    "rows": [],
                    "page": row.page_number + 1,
                    "y": row.y0,
                    "field_type": "header",
                    "is_form": False,
                }

                blocks.append(
                    current_block
                )

                section_index += 1

            else:

                blocks[-1]["rows"].append(row)

    if (
        len(blocks) >= 2
        or (
            len(blocks) == 1
            and blocks[0]["rows"]
        )
    ):
        return blocks

    blocks = []

    current_para = None

    para_index = 1

    last_y = None

    last_page = None

    for row in rows:

        text = row.get_text().strip()

        if not text:
            continue

        is_new_para = False

        if (
            last_page is not None
            and row.page_number != last_page
        ):

            is_new_para = True

        elif (
            last_y is not None
            and (row.y0 - last_y) > 16.0
        ):

            is_new_para = True

        if (
            is_new_para
            or current_para is None
        ):

            current_para = {
                "number": para_index,
                "text": clean_question_text(
                    text
                ),
                "rows": [],
                "page": row.page_number + 1,
                "y": row.y0,
                "field_type": "paragraph",
                "is_form": False,
            }

            blocks.append(
                current_para
            )

            para_index += 1

        else:

            current_para["rows"].append(
                row
            )

        last_y = row.y0

        last_page = row.page_number

    return blocks


def _split_checkbox_options(text: str):

    if CHECKBOX_CHAR not in text:
        return []

    parts = [
        p.strip()
        for p in text.split(
            CHECKBOX_CHAR
        )
    ]

    return [
        p
        for p in parts
        if p
    ]


def _clean_option(text: str):

    text = text.replace(
        "\xad",
        "-",
    )

    text = re.sub(
        r"^[☐□◻◯○]\s*",
        "",
        text,
    )

    text = re.sub(
        r"^\(\s*\)\s*",
        "",
        text,
    )

    text = re.sub(
        r"^[oO]\s+",
        "",
        text,
    )

    for b in BULLET_CHARS:

        if text.startswith(b):

            text = text[
                len(b):
            ].strip()

    text = re.sub(
        r"^[-•*▪●]\s+",
        "",
        text,
    )

    text = re.sub(
        r"^\(?\d+[\.\)]\s+",
        "",
        text,
    )

    text = re.sub(
        r"_{2,}",
        " ",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def _looks_like_plain_options(
    question_text: str,
    rows,
):

    if not rows:
        return False

    lower = question_text.lower()

    if (
        "check all that apply"
        in lower
    ):
        return True

    texts = [
        r.get_text().strip()
        for r in rows
        if r.get_text().strip()
    ]

    if len(texts) < 2:
        return False

    if any(
        t.lower().startswith(
            (
                "specify ",
                "location of ",
                "if ",
            )
        )
        for t in texts
    ):
        return False

    footer_markers = (
        "first name:",
        "last name:",
        "e-mail address:",
        "email address:",
        "date:",
    )

    if any(
        any(
            marker in t.lower()
            for marker in footer_markers
        )
        for t in texts
    ):
        return False

    return all(
        len(t) <= 80
        for t in texts
    )


def extract_options(
    question_text: str,
    rows,
):
    return extract_options_with_source(
        question_text,
        rows,
    )[0]


def extract_options_with_source(
    question_text: str,
    rows,
):

    options = []

    had_checkbox = False

    pending_index = None

    previous_page = None

    header_markers = (
        "cibmtr center number:",
        "cibmtr research id:",
        "form released",
        "copyright",
    )

    for row in rows:

        if (
            previous_page is not None
            and row.page_number
            != previous_page
        ):
            pending_index = None

        previous_page = row.page_number

        text = row.get_text().strip()

        if any(
            marker in text.lower()
            for marker in header_markers
        ):

            pending_index = None

            continue

        if not text:
            continue

        split = _split_checkbox_options(
            text
        )

        if split:

            had_checkbox = True

            for item in split:

                options.append(
                    _clean_option(item)
                )

            pending_index = (
                len(options) - 1
            )

            continue

        if (
            had_checkbox
            and pending_index is not None
            and not is_question_row(row)
        ):

            cleaned = _clean_option(
                text
            )

            if (
                cleaned
                and len(cleaned) < 80
            ):

                options[pending_index] = (
                    f"{options[pending_index]} {cleaned}"
                ).strip()

                continue

        if is_option_row(text):

            options.append(
                _clean_option(text)
            )

            pending_index = (
                len(options) - 1
            )

    if options:

        return (
            options,
            "checkbox_or_marked",
        )

    if _looks_like_plain_options(
        question_text,
        rows,
    ):

        return (
            [
                _clean_option(
                    r.get_text()
                )
                for r in rows
                if r.get_text().strip()
            ],
            "plain_text",
        )

    compact = " ".join(
        r.get_text().strip()
        for r in rows
        if r.get_text().strip()
    )

    m = re.fullmatch(
        r"(male)\s+(female)(?:\s+(other))?",
        compact,
        re.I,
    )

    if m:

        return (
            [
                p
                for p in m.groups()
                if p
            ],
            "compact_text",
        )

    return (
        [],
        None,
    )


def is_option_row(text):

    return bool(
        CHECKBOX_CHAR in text
        or re.match(
            r"^[☐□◻◯○]\s*(.+)$",
            text,
        )
        or re.match(
            r"^\(\s*\)\s*(.+)$",
            text,
        )
        or re.match(
            r"^[oO]\s+(.+)$",
            text,
        )
        or re.match(
            r"^[-•]\s+(.+)$",
            text,
        )
    )


def infer_field_type(
    question_text,
    options,
    rows,
):

    lower = question_text.lower()

    if (
        "check all that apply"
        in lower
    ):
        return "checkbox"

    if options:
        return "single_choice"

    if (
        "date" in lower
        or "yyyy mm dd"
        in " ".join(
            r.get_text().lower()
            for r in rows
        )
    ):
        return "date"

    if any(
        term in lower
        for term in (
            "number",
            "id:",
            "id)",
            "cic:",
        )
    ):
        return "text"

    return "text"


def parse_question_blocks(
    question_blocks,
):

    questions = []

    for block in question_blocks:

        is_form = block.get(
            "is_form",
            True,
        )

        if is_form:

            (
                options,
                option_source,
            ) = extract_options_with_source(
                block["text"],
                block["rows"],
            )

            field_type = infer_field_type(
                block["text"],
                options,
                block["rows"],
            )

        else:

            options = extract_section_items(
                block["rows"]
            )

            option_source = (
                "section_items"
                if options
                else None
            )

            field_type = (
                block.get(
                    "field_type"
                )
                or "section"
            )

        question = Question(
            number=block["number"],
            text=block["text"],
            field_type=field_type,
            options=options,
            child_questions=[],
            page=block.get("page"),
            y=block.get("y"),
            option_source=option_source,
        )

        questions.append(question)

    return questions


def parse_pdf(
    path: str | Path,
    password: str | None = None,
    max_size_bytes: int = MAX_PDF_SIZE_BYTES,
):
    """Return parsed questions plus complete document text coordinates."""

    document = open_pdf(
        path,
        password=password,
        max_size_bytes=max_size_bytes,
    )

    try:

        # =========================================================
        # NEW: EXTRACT EVERY TEXT ELEMENT FROM THE WHOLE PDF
        # =========================================================
        #
        # Unlike the existing comparison parser, this extraction
        # does NOT remove headers or footers.
        #
        # These elements contain:
        #   - text
        #   - page number
        #   - x0 / y0
        #   - x1 / y1
        #
        # The highlighting system uses these coordinates later.
        # =========================================================

        all_text_elements = extract_text_elements(
            document,
            header_margin=0,
            footer_margin=0,
        )

        # =========================================================
        # EXISTING QUESTION PARSING
        # =========================================================

        elements = extract_text_elements(
            document,
            header_margin=HEADER_MARGIN,
            footer_margin=FOOTER_MARGIN,
        )

        rows = build_visual_rows(
            elements
        )

        blocks = group_rows_by_question(
            rows
        )

        # If no numbered form questions were found,
        # use the existing universal structural parser.
        if not blocks:

            elements = extract_text_elements(
                document,
                header_margin=15,
                footer_margin=25,
            )

            rows = build_visual_rows(
                elements
            )

            blocks = group_rows_by_sections_or_paragraphs(
                document,
                rows,
                elements,
            )

        questions = parse_question_blocks(
            blocks
        )

        return {
            "filename": Path(path).name,

            "page_count": document.page_count,

            "encrypted": bool(
                document.is_encrypted
            ),

            # Existing parser information
            "text_elements": len(
                elements
            ),

            "visual_rows": len(
                rows
            ),

            "questions": questions,

            # =====================================================
            # NEW
            # Complete PDF word coordinates used by highlighting.
            # =====================================================
            "all_text_elements": all_text_elements,
        }

    finally:

        document.close()