from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app
import pymupdf


def make_sample_pdf(path: Path, title: str, text: str):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), f"{title}\n1. {text}\n")
    doc.save(str(path))
    doc.close()


def test_api_health():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "offline"


def test_favicon():
    client = TestClient(app)
    res_ico = client.get("/favicon.ico")
    assert res_ico.status_code == 200
    res_svg = client.get("/favicon.svg")
    assert res_svg.status_code == 200


def test_api_compare_and_reports(tmp_path):
    client = TestClient(app)
    pdf1 = tmp_path / "old.pdf"
    pdf2 = tmp_path / "new.pdf"
    make_sample_pdf(pdf1, "Form V1", "What is your full name?")
    make_sample_pdf(pdf2, "Form V2", "What is your complete legal name?")

    with open(pdf1, "rb") as f1, open(pdf2, "rb") as f2:
        response = client.post(
            "/api/compare",
            files={
                "old_pdf": ("old.pdf", f1, "application/pdf"),
                "new_pdf": ("new.pdf", f2, "application/pdf"),
            },
            data={"threshold": "0.4"},
        )

    assert response.status_code == 200
    res = response.json()
    assert res["ok"] is True
    assert "token" in res
    assert "payload" in res
    assert "reports" in res

    token = res["token"]
    for kind in ["json", "html", "pdf", "xlsx"]:
        rep = client.get(f"/api/report/{token}/{kind}")
        assert rep.status_code == 200
        assert len(rep.content) > 0
