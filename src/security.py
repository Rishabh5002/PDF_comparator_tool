"""Local security controls for the offline comparison core.

These controls are intentionally small and auditable. They do not claim to be
an enterprise security boundary; deployment-level controls still belong to
the host/container environment.
"""
from __future__ import annotations

import importlib.util
import ipaddress
import socket
from pathlib import Path
from typing import Iterable

DEFAULT_MAX_PDF_BYTES = 50 * 1024 * 1024


class SecurityError(ValueError):
    """Raised when a local security/input policy is violated."""


def validate_pdf_input(path: str | Path, max_size_bytes: int = DEFAULT_MAX_PDF_BYTES) -> Path:
    """Validate a user-supplied PDF before opening it."""
    pdf_path = Path(path).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not pdf_path.is_file():
        raise SecurityError("Input path is not a regular file.")
    if pdf_path.suffix.lower() != ".pdf":
        raise SecurityError("Only PDF files are supported.")
    if pdf_path.stat().st_size > max_size_bytes:
        raise SecurityError(
            f"PDF exceeds the {max_size_bytes // (1024 * 1024)} MB local processing limit."
        )
    return pdf_path


def active_core_network_dependencies() -> list[str]:
    """Return cloud/network packages imported by the active core, if installed.

    This is a conservative dependency check, not a proof that arbitrary code
    on the host cannot access a network.
    """
    candidates = ("requests", "httpx", "openai", "google.generativeai", "google.genai")
    return [name for name in candidates if importlib.util.find_spec(name) is not None]


def verify_offline_core() -> dict:
    """Return an auditable status for the application's active core.

    The comparison engine itself does not import or call these packages. Their
    presence in the Python environment is therefore reported as a warning
    rather than treated as a failure.
    """
    deps = active_core_network_dependencies()
    return {
        "mode": "offline",
        "network_calls_in_comparison_core": False,
        "cloud_ai_dependency_required": False,
        "installed_cloud_network_packages": deps,
        "note": (
            "This verifies the application's declared dependency path; "
            "it is not an OS-level firewall or sandbox."
        ),
    }


def redact_filename(name: str) -> str:
    """Return a filename safe for metadata/logging; never include file content."""
    return Path(name).name[:255]


def security_status() -> dict:
    return {
        "local_processing": True,
        "external_ai_required": False,
        "pdf_content_logged": False,
        "password_bypass_attempted": False,
        "ocr_claimed": False,
        "default_max_pdf_mb": DEFAULT_MAX_PDF_BYTES // (1024 * 1024),
        "temporary_work_files_created_by_core": False,
        "enterprise_security_audit": False,
    }
