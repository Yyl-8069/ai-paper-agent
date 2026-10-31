import json
import time
from pathlib import Path
import pymupdf
import pytest
from fastapi.testclient import TestClient
from app.server import create_app
from app.cli import library_lock
from test_store import candidate


@pytest.fixture
def web(tmp_path,monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY",raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL",raising=False)
    application=create_app(tmp_path/"library",config_path=tmp_path/".env")
    with TestClient(application,base_url="http://127.0.0.1") as client:
        token=client.get("/api/session").json()["token"]
        yield application,client,{"X-Local-Token":token}


def test_health_index_and_openapi(web):
    app,c,h=web
    assert c.get("/health").json()["status"]=="ok"
    assert c.get("/").status_code==200
    assert "/api/cleanup/execute" in c.get("/openapi.json").json()["paths"]
    assert c.get("/api/papers").json()==[]
    assert c.get("/api/reports").json()==[]


def test_mutations_need_token_and_same_origin(web):
    app,c,h=web
    assert c.post("/api/search",json={}).status_code==403
    assert c.post("/api/search",headers={**h,"Origin":"https://evil.test"},json={}).status_code==403
    assert c.get("/health",headers={"Host":"evil.test"}).status_code==400


def test_config_never_echoes_key_or_validation_input(web):
    app,c,h=web
    secret="test-key-never-return"
    r=c.put("/api/config",headers=h,json={"api_key":secret,"model":"deepseek-flash"})
    assert r.status_code==200 and r.json()["key_configured"]
    assert secret not in r.text
    assert secret not in c.get("/api/config").text
    bad=c.put("/api/config",headers=h,json={"api_key":secret,"model":"bad\nmodel"})
    assert bad.status_code==422 and secret not in bad.text
    assert app.state.config_path.read_text().count(secret)==1


def test_search_then_collect_uses_server_candidates_and_tracks_failure(web,monkeypatch):
    app,c,h=web
    import app.server as server
    monkeypatch.setattr(server,"fetch_candidates",lambda *a:[candidate()])
    result=c.post("/api/search",headers=h,json={"limit":1}).json()
    assert result["candidates"][0]["source_id"]=="1706.03762"
    search_id=result["search_id"]
    rejected=c.post("/api/collect",headers=h,json={"search_id":search_id,"indices":[0],"summarize":False})
    assert rejected.status_code==422
    def fail(*a,**k):raise RuntimeError("simulated source outage")
    monkeypatch.setattr(server,"collect_candidates",fail)
    accepted=c.post("/api/collect",headers=h,json={"search_id":search_id,"indices":[1],"summarize":False})
    assert accepted.status_code==202
    job=c.get("/api/jobs/"+accepted.json()["job_id"]).json()
    assert job["status"]=="failed" and "RuntimeError" in job["error"]


def test_import_pdf_job_archives_and_downloads_only_registered_files(web):
    app,c,h=web
    with pymupdf.open() as doc:
        page=doc.new_page()
        page.insert_text((72,72),"An AI paper\nMeaningful experiments and useful research results.")
        content=doc.tobytes()
    r=c.post("/api/import?title=Test&filename=original.pdf",headers={**h,"Content-Type":"application/pdf"},content=content)
    assert r.status_code==202
    job=c.get("/api/jobs/"+r.json()["job_id"]).json()
    assert job["status"]=="succeeded",job
    papers=c.get("/api/papers").json()
    assert papers[0]["ref"]=="P000001/v1"
    file=next(f for f in papers[0]["files"] if f["kind"]=="markdown")
    download=c.get("/api/files",params={"path":file["path"]})
    assert download.status_code==200 and "research" in download.text
    assert "attachment" in download.headers["content-disposition"]
    hidden=app.state.store.root/"private.txt";hidden.write_text("private")
    assert c.get("/api/files",params={"path":"private.txt"}).status_code==404
    assert c.get("/api/files",params={"path":"../.env"}).status_code==404


def test_invalid_pdf_is_rejected_and_not_queued(web):
    app,c,h=web
    r=c.post("/api/import",headers={**h,"Content-Type":"application/pdf"},content=b"not PDF")
    assert r.status_code==422
    assert c.get("/api/jobs").json()==[]


def test_cleanup_is_two_step_confirmation_and_stale_target_rejected(web):
    app,c,h=web
    store=app.state.store;ref=store.register(candidate())
    d=store.directory(ref);d.mkdir(parents=True)
    p=d/"original.pdf";p.write_bytes(b"%PDF-test");store.record_artifact(ref,"pdf",p)
    preview=c.post("/api/cleanup/preview",headers=h,json={"mode":"pdf","refs":[ref]}).json()
    wrong=c.post("/api/cleanup/execute",headers=h,json={"plan_id":preview["id"],"confirmation":"NO"})
    assert wrong.status_code==422 and p.exists()
    p.write_bytes(b"%PDF-changed")
    stale=c.post("/api/cleanup/execute",headers=h,json={"plan_id":preview["id"],"confirmation":"DELETE"})
    assert stale.status_code==409 and p.exists()
    fresh=c.post("/api/cleanup/preview",headers=h,json={"mode":"pdf","refs":[ref]}).json()
    deleted=c.post("/api/cleanup/execute",headers=h,json={"plan_id":fresh["id"],"confirmation":"DELETE"})
    assert deleted.status_code==200 and not p.exists()
    assert store.lookup(ref)["title"]=="Attention Is All You Need"


def test_busy_library_returns_conflict_instead_of_accepting_work(web):
    app,c,h=web
    with library_lock(app.state.store.root):
        r=c.post("/api/weekly",headers=h,json={"week":"2026-W44"})
    assert r.status_code==409


def test_restart_marks_unfinished_jobs_interrupted(tmp_path):
    from app.store import Store
    from app.jobs import JobRunner
    store=Store(tmp_path/"library")
    JobRunner(store)
    with store.connect() as db:
        db.execute("INSERT INTO api_jobs(id,kind,status,created,updated,result,error) VALUES(?,?,?,?,?,?,?)",
                   ("dead","collect","running","2026","2026",None,None))
    second=create_app(store.root,config_path=tmp_path/".env")
    with TestClient(second,base_url="http://127.0.0.1") as client:
        assert client.get("/api/jobs/dead").json()["status"]=="interrupted"
