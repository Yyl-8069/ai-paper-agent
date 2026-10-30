from pathlib import Path
import pytest
from app.store import Store
from tools.cleanup import plan_cleanup,execute_cleanup
from workflows.collect import collect_candidates
from test_store import candidate

def test_restore_pdf_even_when_markdown_remains(tmp_path):
    s=Store(tmp_path);ref=s.register(candidate());d=s.directory(ref);d.mkdir(parents=True)
    (d/"paper.md").write_text("# Paper\n\nContent.\n")
    old=d/"original.pdf";old.write_bytes(b"%PDF-removed");s.record_artifact(ref,"pdf",old);old.unlink()
    with s.connect() as c:c.execute("UPDATE artifacts SET status='deleted' WHERE kind='pdf'")
    def download(c,target):target.write_bytes(b"%PDF-restored");return target
    r=collect_candidates([candidate()],s,downloader=download,restore=True)
    assert r["refs"]==[ref]
    assert old.read_bytes()==b"%PDF-restored"
    assert next(a for a in s.artifacts() if a["kind"]=="pdf")["status"]=="present"

@pytest.mark.parametrize("markup",[
    "![figure][fig]\n\n[fig]: ../papers/P000001/v1/assets/figure.png\n",
    '<img src="../papers/P000001/v1/assets/figure.png">\n'])
def test_report_reference_or_html_image_protects_asset(tmp_path,markup):
    s=Store(tmp_path);ref=s.register(candidate());d=s.directory(ref);(d/"assets").mkdir(parents=True)
    md=d/"paper.md";md.write_text("# Paper\n");s.record_artifact(ref,"markdown",md)
    asset=d/"assets/figure.png";asset.write_bytes(b"image");s.record_artifact(ref,"asset",asset)
    report=tmp_path/"briefs/report.md";report.parent.mkdir();report.write_text(markup)
    s.record_report(dict(id="brief",kind="brief",period="2026",path=report,references=[ref],coverage={}))
    p=plan_cleanup(tmp_path,{"refs":[ref]},"markdown",s)
    assert all(t["kind"]!="asset" for t in p["targets"])

def test_changed_surviving_document_dependency_invalidates_preview(tmp_path):
    s=Store(tmp_path);ref=s.register(candidate());d=s.directory(ref);(d/"assets").mkdir(parents=True)
    asset=d/"assets/figure.png";asset.write_bytes(b"image");s.record_artifact(ref,"asset",asset)
    md=d/"paper.md";md.write_text("# Paper\n");s.record_artifact(ref,"markdown",md)
    other=s.register({**candidate(),"source_id":"2401.00004"})
    otherdir=s.directory(other);otherdir.mkdir(parents=True)
    survivor=otherdir/"paper.md";survivor.write_text("# Other\n");s.record_artifact(other,"markdown",survivor)
    p=plan_cleanup(tmp_path,{"refs":[ref]},"markdown",s)
    survivor.write_text("![image](../../P000001/v1/assets/figure.png)\n")
    with pytest.raises(ValueError):
        execute_cleanup(p,p["id"],s)
    assert asset.exists()
    assert md.exists()
