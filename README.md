# Form PDF Comparison Tool — Offline Core

A local-first engine for comparing revisions of form PDFs without requiring Gemini or another cloud AI API.

## Current architecture

```text
PDF V1 ──┐
         ├─> PyMuPDF extraction ─> spatial parser ─> Question[] ─┐
PDF V2 ──┘                                                       │
                                                                 ▼
                                                   local question matcher
                                                   normalized/fuzzy/structure
                                                                 │
                                                                 ▼
                                                        local comparator
                                                                 │
                                          added/removed/reordered/modified
                                                                 │
                                                                 ▼
                                                        HTML / JSON report
```

## Why this architecture

The core comparison does not send PDF content to a third-party AI service. PDF extraction, question parsing, matching, comparison and summary generation run locally.

The `src/llm/` package is intentionally left as an extension point. A future locally deployed model can be added for semantic matching or natural-language summarization without making cloud AI a prerequisite for the core comparison.

## Features implemented

- PyMuPDF-based text/coordinate extraction
- Spatial row reconstruction
- Numbered-question detection for `1 Question` and `1. Question` formats
- Checkbox and plain-text option extraction
- Field-type inference
- One-to-one question matching independent of question number
- Text similarity + meaningful-token guard + structural signals
- Ranked matching diagnostics for reviewing why questions were paired
- Per-difference match confidence in JSON/HTML output
- Added/removed question detection
- Question renumbering detection
- Question order detection based on matched identities rather than numbers
- Question text, options, field-type and child-logic comparison
- Deterministic local summary
- HTML/JSON reports
- Password-protected PDF detection and local authentication
- No network/API dependency in the active comparison pipeline

## Run

```bash
pip install -r requirements.txt

python app.py data/samples/samplev1.pdf data/samples/samplev2.pdf \
  --json output/comparison.json \
  --html output/comparison.html \
  --diagnostics output/matching_diagnostics.json
```

For encrypted PDFs:

```bash
python app.py old.pdf new.pdf --old-password "..." --new-password "..."
```

If the password is missing or incorrect, processing stops with a clear error. The application does not attempt to bypass PDF protection.

## Offline verification

Run the comparison with Wi-Fi disabled. The active pipeline imports only PyMuPDF and Python standard-library modules; there is no Gemini/OpenAI/network call in the comparison path.

## Security posture

- PDF processing is local-first; the active core has no Gemini/OpenAI/cloud API dependency.
- The parser validates the `.pdf` extension and applies a configurable 50 MB default file-size limit.
- Encrypted PDFs require the correct password and are authenticated locally through PyMuPDF.
- The application never attempts to bypass PDF encryption.
- The comparison core does not log PDF text or transmit document contents.
- Temporary-file cleanup and OS-level sandboxing should still be added/reviewed before enterprise deployment.

## Manager-facing architecture

The current prototype does **not** claim to train an LLM. Its core intelligence is our deterministic extraction, spatial parsing, question representation, matching and comparison logic. The `src/llm/` package is an extension point for a future locally deployed model. This distinction is important: the prototype can run with Wi-Fi disabled and does not require a third-party AI service to compare the supplied form revisions.

## Current limitations

- The parser is optimized for the supplied sample forms and should be evaluated against additional form families before production use.
- Image-only/scanned PDFs require OCR; the current parser intentionally does not claim OCR support.
- Semantic matching is deterministic fuzzy/structural matching. A small locally deployed embedding model can be added later if required.
- A production security review would still be required for enterprise deployment.


## Security / offline verification

The CLI includes a local security status in JSON output. It records that the
active comparison path does not require external AI, does not intentionally
log PDF content, does not bypass password protection, and does not create
temporary work files as part of the core parser/comparator.

Run:

```bash
python app.py data/samples/samplev1.pdf data/samples/samplev2.pdf --json output/comparison.json
```

and inspect the `security` and `offline_verification` objects.

The offline verification is an application-level declaration/check, not an
OS firewall or sandbox. For enterprise deployment, run the application inside
an organization-controlled host/container with outbound network policy,
least-privilege file permissions, dependency scanning, and other required
controls.

## Local web application

The project includes a localhost-only UI. Install the requirements and run:

```bash
python -m pip install -r requirements.txt
python run_local.py
```

Then open `http://127.0.0.1:8000` in a browser. The UI uploads both PDFs to the local application, runs the existing offline comparison core, and exposes JSON/HTML/PDF/Excel reports. The Flask server binds to `127.0.0.1` by default.
