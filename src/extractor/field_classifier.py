"""
Field Classifier

Takes structured PDF inspection data and identifies
candidate form-field regions based on geometry and
nearby text.

This version is intentionally conservative.

The PDF inspector detects many drawings that are only
layout elements (page borders, containers, table rows,
etc.). This classifier filters those out before treating
a drawing as a possible form field.
"""

import re
from math import isclose


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_PAGE_WIDTH = 595
DEFAULT_PAGE_HEIGHT = 842

# Label detection
LABEL_VERTICAL_TOLERANCE = 5
LABEL_HORIZONTAL_LIMIT = 120
LABEL_MAX_WORDS = 8

# Checkbox grouping
CHECKBOX_GROUP_X_TOLERANCE = 3
CHECKBOX_GROUP_Y_GAP_MIN = 8
CHECKBOX_GROUP_Y_GAP_MAX = 18
MIN_CHECKBOX_GROUP_SIZE = 3

# Confidence thresholds
HIGH_CONFIDENCE = 0.80
MEDIUM_CONFIDENCE = 0.55


# ============================================================
# GEOMETRY HELPERS
# ============================================================

def get_bbox(obj):
    """
    Return the bounding box from a normalized object.
    """
    return obj["bbox"]


def bbox_width(bbox):
    return max(0, bbox["x1"] - bbox["x0"])


def bbox_height(bbox):
    return max(0, bbox["y1"] - bbox["y0"])


def bbox_center(bbox):
    return (
        (bbox["x0"] + bbox["x1"]) / 2,
        (bbox["y0"] + bbox["y1"]) / 2,
    )


def bbox_center_y(bbox):
    return (bbox["y0"] + bbox["y1"]) / 2


def bbox_center_x(bbox):
    return (bbox["x0"] + bbox["x1"]) / 2


# ============================================================
# PAGE BOUNDARY FILTERS
# ============================================================

def is_outside_page(bbox, page_width=DEFAULT_PAGE_WIDTH,
                    page_height=DEFAULT_PAGE_HEIGHT,
                    tolerance=10):
    """
    Detect objects that are clearly outside the visible page.
    """

    return (
        bbox["x1"] < -tolerance
        or bbox["x0"] > page_width + tolerance
        or bbox["y1"] < -tolerance
        or bbox["y0"] > page_height + tolerance
    )


# ============================================================
# GEOMETRY FILTERS
# ============================================================

def is_page_width_object(
    bbox,
    page_width=DEFAULT_PAGE_WIDTH,
    threshold=0.90,
):
    """
    Detect objects that span almost the entire PDF page.

    These are usually page borders, section containers,
    table structures, or layout elements.
    """

    width = bbox_width(bbox)

    return width >= page_width * threshold


def is_tiny_rectangle(bbox):
    """
    Detect very small rectangles.

    These are strong candidates for checkboxes/options.
    """

    width = bbox_width(bbox)
    height = bbox_height(bbox)

    return width <= 20 and height <= 20


def is_reasonable_checkbox(bbox):
    """
    Detect small approximately square objects.
    """

    width = bbox_width(bbox)
    height = bbox_height(bbox)

    if width <= 2 or height <= 2:
        return False

    if width > 20 or height > 20:
        return False

    ratio = width / height

    return 0.55 <= ratio <= 1.8


def is_reasonable_input_line(bbox, page_width=DEFAULT_PAGE_WIDTH):
    """
    Detect a horizontal line that could represent
    an input field.

    The line should be reasonably long but should not
    span the entire page.
    """

    width = bbox_width(bbox)
    height = bbox_height(bbox)

    if width < 40:
        return False

    if width > 0.90 * page_width:
        return False

    if height > 3:
        return False

    return True


def is_reasonable_text_field(
    bbox,
    page_width=DEFAULT_PAGE_WIDTH,
):
    """
    Detect a rectangular region that could represent
    a text/input field.
    """

    width = bbox_width(bbox)
    height = bbox_height(bbox)

    if width < 40 or height < 3:
        return False

    if width >= 0.90 * page_width:
        return False

    if height > 50:
        return False

    if width / height < 2:
        return False

    return True


# ============================================================
# DRAWING CLASSIFICATION
# ============================================================

def classify_rectangle(drawing):
    """
    Classify a rectangular drawing as a possible:

        - checkbox
        - text field
        - container

    The classifier is intentionally conservative.
    """

    bbox = get_bbox(drawing)

    # --------------------------------------------------------
    # Reject page-sized/layout rectangles
    # --------------------------------------------------------

    if is_page_width_object(bbox):
        return None

    # --------------------------------------------------------
    # Checkbox
    # --------------------------------------------------------

    if is_reasonable_checkbox(bbox):
        return "possible_checkbox"

    # --------------------------------------------------------
    # Text field
    # --------------------------------------------------------

    if is_reasonable_text_field(bbox):
        return "possible_text_field"

    # --------------------------------------------------------
    # Everything else is probably layout
    # --------------------------------------------------------

    return "possible_container"


# ============================================================
# DRAWING CANDIDATES
# ============================================================

def classify_drawings(
    drawings,
    page_width=DEFAULT_PAGE_WIDTH,
    page_height=DEFAULT_PAGE_HEIGHT,
):
    """
    Classify normalized drawings into candidate field types.
    """

    candidates = []

    for drawing in drawings:

        bbox = drawing.get("bbox")

        if not bbox:
            continue

        # ----------------------------------------------------
        # Reject objects outside the page
        # ----------------------------------------------------

        if is_outside_page(
            bbox,
            page_width,
            page_height,
        ):
            continue

        classification = drawing.get("classification")

        # ====================================================
        # RECTANGLES
        # ====================================================

        if classification == "rectangle":

            candidate_type = classify_rectangle(drawing)

            if candidate_type is None:
                continue

            if candidate_type == "possible_container":
                continue

            candidates.append({
                "source": "drawing",
                "drawing_index": drawing.get("index"),
                "type": candidate_type,
                "bbox": bbox,
            })

        # ====================================================
        # HORIZONTAL LINES
        # ====================================================

        elif classification == "horizontal_line":

            if not is_reasonable_input_line(
                bbox,
                page_width,
            ):
                continue

            candidates.append({
                "source": "drawing",
                "drawing_index": drawing.get("index"),
                "type": "possible_line_field",
                "bbox": bbox,
            })

    return candidates


# ============================================================
# TEXT NORMALIZATION
# ============================================================

QUESTION_NUMBER_PATTERN = re.compile(
    r"^\s*\d{1,3}[.)]?\s*$"
)


def normalize_word_text(text):
    """
    Normalize extracted word text.
    """

    if not text:
        return ""

    text = str(text)

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def is_question_number(text):
    """
    Detect standalone question numbers such as:

        1
        2
        11
        12.
        13)
    """

    if not text:
        return False

    return bool(
        QUESTION_NUMBER_PATTERN.match(text)
    )


def clean_label_text(text):
    """
    Normalize label punctuation and whitespace.
    """

    if not text:
        return ""

    text = normalize_word_text(text)

    # Remove duplicated whitespace around punctuation
    text = re.sub(
        r"\s+([,:;?])",
        r"\1",
        text,
    )

    text = re.sub(
        r"([(:])\s+",
        r"\1 ",
        text,
    )

    return text.strip()


# ============================================================
# WORD POSITION HELPERS
# ============================================================

def word_center_y(word):
    return bbox_center_y(word["bbox"])


def word_center_x(word):
    return bbox_center_x(word["bbox"])


def word_right(word):
    return word["bbox"]["x1"]


def word_left(word):
    return word["bbox"]["x0"]


# ============================================================
# LABEL ANALYSIS
# ============================================================

def find_nearby_words(
    candidate,
    words,
    vertical_tolerance=LABEL_VERTICAL_TOLERANCE,
    horizontal_limit=LABEL_HORIZONTAL_LIMIT,
    max_words=LABEL_MAX_WORDS,
):
    """
    Find the most relevant words immediately to the left
    of a candidate.

    Unlike the previous implementation, this does NOT
    collect every word within a large 200-point region.

    Words are first restricted to approximately the same
    baseline and then selected based on their distance
    from the candidate.
    """

    bbox = candidate["bbox"]

    candidate_y = bbox_center_y(bbox)

    possible = []

    for word in words:

        word_bbox = word.get("bbox")

        if not word_bbox:
            continue

        text = normalize_word_text(
            word.get("text", "")
        )

        if not text:
            continue

        word_y = word_center_y(word)

        # ----------------------------------------------------
        # Same horizontal text line
        # ----------------------------------------------------

        if abs(word_y - candidate_y) > vertical_tolerance:
            continue

        # ----------------------------------------------------
        # Word must be completely to the left
        # ----------------------------------------------------

        if word_right(word) > bbox["x0"]:
            continue

        horizontal_distance = (
            bbox["x0"] - word_right(word)
        )

        if horizontal_distance > horizontal_limit:
            continue

        possible.append({
            "word": word,
            "distance": horizontal_distance,
        })

    # --------------------------------------------------------
    # Closest words first
    # --------------------------------------------------------

    possible.sort(
        key=lambda item: item["distance"]
    )

    if not possible:
        return []

    # --------------------------------------------------------
    # Build a contiguous label from the candidate backwards.
    #
    # This prevents unrelated text elsewhere on the row
    # from being swallowed into the label.
    # --------------------------------------------------------

    selected = []

    previous_left = bbox["x0"]

    for item in possible:

        word = item["word"]
        gap = previous_left - word_right(word)

        # Large gap = probably a different text region.
        if selected and gap > 35:
            break

        selected.append(word)

        previous_left = word_left(word)

        if len(selected) >= max_words:
            break

    # We selected from right -> left.
    selected.reverse()

    return selected

def find_checkbox_option_label(
    candidate,
    words,
    vertical_tolerance=7,
    horizontal_limit=100,
):
    """
    Find text immediately to the right of a checkbox.

    Example:

        [ ] Male

    returns:

        "Male"
    """

    bbox = candidate["bbox"]

    candidate_y = (
        bbox["y0"] + bbox["y1"]
    ) / 2

    possible_words = []

    for word in words:

        word_bbox = word["bbox"]

        word_y = (
            word_bbox["y0"] +
            word_bbox["y1"]
        ) / 2

        # ----------------------------------------------------
        # Must be on approximately the same line.
        # ----------------------------------------------------

        if abs(word_y - candidate_y) > vertical_tolerance:
            continue

        # ----------------------------------------------------
        # Word must be to the right.
        # ----------------------------------------------------

        if word_bbox["x0"] < bbox["x1"]:
            continue

        horizontal_distance = (
            word_bbox["x0"] - bbox["x1"]
        )

        if horizontal_distance > horizontal_limit:
            continue

        possible_words.append(word)

    # --------------------------------------------------------
    # Sort left-to-right.
    # --------------------------------------------------------

    possible_words.sort(
        key=lambda word:
        word["bbox"]["x0"]
    )

    return clean_label(possible_words)

def enrich_checkbox_options(
    candidates,
    words,
):
    """
    Attach option labels to checkbox candidates.
    """

    enriched = []

    for candidate in candidates:

        if candidate["type"] != "possible_checkbox":
            enriched.append(candidate)
            continue

        option_label = find_checkbox_option_label(
            candidate,
            words
        )

        enriched_candidate = {
            **candidate,
            "option_label": option_label,
        }

        enriched.append(
            enriched_candidate
        )

    return enriched


# ============================================================
# LABEL CLEANING
# ============================================================

def clean_label(words):
    """
    Convert nearby words into a readable label.

    Standalone question-number tokens are removed.

    Example:

        ["1", "First", "Name:"]

    becomes:

        "First Name:"
    """

    if not words:
        return ""

    cleaned = []

    for word in words:

        text = normalize_word_text(
            word.get("text", "")
        )

        if not text:
            continue

        # Remove standalone question numbers.
        if is_question_number(text):
            continue

        cleaned.append(text)

    return clean_label_text(
        " ".join(cleaned)
    )


# ============================================================
# LABEL SCORING
# ============================================================

def calculate_label_confidence(
    candidate,
    nearby_words,
):
    """
    Calculate a rough confidence score for label association.

    This is intentionally heuristic. It is useful for ranking
    candidates, not as a machine-learning probability.
    """

    if not nearby_words:
        return 0.0

    bbox = candidate["bbox"]
    candidate_y = bbox_center_y(bbox)

    score = 0.0

    # --------------------------------------------------------
    # Words on same baseline
    # --------------------------------------------------------

    distances = []

    for word in nearby_words:

        word_y = word_center_y(word)

        distances.append(
            abs(word_y - candidate_y)
        )

    if distances:

        average_vertical_distance = (
            sum(distances) / len(distances)
        )

        if average_vertical_distance <= 2:
            score += 0.45

        elif average_vertical_distance <= 4:
            score += 0.35

        else:
            score += 0.20

    # --------------------------------------------------------
    # Label immediately before field
    # --------------------------------------------------------

    nearest_word = nearby_words[-1]

    horizontal_distance = (
        bbox["x0"] - word_right(nearest_word)
    )

    if horizontal_distance <= 10:
        score += 0.40

    elif horizontal_distance <= 25:
        score += 0.30

    elif horizontal_distance <= 50:
        score += 0.15

    # --------------------------------------------------------
    # Label length
    # --------------------------------------------------------

    if len(nearby_words) <= 5:
        score += 0.15

    else:
        score += 0.05

    return min(score, 1.0)


# ============================================================
# CANDIDATE ENRICHMENT
# ============================================================

def enrich_candidates(
    candidates,
    words,
):
    """
    Attach nearby text to each candidate.

    Adds:

        nearby_words
        possible_label
        label_confidence
    """

    enriched = []

    for candidate in candidates:

        nearby_words = find_nearby_words(
            candidate,
            words,
        )

        label = clean_label(
            nearby_words
        )

        label_confidence = calculate_label_confidence(
            candidate,
            nearby_words,
        )

        enriched_candidate = {
            **candidate,
            "nearby_words": nearby_words,
            "possible_label": label,
            "label_confidence": round(
                label_confidence,
                3,
            ),
        }

        enriched.append(
            enriched_candidate
        )

    return enriched

# ============================================================
# CHECKBOX GROUPING
# ============================================================

def vertical_distance(bbox1, bbox2):
    """
    Return vertical distance between two bounding boxes.
    """
    center1 = bbox_center(bbox1)
    center2 = bbox_center(bbox2)

    return abs(center1[1] - center2[1])


def horizontal_distance(bbox1, bbox2):
    """
    Return horizontal distance between two bounding boxes.
    """
    center1 = bbox_center(bbox1)
    center2 = bbox_center(bbox2)

    return abs(center1[0] - center2[0])


def same_checkbox_column(candidate1, candidate2, tolerance=8):
    """
    Check whether two checkbox candidates are vertically
    aligned in approximately the same column.
    """

    x1 = bbox_center(candidate1["bbox"])[0]
    x2 = bbox_center(candidate2["bbox"])[0]

    return abs(x1 - x2) <= tolerance


def group_checkboxes(
    candidates,
    max_vertical_gap=18,
    x_tolerance=8,
    min_group_size=2,
):
    """
    Group vertically aligned checkbox candidates.

    The classifier currently sees repeated checkbox drawings
    as independent fields.

    Example:

        checkbox
        checkbox
        checkbox
        checkbox

    becomes:

        checkbox_group
            ├── checkbox
            ├── checkbox
            ├── checkbox
            └── checkbox

    This is only a geometric grouping step.
    Semantic option labels are assigned later.
    """

    checkboxes = [
        candidate
        for candidate in candidates
        if candidate["type"] == "possible_checkbox"
    ]

    if not checkboxes:
        return candidates

    # --------------------------------------------------------
    # Sort by x position first, then y position.
    # --------------------------------------------------------

    checkboxes.sort(
        key=lambda candidate: (
            bbox_center(candidate["bbox"])[0],
            bbox_center(candidate["bbox"])[1],
        )
    )

    groups = []
    current_group = []

    for checkbox in checkboxes:

        if not current_group:
            current_group.append(checkbox)
            continue

        previous = current_group[-1]

        same_column = same_checkbox_column(
            previous,
            checkbox,
            tolerance=x_tolerance,
        )

        previous_y = bbox_center(
            previous["bbox"]
        )[1]

        current_y = bbox_center(
            checkbox["bbox"]
        )[1]

        vertical_gap = abs(
            current_y - previous_y
        )

        if (
            same_column
            and vertical_gap <= max_vertical_gap
        ):
            current_group.append(checkbox)

        else:
            groups.append(current_group)
            current_group = [checkbox]

    if current_group:
        groups.append(current_group)

    # --------------------------------------------------------
    # Assign group IDs.
    # --------------------------------------------------------

    group_number = 0

    for group in groups:

        if len(group) < min_group_size:
            continue

        group_number += 1

        group_id = f"checkbox_group_{group_number}"

        # Sort top-to-bottom.
        group.sort(
            key=lambda candidate:
            bbox_center(candidate["bbox"])[1]
        )

        total = len(group)

        for index, candidate in enumerate(group):

            candidate["group"] = group_id
            candidate["group_index"] = index + 1
            candidate["group_size"] = total

    return candidates


# ============================================================
# CHECKBOX GROUPING
# ============================================================

def are_same_checkbox_column(
    bbox1,
    bbox2,
    x_tolerance=CHECKBOX_GROUP_X_TOLERANCE,
):
    """
    Determine whether two checkboxes belong to the same
    vertical checkbox column.
    """

    return abs(
        bbox_center_x(bbox1)
        - bbox_center_x(bbox2)
    ) <= x_tolerance


def checkbox_vertical_gap(
    bbox1,
    bbox2,
):
    """
    Calculate vertical distance between two boxes.
    """

    return abs(
        bbox_center_y(bbox1)
        - bbox_center_y(bbox2)
    )


def detect_checkbox_groups(
    candidates,
):
    """
    Detect regularly spaced vertical checkbox groups.

    Example:

        checkbox
        checkbox
        checkbox
        checkbox
        checkbox

    Instead of treating these as unrelated objects, annotate
    them as belonging to the same checkbox group.
    """

    checkboxes = [
        candidate
        for candidate in candidates
        if candidate["type"] == "possible_checkbox"
    ]

    if not checkboxes:
        return candidates

    # --------------------------------------------------------
    # Sort by x then y
    # --------------------------------------------------------

    checkboxes.sort(
        key=lambda candidate: (
            bbox_center_x(candidate["bbox"]),
            bbox_center_y(candidate["bbox"]),
        )
    )

    groups = []

    current_group = []

    for checkbox in checkboxes:

        if not current_group:
            current_group = [checkbox]
            continue

        previous = current_group[-1]

        same_column = are_same_checkbox_column(
            checkbox["bbox"],
            previous["bbox"],
        )

        gap = checkbox_vertical_gap(
            checkbox["bbox"],
            previous["bbox"],
        )

        regular_gap = (
            CHECKBOX_GROUP_Y_GAP_MIN
            <= gap
            <= CHECKBOX_GROUP_Y_GAP_MAX
        )

        if same_column and regular_gap:
            current_group.append(checkbox)

        else:
            groups.append(current_group)
            current_group = [checkbox]

    if current_group:
        groups.append(current_group)

    # --------------------------------------------------------
    # Annotate groups
    # --------------------------------------------------------

    group_id = 0

    grouped_lookup = {}

    for group in groups:

        if len(group) < MIN_CHECKBOX_GROUP_SIZE:
            continue

        group_id += 1

        for index, checkbox in enumerate(group):

            checkbox["checkbox_group_id"] = (
                f"checkbox_group_{group_id}"
            )

            checkbox["checkbox_group_index"] = index

            checkbox["checkbox_group_size"] = len(
                group
            )

            checkbox["confidence"] = 0.75

            grouped_lookup[
                id(checkbox)
            ] = True

    # --------------------------------------------------------
    # Non-grouped checkboxes remain individual candidates.
    # --------------------------------------------------------

    for candidate in candidates:

        if candidate["type"] != "possible_checkbox":
            continue

        if "checkbox_group_id" in candidate:
            continue

        # A standalone checkbox with a label is still useful.
        if candidate.get("possible_label"):
            candidate["confidence"] = 0.65

        else:
            candidate["confidence"] = 0.45

    return candidates


# ============================================================
# GENERAL CONFIDENCE
# ============================================================

def calculate_candidate_confidence(candidate):
    """
    Calculate candidate confidence based on field type,
    geometry, and label evidence.
    """

    candidate_type = candidate["type"]

    label_confidence = candidate.get(
        "label_confidence",
        0.0,
    )

    # --------------------------------------------------------
    # Line fields
    # --------------------------------------------------------

    if candidate_type == "possible_line_field":

        score = 0.45

        if candidate.get("possible_label"):
            score += 0.35

        score += min(
            label_confidence * 0.20,
            0.20,
        )

        return min(score, 1.0)

    # --------------------------------------------------------
    # Text fields
    # --------------------------------------------------------

    if candidate_type == "possible_text_field":

        score = 0.40

        if candidate.get("possible_label"):
            score += 0.35

        score += min(
            label_confidence * 0.25,
            0.25,
        )

        return min(score, 1.0)

    # --------------------------------------------------------
    # Checkbox
    # --------------------------------------------------------

    if candidate_type == "possible_checkbox":

        if "confidence" in candidate:
            return candidate["confidence"]

        if candidate.get("possible_label"):
            return 0.65

        return 0.45

    return 0.0


def add_confidence_scores(candidates):
    """
    Add final confidence score to every candidate.
    """

    for candidate in candidates:

        candidate["confidence"] = round(
            calculate_candidate_confidence(candidate),
            3,
        )

    return candidates


# ============================================================
# DUPLICATE / OVERLAP FILTERING
# ============================================================

def bbox_overlap(bbox1, bbox2):
    """
    Calculate intersection-over-union (IoU)
    between two bounding boxes.
    """

    x0 = max(
        bbox1["x0"],
        bbox2["x0"],
    )

    y0 = max(
        bbox1["y0"],
        bbox2["y0"],
    )

    x1 = min(
        bbox1["x1"],
        bbox2["x1"],
    )

    y1 = min(
        bbox1["y1"],
        bbox2["y1"],
    )

    intersection_width = max(
        0,
        x1 - x0,
    )

    intersection_height = max(
        0,
        y1 - y0,
    )

    intersection = (
        intersection_width
        * intersection_height
    )

    if intersection == 0:
        return 0.0

    area1 = (
        bbox_width(bbox1)
        * bbox_height(bbox1)
    )

    area2 = (
        bbox_width(bbox2)
        * bbox_height(bbox2)
    )

    union = (
        area1
        + area2
        - intersection
    )

    if union <= 0:
        return 0.0

    return intersection / union


def remove_duplicate_candidates(candidates):
    """
    Remove candidates that represent essentially the
    same visual field.

    When duplicates exist, prefer the candidate with:

        1. A label
        2. Higher confidence
    """

    filtered = []

    for candidate in candidates:

        duplicate_index = None

        for index, existing in enumerate(filtered):

            overlap = bbox_overlap(
                candidate["bbox"],
                existing["bbox"]
            )

            if overlap >= 0.80:
                duplicate_index = index
                break

        # ----------------------------------------------------
        # No duplicate.
        # ----------------------------------------------------

        if duplicate_index is None:
            filtered.append(candidate)
            continue

        existing = filtered[duplicate_index]

        # ----------------------------------------------------
        # Determine which candidate is better.
        # ----------------------------------------------------

        candidate_label = bool(
            candidate.get("possible_label")
        )

        existing_label = bool(
            existing.get("possible_label")
        )

        candidate_confidence = candidate.get(
            "confidence",
            0
        )

        existing_confidence = existing.get(
            "confidence",
            0
        )

        candidate_is_better = (
            candidate_label and not existing_label
        ) or (
            candidate_label == existing_label
            and candidate_confidence > existing_confidence
        )

        if candidate_is_better:
            filtered[duplicate_index] = candidate

    return filtered


# ============================================================
# SORTING
# ============================================================

def sort_candidates(candidates):
    """
    Sort candidates top-to-bottom and left-to-right.
    """

    return sorted(
        candidates,
        key=lambda candidate: (
            candidate["bbox"]["y0"],
            candidate["bbox"]["x0"],
        ),
    )


# ============================================================
# PAGE CLASSIFICATION
# ============================================================

def classify_page(page_data):
    """
    Classify possible form fields on one page.

    Expected input:

    {
        "page_number": ...,
        "words": [...],
        "drawings": [...],
        "widgets": [...]
    }
    """

    words = page_data.get(
        "words",
        [],
    )

    drawings = page_data.get(
        "drawings",
        [],
    )

    page_width = page_data.get(
        "page_width",
        DEFAULT_PAGE_WIDTH,
    )

    page_height = page_data.get(
        "page_height",
        DEFAULT_PAGE_HEIGHT,
    )

    # --------------------------------------------------------
    # Detect drawing-based candidates
    # --------------------------------------------------------

    candidates = classify_drawings(
        drawings,
        page_width=page_width,
        page_height=page_height,
    )

    # --------------------------------------------------------
    # Attach nearby labels
    # --------------------------------------------------------

    candidates = enrich_candidates(
    candidates,
    words
)

# --------------------------------------------------------
# Group geometrically related checkboxes
# --------------------------------------------------------

    candidates = group_checkboxes(
        candidates
    )

    # --------------------------------------------------------
    # Detect checkbox groups
    # --------------------------------------------------------

    candidates = detect_checkbox_groups(
        candidates
    )

    candidates = enrich_checkbox_options(
    candidates,
    words
    )

    # --------------------------------------------------------
    # Add confidence
    # --------------------------------------------------------

    candidates = add_confidence_scores(
        candidates
    )

    # --------------------------------------------------------
    # Remove duplicate visual candidates
    # --------------------------------------------------------

    candidates = remove_duplicate_candidates(
        candidates
    )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    candidates = sort_candidates(
        candidates
    )

    return {
        "page_number": page_data["page_number"],
        "candidates": candidates,
    }


# ============================================================
# COMPLETE DOCUMENT CLASSIFICATION
# ============================================================

def classify_document(pages):
    """
    Classify all pages in an inspected PDF.
    """

    results = []

    for page in pages:

        result = classify_page(page)

        results.append(result)

    return results


# ============================================================
# PRINT CLASSIFICATION
# ============================================================

def print_classification(results):
    """
    Print a compact classification summary.
    """

    print("\n" + "=" * 80)
    print("FIELD CLASSIFICATION")
    print("=" * 80)

    total = 0

    for page in results:

        candidates = page["candidates"]

        print(
            f"\nPAGE {page['page_number']}"
        )

        print(
            f"Candidate fields: {len(candidates)}"
        )

        for candidate in candidates:

            group = ""

            if "checkbox_group_id" in candidate:
                group = (
                    f" "
                    f"group={candidate['checkbox_group_id']}"
                    f"[{candidate['checkbox_group_index'] + 1}/"
                    f"{candidate['checkbox_group_size']}]"
                )

            print(
                f"  [{candidate['type']}] "
                f"confidence={candidate['confidence']:.2f} "
                f"{candidate['bbox']} "
                f"label='{candidate['possible_label']}'"
                f"{group}"
            )

            total += 1

    print("\n" + "-" * 80)
    print(
        f"TOTAL CANDIDATES: {total}"
    )
    print("-" * 80)


# ============================================================
# LINE CLASSIFICATION
# ============================================================

def print_line_classification(results):
    """
    Print only candidates that are based on horizontal lines.
    """

    print("\n" + "=" * 80)
    print("LINE-BASED FIELD CANDIDATES")
    print("=" * 80)

    total = 0

    for page in results:

        for candidate in page["candidates"]:

            if candidate["type"] != "possible_line_field":
                continue

            print(
                f"Page {page['page_number']} | "
                f"confidence={candidate['confidence']:.2f} | "
                f"{candidate['bbox']} | "
                f"label='{candidate['possible_label']}'"
            )

            total += 1

    print("\n" + "-" * 80)
    print(
        f"TOTAL LINE CANDIDATES: {total}"
    )
    print("-" * 80)


# ============================================================
# CHECKBOX CLASSIFICATION
# ============================================================

def print_checkbox_classification(results):
    """
    Print checkbox candidates and their detected groups.
    """

    print("\n" + "=" * 80)
    print("CHECKBOX CANDIDATES")
    print("=" * 80)

    total = 0

    for page in results:

        for candidate in page["candidates"]:

            if candidate["type"] != "possible_checkbox":
                continue

            group = candidate.get(
                "checkbox_group_id",
                "standalone",
            )

            position = ""

            if group != "standalone":
                position = (
                    f" "
                    f"[{candidate['checkbox_group_index'] + 1}/"
                    f"{candidate['checkbox_group_size']}]"
                )

            print(
                f"Page {page['page_number']} | "
                f"{group}{position} | "
                f"{candidate['bbox']} | "
                f"label='{candidate['possible_label']}' | "
                f"confidence={candidate['confidence']:.2f}"
            )

            total += 1

    print("\n" + "-" * 80)
    print(
        f"TOTAL CHECKBOX CANDIDATES: {total}"
    )
    print("-" * 80)