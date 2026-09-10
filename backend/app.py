"""FastAPI backend application for FormDiff."""

from __future__ import annotations

import mimetypes
import os
import secrets
import tempfile
from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from fastapi.responses import (
    JSONResponse,
    FileResponse,
    Response,
)

from fastapi.staticfiles import (
    StaticFiles,
)

from backend.service import (
    MAX_SIZE,
    build_payload,
    write_reports,
    _create_highlighted_pdfs,
)

from src.security import (
    security_status,
    verify_offline_core,
)


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent.parent
)


if (
    os.environ.get("VERCEL")
    or os.environ.get(
        "AWS_LAMBDA_FUNCTION_NAME"
    )
):

    RUNTIME_DIR = (
        Path(tempfile.gettempdir())
        / "formdiff_runtime"
    )

else:

    RUNTIME_DIR = (
        BASE_DIR
        / ".runtime"
    )


RUNTIME_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


FRONTEND_DIST = (
    BASE_DIR
    / "frontend"
    / "dist"
)


FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg"
viewBox="0 0 32 32" width="32" height="32">
<rect width="32" height="32" rx="6" fill="#0f172a"/>
<text x="16" y="21" fill="#14b8a6"
font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
font-size="14" font-weight="800"
text-anchor="middle"
letter-spacing="-0.5">FD</text>
</svg>"""


app = FastAPI(
    title="FormDiff API",
    description="Offline PDF Comparison API",
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# FAVICON
# =========================================================


@app.get(
    "/favicon.ico",
    include_in_schema=False,
)
@app.get(
    "/favicon.svg",
    include_in_schema=False,
)
async def favicon():

    fav_svg = (
        BASE_DIR
        / "frontend"
        / "public"
        / "favicon.svg"
    )

    if fav_svg.is_file():

        return FileResponse(
            fav_svg,
            media_type="image/svg+xml",
        )

    return Response(
        content=FAVICON_SVG,
        media_type="image/svg+xml",
    )


# =========================================================
# HEALTH CHECK
# =========================================================


@app.get("/api/health")
async def health():

    return {
        "status": "ok",
        "mode": "offline",
        "security": security_status(),
        "offline": verify_offline_core(),
    }


# =========================================================
# SAVE UPLOADED PDF
# =========================================================


def _save_upload(
    upload: UploadFile,
    workdir: Path,
    label: str,
) -> Path:

    if (
        not upload
        or not upload.filename
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                f"{label} PDF is required."
            ),
        )

    filename = Path(
        upload.filename
    ).name

    if (
        Path(filename)
        .suffix.lower()
        != ".pdf"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                f"{label} must be a PDF file."
            ),
        )

    data = upload.file.read()

    if len(data) > MAX_SIZE:

        raise HTTPException(
            status_code=400,
            detail=(
                f"{label} PDF exceeds "
                "50 MB limit."
            ),
        )

    target = (
        workdir
        / f"{secrets.token_hex(8)}_{filename}"
    )

    target.write_bytes(
        data
    )

    return target


# =========================================================
# PDF COMPARISON
# =========================================================


@app.post("/api/compare")
async def compare(
    old_pdf: UploadFile = File(...),
    new_pdf: UploadFile = File(...),
    old_password: str | None = Form(None),
    new_password: str | None = Form(None),
    threshold: float = Form(0.45),
):

    try:

        threshold = min(
            max(
                float(threshold),
                0.0,
            ),
            1.0,
        )

        # =================================================
        # CREATE ISOLATED WORK DIRECTORY
        # =================================================

        workdir = Path(
            tempfile.mkdtemp(
                prefix="fpct_",
                dir=RUNTIME_DIR,
            )
        )

        # =================================================
        # SAVE ORIGINAL PDF
        # =================================================

        old_path = _save_upload(
            old_pdf,
            workdir,
            "Original",
        )

        # =================================================
        # SAVE REVISED PDF
        # =================================================

        new_path = _save_upload(
            new_pdf,
            workdir,
            "Revised",
        )

        # =================================================
        # EXISTING COMPARISON ENGINE
        # =================================================

        payload = build_payload(
            old_path,
            new_path,
            old_password or None,
            new_password or None,
            threshold,
        )

        # =================================================
        # EXISTING REPORTS
        # =================================================

        paths = write_reports(
            payload,
            workdir,
        )

        # =================================================
        # WHOLE-PDF HIGHLIGHTING
        # =================================================

        highlighted_paths = (
            _create_highlighted_pdfs(
                old_path=old_path,
                new_path=new_path,

                # NEW:
                # Use every text element from
                # the entire PDF.
                old_text_elements=payload[
                    "_old_text_elements"
                ],

                new_text_elements=payload[
                    "_new_text_elements"
                ],

                workdir=workdir,

                # Passwords are passed so that
                # encrypted PDFs can also be
                # opened for highlighting.
                old_password=(
                    old_password or None
                ),

                new_password=(
                    new_password or None
                ),
            )
        )

        # =================================================
        # REPORT URLS
        # =================================================

        token = workdir.name

        reports = {
            key: (
                f"/api/report/"
                f"{token}/{key}"
            )
            for key in paths
        }

        # =================================================
        # HIGHLIGHTED PDF URLS
        # =================================================

        highlighted_pdfs = {}

        if highlighted_paths.get(
            "old_highlighted_pdf"
        ):

            highlighted_pdfs[
                "original"
            ] = (
                f"/api/highlighted/"
                f"{token}/original"
            )

        if highlighted_paths.get(
            "new_highlighted_pdf"
        ):

            highlighted_pdfs[
                "revised"
            ] = (
                f"/api/highlighted/"
                f"{token}/revised"
            )

        # =================================================
        # REMOVE INTERNAL DATA
        # =================================================

        json_payload = {
            key: value
            for key, value
            in payload.items()
            if not key.startswith("_")
        }

        # =================================================
        # RESPONSE
        # =================================================

        return JSONResponse(
            {
                "ok": True,

                "token": token,

                "payload": json_payload,

                "reports": reports,

                "highlighted_pdfs": (
                    highlighted_pdfs
                ),
            }
        )

    except HTTPException:

        raise

    except Exception as exc:

        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": str(exc),
            },
        )


# =========================================================
# EXISTING REPORT DOWNLOAD / VIEW
# =========================================================


@app.get(
    "/api/report/{token}/{kind}"
)
async def get_report(
    token: str,
    kind: str,
):

    if kind not in {
        "json",
        "html",
        "pdf",
        "xlsx",
    }:

        raise HTTPException(
            status_code=404,
            detail=(
                "Unsupported report format."
            ),
        )

    p = (
        RUNTIME_DIR
        / token
        / f"comparison.{kind}"
    )

    if not p.is_file():

        raise HTTPException(
            status_code=404,
            detail=(
                "Report not found "
                "or expired."
            ),
        )

    content_types = {
        "json": "application/json",

        "html": (
            "text/html; charset=utf-8"
        ),

        "pdf": "application/pdf",

        "xlsx": (
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    }

    media_type = content_types.get(
        kind,
        mimetypes.guess_type(
            str(p)
        )[0]
        or "application/octet-stream",
    )

    return FileResponse(
        p,
        media_type=media_type,
        filename=(
            f"comparison.{kind}"
        ),
    )


# =========================================================
# HIGHLIGHTED PDF ENDPOINT
# =========================================================


@app.get(
    "/api/highlighted/{token}/{side}"
)
async def get_highlighted_pdf(
    token: str,
    side: str,
):

    if side == "original":

        filename = (
            "comparison_original_highlighted.pdf"
        )

    elif side == "revised":

        filename = (
            "comparison_revised_highlighted.pdf"
        )

    else:

        raise HTTPException(
            status_code=404,
            detail=(
                "Unsupported highlighted PDF."
            ),
        )

    p = (
        RUNTIME_DIR
        / token
        / filename
    )

    if not p.is_file():

        raise HTTPException(
            status_code=404,
            detail=(
                "Highlighted PDF not found "
                "or expired."
            ),
        )

    return FileResponse(
        p,
        media_type="application/pdf",
        filename=filename,
    )


# =========================================================
# SERVE REACT FRONTEND
# =========================================================


if FRONTEND_DIST.is_dir():

    app.mount(
        "/",
        StaticFiles(
            directory=str(
                FRONTEND_DIST
            ),
            html=True,
        ),
        name="frontend",
    )