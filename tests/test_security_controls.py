from pathlib import Path

import pytest

from src.security import security_status, validate_pdf_input, verify_offline_core


def test_pdf_input_validation_rejects_non_pdf(tmp_path):
    path = tmp_path / "not_a_pdf.txt"
    path.write_text("not a pdf", encoding="utf-8")
    with pytest.raises(ValueError, match="Only PDF"):
        validate_pdf_input(path)


def test_pdf_input_validation_rejects_oversize(tmp_path):
    path = tmp_path / "large.pdf"
    path.write_bytes(b"0" * 1025)
    with pytest.raises(ValueError, match="exceeds"):
        validate_pdf_input(path, max_size_bytes=1024)


def test_security_status_is_local_only():
    status = security_status()
    assert status["local_processing"] is True
    assert status["external_ai_required"] is False
    assert status["pdf_content_logged"] is False
    assert status["password_bypass_attempted"] is False
    assert status["temporary_work_files_created_by_core"] is False


def test_offline_verification_reports_no_cloud_dependency_required():
    status = verify_offline_core()
    assert status["mode"] == "offline"
    assert status["network_calls_in_comparison_core"] is False
    assert status["cloud_ai_dependency_required"] is False


def test_input_path_is_resolved_and_regular_file(tmp_path):
    path = tmp_path / "sample.pdf"
    path.write_bytes(b"%PDF-1.4")
    resolved = validate_pdf_input(path)
    assert resolved == path.resolve()
