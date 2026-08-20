# FormDiff — Personal Project Status

## Completed

- Local PDF extraction with PyMuPDF
- Spatial text/question parsing
- Option and field-type extraction
- Deterministic question matching
- Local vector similarity signal
- Added/removed/modified/reordered detection
- Question renumbering detection
- Child-question comparison foundation
- Password-protected PDF handling
- PDF validation and size limits
- Local/offline comparison path
- JSON, HTML, PDF and Excel reports
- Automated regression/security/report tests
- Local web application
- Drag-and-drop PDF upload
- Question-by-question side-by-side comparison viewer
- Match confidence and signal inspection
- Added/removed question visualization
- Search and result filtering

## Current limitation

The current semantic layer is a dependency-light local vector representation, not a trained proprietary LLM. OCR for image-only PDFs is not claimed as supported by the current core.

## Intended deployment model

The application binds to localhost for the personal web UI. The comparison core does not require a cloud AI service or network access. Enterprise deployment should additionally enforce OS/container/network controls appropriate to the organization's security policy.
