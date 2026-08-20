# Offline Architecture

## Pipeline

1. **PDF access** — validate file type/size and authenticate encrypted PDFs locally.
2. **Extraction** — PyMuPDF extracts words and their coordinates.
3. **Spatial reconstruction** — words are grouped into visually ordered rows.
4. **Question parsing** — numbered question rows start question blocks; following rows provide options/field evidence.
5. **Structured representation** — each question becomes a `Question` object containing number, text, field type, options, page and position metadata.
6. **Local matching** — normalized text, meaningful-token overlap, fuzzy similarity and small structural signals produce one-to-one matches independent of question number.
7. **Comparison** — matched questions are checked for text, options, field type, child logic and numbering; unmatched questions are classified as added/removed. Relative matched positions are used for reorder detection.
8. **Reporting** — deterministic summary plus JSON/HTML output.

## Why Gemini is not required

The original prototype used an external LLM for semantic normalization. The new local core moves the mandatory processing into deterministic code. This means confidential PDF content can remain on the machine and comparison can run without Wi-Fi.

## Future local model

A locally deployed embedding or small language model can be inserted behind the matcher interface if deterministic matching is insufficient. The model would be an optional inference component; the extraction and comparison engine remains our own code.


## Offline/security demonstration

1. Run the comparison with Wi-Fi disabled.
2. Show the JSON `mode`, `security`, and `offline_verification` fields.
3. Explain that the core reads the PDFs locally and does not create temporary
   extraction copies.
4. For encrypted PDFs, demonstrate a correct password and an incorrect
   password. The latter stops processing; no bypass is attempted.
5. For enterprise deployment, state explicitly that host/container network
   controls and a security review are still required.
