import pymupdf
from pathlib import Path
from src.parser.form_parser import parse_pdf
from src.comparator.comparator import FormComparator


def test_resume_and_document_section_extraction(tmp_path):
    # Create Document 1 (Resume V1)
    doc1_path = tmp_path / "resume_v1.pdf"
    doc1 = pymupdf.open()
    p1 = doc1.new_page()
    p1.insert_text((50, 50), "SAYAN GHOSH\nSoftware Developer")
    p1.insert_text((50, 100), "PROFILE")
    p1.insert_text((50, 120), "B.Tech IT student with strong background in Python and Java.")
    p1.insert_text((50, 160), "TECHNICAL SKILLS")
    p1.insert_text((50, 180), "Languages: Java, Python, C")
    p1.insert_text((50, 200), "Databases: MySQL, SQLite")
    p1.insert_text((50, 240), "PROJECTS")
    p1.insert_text((50, 260), "• Student Performance Prediction System")
    p1.insert_text((50, 280), "• PDF Comparison Tool")
    p1.insert_text((50, 320), "SOFT SKILLS")
    p1.insert_text((50, 340), "• Problem Solving\n• Teamwork")
    doc1.save(str(doc1_path))
    doc1.close()

    # Create Document 2 (Resume V2)
    doc2_path = tmp_path / "resume_v2.pdf"
    doc2 = pymupdf.open()
    p2 = doc2.new_page()
    p2.insert_text((50, 50), "SAYAN GHOSH\nSoftware Developer")
    p2.insert_text((50, 100), "CAREER OBJECTIVE")
    p2.insert_text((50, 120), "Enthusiastic student looking to gain practical experience.")
    p2.insert_text((50, 160), "SKILLS")
    p2.insert_text((50, 180), "• Python\n• Java\n• JavaScript")
    p2.insert_text((50, 240), "TECHNICAL PROJECTS")
    p2.insert_text((50, 260), "• Personal Portfolio Website")
    p2.insert_text((50, 280), "• PDF Comparison Tool")
    p2.insert_text((50, 320), "LANGUAGES")
    p2.insert_text((50, 340), "• English\n• Hindi")
    doc2.save(str(doc2_path))
    doc2.close()

    parsed1 = parse_pdf(doc1_path)
    parsed2 = parse_pdf(doc2_path)

    # Verify sections were detected
    texts1 = [q.text.upper() for q in parsed1["questions"]]
    texts2 = [q.text.upper() for q in parsed2["questions"]]

    assert any("TECHNICAL SKILLS" in t or "SKILLS" in t for t in texts1)
    assert any("PROJECTS" in t for t in texts1)
    assert any("SKILLS" in t for t in texts2)
    assert any("PROJECTS" in t for t in texts2)

    # Run comparator
    comparator = FormComparator()
    result = comparator.compare(parsed1["questions"], parsed2["questions"])

    diff_types = {d.difference_type for d in result.differences}
    # Differences must detect changes (added/removed/modified sections or options)
    assert len(result.differences) > 0
    assert "QUESTION_ADDED" in diff_types or "QUESTION_REMOVED" in diff_types or "OPTIONS_ADDED" in diff_types or "OPTIONS_CHANGED" in diff_types


def test_general_paragraph_document_extraction(tmp_path):
    doc_path = tmp_path / "memo.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((50, 60), "Introduction")
    p.insert_text((50, 80), "This is the first paragraph describing project goals.")
    p.insert_text((50, 150), "Conclusion")
    p.insert_text((50, 170), "This is the final paragraph summarizing results.")
    doc.save(str(doc_path))
    doc.close()

    parsed = parse_pdf(doc_path)
    assert len(parsed["questions"]) >= 2
