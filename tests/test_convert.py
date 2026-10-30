from pathlib import Path
import pymupdf
import pytest
from tools.convert import convert_pdf
from tools.validate import validate_markdown

def make_pdf(path, text="Research paper\nA useful result with enough text for extraction."):
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72,72),text)
        doc.save(path)

def test_actual_pdf_conversion_and_lint_are_separate(tmp_path):
    source=tmp_path/"input.pdf"
    make_pdf(source)
    result=convert_pdf(source,tmp_path/"out",timeout=40)
    text=Path(result["markdown_path"]).read_text(encoding="utf-8")
    assert "useful result" in text
    assert result["completeness"] == "needs_review"
    assert result["pages"] == 1
    lint=validate_markdown(Path(result["markdown_path"]))
    assert lint["status"] in {"passed","issues"}
    assert "issues" in lint

def test_blank_pdf_does_not_count_as_full_text(tmp_path):
    source=tmp_path/"empty.pdf"
    with pymupdf.open() as doc:
        doc.new_page()
        doc.save(source)
    with pytest.raises(ValueError,match="text"):
        convert_pdf(source,tmp_path/"out",timeout=40)

def test_linter_reports_real_line_rule(tmp_path):
    path=tmp_path/"bad.md"
    path.write_text("# Heading\ntext\n",encoding="utf-8")
    r=validate_markdown(path)
    assert r["status"] == "issues"
    assert any(x["line"] == 1 for x in r["issues"])
    assert all(x["rule"] for x in r["issues"])
