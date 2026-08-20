import fitz
from collections import Counter

from .field_classifier import (
    classify_page,
    classify_document,
    print_classification,
    print_line_classification,
)

# ============================================================
# PDF METADATA
# ============================================================

def inspect_metadata(doc):
    """
    Inspect basic PDF metadata and document properties.
    """
    print("PDF Metadata:")
    print(f"  Page count: {len(doc)}")
    print(f"  Metadata: {doc.metadata}")
    print(f"  Is encrypted: {doc.is_encrypted}")


# ============================================================
# TEXT INSPECTION
# ============================================================

def inspect_text(page):
    """
    Extract and display text information from a page.
    """

    print("\n--- TEXT ---")

    text = page.get_text("text")

    print(text)

    print("\n--- TEXT BLOCKS ---")

    blocks = page.get_text("blocks")

    for index, block in enumerate(blocks):
        print(f"\nBlock {index}:")
        print(block)


# ============================================================
# WORD INSPECTION
# ============================================================

def inspect_words(page):
    """
    Extract words along with their coordinates.
    """

    print("\n--- WORDS ---")

    words = page.get_text("words")

    for index, word in enumerate(words):
        print(f"Word {index}: {word}")


# ============================================================
# IMAGE INSPECTION
# ============================================================

def inspect_images(page):
    """
    Inspect images embedded in a PDF page.
    """

    print("\n--- IMAGES ---")

    images = page.get_images(full=True)

    print(f"Total images: {len(images)}")

    for index, image in enumerate(images):
        print(f"\nImage {index}:")
        print(image)


# ============================================================
# DRAWING NORMALIZATION
# ============================================================

def normalize_drawing(drawing):
    """
    Convert PyMuPDF drawing information into a smaller,
    consistent structure that can later be used by the parser
    and comparison engine.
    """

    rect = drawing["rect"]

    return {
        "type": drawing["type"],

        "bbox": {
            "x0": round(rect.x0, 2),
            "y0": round(rect.y0, 2),
            "x1": round(rect.x1, 2),
            "y1": round(rect.y1, 2),
        },

        "geometry": {
            "width": round(rect.width, 2),
            "height": round(rect.height, 2),
        },

        "fill": (
            tuple(round(value, 3) for value in drawing["fill"])
            if drawing["fill"]
            else None
        ),

        "stroke": (
            tuple(round(value, 3) for value in drawing["color"])
            if drawing["color"]
            else None
        ),

        "fill_opacity": (
            round(drawing["fill_opacity"], 3)
            if drawing["fill_opacity"] is not None
            else None
        ),

        "stroke_opacity": (
            round(drawing["stroke_opacity"], 3)
            if drawing["stroke_opacity"] is not None
            else None
        ),

        "line_width": (
            round(drawing["width"], 2)
            if drawing["width"] is not None
            else None
        ),

        "seqno": drawing.get("seqno"),

        "layer": drawing.get("layer"),

        "close_path": drawing.get("closePath"),
    }


# ============================================================
# DRAWING CLASSIFICATION
# ============================================================

def classify_drawing(drawing):
    """
    Classify a PDF drawing based on its bounding box.

    This is an initial geometric classifier.
    Later we can make this much more sophisticated.
    """

    rect = drawing["rect"]

    width = rect.width
    height = rect.height

    # Very small objects
    if width < 1 and height < 1:
        return "tiny_shape"

    # Very wide and very short
    if width > 100 and height < 2:
        return "horizontal_line"

    # Very tall and very narrow
    if height > 100 and width < 2:
        return "vertical_line"

    # Rectangular shape
    if width > 2 and height > 2:
        return "rectangle"

    return "other"


# ============================================================
# DRAWING INSPECTION
# ============================================================

def inspect_drawings(page):
    """
    Extract, normalize and classify all drawings on a page.

    Returns:
        list[dict]: Structured drawing information.
    """

    raw_drawings = page.get_drawings()

    drawings = []

    for index, drawing in enumerate(raw_drawings):

        normalized = normalize_drawing(drawing)

        normalized["index"] = index

        normalized["classification"] = classify_drawing(drawing)

        drawings.append(normalized)

    return drawings


# ============================================================
# DRAWING SUMMARY
# ============================================================

def drawing_summary(drawings):
    """
    Count drawings by their classification.
    """

    return Counter(
        drawing["classification"]
        for drawing in drawings
    )


# ============================================================
# PRINT DRAWING DETAILS
# ============================================================

def print_drawing_summary(drawings):
    """
    Print a compact summary instead of dumping all 666 drawings.
    """

    print("\n--- DRAWING SUMMARY ---")

    print(f"Total drawings: {len(drawings)}")

    summary = drawing_summary(drawings)

    for name, count in summary.items():
        print(f"  {name}: {count}")


# ============================================================
# PRINT INDIVIDUAL DRAWINGS
# ============================================================

def print_drawings(drawings):
    """
    Print normalized drawing information.
    """

    print("\n--- DRAWINGS ---")

    for drawing in drawings:

        print(
            f"Drawing {drawing['index']}: "
            f"{drawing['classification']} "
            f"{drawing['bbox']}"
        )


def inspect_widgets(page):
    """
    Inspect widgets (interactive form fields) on a page.
    """

    print("\n--- WIDGETS ---")

    widgets = list(page.widgets() or [])

    if not widgets:
        print("No widgets found.")
        return []

    for index, widget in enumerate(widgets):
        print(f"\nWidget {index}:")
        print(f"  Type: {widget.field_type}")
        print(f"  Name: {widget.field_name}")
        print(f"  Value: {widget.field_value}")
        print(f"  Rect: {widget.rect}")

    return widgets


# ============================================================
# COMPLETE PAGE INSPECTION
# ============================================================

def inspect_page(page):
    """
    Run all low-level inspection operations for a page.

    Returns structured inspection data for later
    field classification and question extraction.
    """

    print("=" * 60)
    print(f"PAGE {page.number}")
    print("=" * 60)

    # -------------------------
    # TEXT
    # -------------------------

    inspect_text(page)

    # -------------------------
    # WORDS
    # -------------------------

    words = page.get_text("words")

    inspect_words(page)

    normalized_words = normalize_words(words)

    # -------------------------
    # IMAGES
    # -------------------------

    inspect_images(page)

    # -------------------------
    # WIDGETS
    # -------------------------

    widgets = inspect_widgets(page)

    # -------------------------
    # DRAWINGS
    # -------------------------

    drawings = inspect_drawings(page)

    print_drawing_summary(drawings)

    print_drawings(drawings)

    # -------------------------
    # STRUCTURED PAGE RESULT
    # -------------------------

    return {
    "page_number": page.number,
    "words": normalized_words,
    "drawings": drawings,
    "widgets": widgets,
}


# ============================================================
# COMPLETE PDF INSPECTION
# ============================================================

def inspect_pdf(pdf_path):
    """
    Inspect the complete PDF.

    Returns structured inspection data for every page.
    """

    doc = fitz.open(pdf_path)

    inspect_metadata(doc)

    results = []

    for page in doc:

        page_result = inspect_page(page)

        results.append(page_result)

    doc.close()

    return results

# ============================================================
# WORD NORMALIZATION
# ============================================================

def normalize_words(words):
    """
    Convert PyMuPDF word tuples into a consistent structure.

    PyMuPDF word format:
    (x0, y0, x1, y1, text, block_no, line_no, word_no)
    """

    normalized_words = []

    for index, word in enumerate(words):
        x0, y0, x1, y1, text, block_no, line_no, word_no = word

        normalized_words.append({
            "index": index,
            "text": text,

            "bbox": {
                "x0": round(x0, 2),
                "y0": round(y0, 2),
                "x1": round(x1, 2),
                "y1": round(y1, 2),
            },

            "geometry": {
                "width": round(x1 - x0, 2),
                "height": round(y1 - y0, 2),
            },

            "block": block_no,
            "line": line_no,
            "word": word_no,
        })

    return normalized_words


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    from pathlib import Path

    # Get project root
    project_root = Path(__file__).resolve().parents[2]

    print(f"Project root: {project_root}")

    # Search for samplev1.pdf anywhere inside the project
    pdf_files = list(project_root.rglob("samplev1.pdf"))

    if not pdf_files:
        print("\nERROR: samplev1.pdf was not found.")
        print("\nPDF files found in the project:")

        all_pdfs = list(project_root.rglob("*.pdf"))

        if all_pdfs:
            for pdf in all_pdfs:
                print(f"  {pdf}")
        else:
            print("  No PDF files found.")

        raise FileNotFoundError(
            "Could not locate samplev1.pdf inside the project."
        )

    pdf_path = pdf_files[0]

    print(f"\nInspecting PDF: {pdf_path}")

    results = inspect_pdf(str(pdf_path))

    classification_results = classify_document(results)

    print_classification(classification_results)

    print_line_classification(classification_results)