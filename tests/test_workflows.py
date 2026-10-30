import pymupdf
from app.store import Store
from workflows.collect import collect_candidates,import_pdf
from test_store import candidate

def test_import_keeps_user_original_and_deduplicates(tmp_path):
    source=tmp_path/"mine.pdf"
    with pymupdf.open() as d:
        p=d.new_page();p.insert_text((72,72),"An AI paper\nAn important experiment and useful results.");d.save(source)
    s=Store(tmp_path/"lib")
    a=import_pdf(source,"My paper",s)
    assert a["refs"]==["P000001/v1"]
    assert source.exists()
    directory=s.directory("P000001/v1")
    assert (directory/"original.pdf").is_file()
    assert (directory/"paper.md").is_file()
    assert (directory/"validation.json").is_file()
    again=import_pdf(source,"My paper",s)
    assert again["refs"]==a["refs"]
    assert len(s.papers())==1

def test_network_failure_is_recorded_and_no_false_success(tmp_path):
    s=Store(tmp_path)
    def fail(c,target):
        raise TimeoutError("download failed")
    result=collect_candidates([candidate()],s,downloader=fail)
    assert result["refs"]==[]
    assert result["failed"][0]["ref"]=="P000001/v1"
    assert s.lookup("P000001/v1")["state"]=="failed"

def test_deleted_files_not_silently_restored(tmp_path):
    s=Store(tmp_path);ref=s.register(candidate())
    d=s.directory(ref);d.mkdir(parents=True)
    pdf=d/"original.pdf";pdf.write_bytes(b"%PDF-")
    s.record_artifact(ref,"pdf",pdf)
    pdf.unlink()
    with s.connect() as c:c.execute("UPDATE artifacts SET status='deleted'")
    result=collect_candidates([candidate()],s)
    assert result["skipped"]==[ref]
    assert not pdf.exists()
