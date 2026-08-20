# FormDiff Local Web App

## Run

```bash
python run_local.py
```

Open:

`http://127.0.0.1:8000`

The server uses only Python's standard library for the web layer and binds to localhost. The comparison engine remains the existing PyMuPDF/local matcher core.

## Workflow

1. Select the original PDF.
2. Select the revised PDF.
3. Enter passwords only when a PDF is encrypted.
4. Adjust the matching threshold if required.
5. Click **Compare revisions**.
6. Review added, removed, modified and reordered changes.
7. Export JSON, HTML, PDF or Excel reports.

## Security boundary

The web application is intended for local use. It binds to `127.0.0.1` and does not call a cloud AI API. Uploaded PDFs are written to a temporary local runtime directory for processing and report generation. A production deployment should add authenticated access, OS-level/network controls, persistent storage policy, retention cleanup, and other enterprise controls as required by the organization.

## Question comparison viewer

The local web UI includes a question-by-question comparison viewer. Each matched question can be expanded to inspect:

- Original and revised question text
- Question number changes
- Field type
- Extracted options
- Child-question information
- Match confidence
- Local matching signals (text, local vector, options, field, position and neighbour context)

Unmatched questions are shown explicitly as **Added** or **Removed**. The viewer supports filters for all, changed, unchanged, and unmatched questions, plus text search.

The viewer is generated entirely from the local comparison payload; it does not render or upload the source PDF to a remote service.
