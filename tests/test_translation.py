import json
from datetime import datetime, timezone
import httpx
import pytest
from app.store import Store
from agents.researcher import Researcher
from test_store import candidate

def test_calendar_boundaries():
    from tools.search import range_start
    end=datetime(2024,3,31,12,tzinfo=timezone.utc)
    assert range_start("month",end).isoformat()=="2024-02-29T12:00:00+00:00"
    assert range_start("half_year",end).isoformat()=="2023-09-30T12:00:00+00:00"
    assert range_start("year",datetime(2024,2,29,tzinfo=timezone.utc)).day==28
    assert (end-range_start("day",end)).days==1
    assert (end-range_start("week",end)).days==7

def test_translation_chunks_cache_preservation_and_cleanup(tmp_path):
    from workflows.translate import translate_paper
    from tools.cleanup import plan_cleanup
    s=Store(tmp_path);ref=s.register(candidate())
    p=s.directory(ref)/"paper.md";p.parent.mkdir(parents=True)
    text="# Research\n\n"+("A result $x^2$ [source](https://example.org).\n\n"*200)
    p.write_text(text,encoding="utf-8");s.record_artifact(ref,"markdown",p)
    supplied=[]
    def respond(request):
        body=json.loads(request.content);part=body["messages"][-1]["content"];supplied.append(part)
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{
            "content":json.dumps({"translation":part.replace("Research","研究").replace("A result","结果")})}}],
            "usage":{"total_tokens":10}})
    with httpx.Client(transport=httpx.MockTransport(respond)) as c:
        model=Researcher("test-only",client=c)
        result=translate_paper(s,ref,model)
        translated=s.safe_path(result["path"]).read_text(encoding="utf-8")
        assert len(supplied)>1 and translated.count("$x^2$")==200
        assert translated.count("https://example.org")==200 and "结果" in translated and ref in translated
        assert p.read_text(encoding="utf-8")==text
        assert translate_paper(s,ref,model)["cached"]
        assert len(supplied)==result["chunks"]
    targets=plan_cleanup(s.root,{"refs":[ref]},"markdown",s)["targets"]
    assert any(t["path"].endswith("paper.zh.md") for t in targets)

def test_bad_model_output_never_publishes_translation(tmp_path):
    from workflows.translate import translate_paper
    s=Store(tmp_path);ref=s.register(candidate())
    p=s.directory(ref)/"paper.md";p.parent.mkdir(parents=True)
    p.write_text("Research $x$.",encoding="utf-8");s.record_artifact(ref,"markdown",p)
    for reason in ("length","stop"):
        def respond(request):
            return httpx.Response(200,json={"choices":[{"finish_reason":reason,"message":{
                "content":json.dumps({"translation":"遗漏公式"})}}]})
        with httpx.Client(transport=httpx.MockTransport(respond)) as c:
            with pytest.raises(ValueError):translate_paper(s,ref,Researcher("test-only",client=c))
        assert not p.with_name("paper.zh.md").exists()

def test_missing_fulltext_rejected(tmp_path):
    from workflows.translate import translate_paper
    s=Store(tmp_path);ref=s.register(candidate())
    with pytest.raises(ValueError,match="Markdown"):translate_paper(s,ref,None)

def test_c_storage_rejected():
    import os
    if os.name!="nt":pytest.skip("Windows policy")
    with pytest.raises(ValueError,match="C"):Store("C:/paper-agent-must-not-create")

def test_translation_endpoint_guards(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.server import create_app
    monkeypatch.delenv("DEEPSEEK_API_KEY",raising=False)
    app=create_app(tmp_path/"library",tmp_path/".env")
    ref=app.state.store.register(candidate())
    with TestClient(app,base_url="http://127.0.0.1") as c:
        assert c.post("/api/translate",json={"ref":ref}).status_code==403
        h={"X-Local-Token":c.get("/api/session").json()["token"]}
        assert c.post("/api/translate",headers=h,json={"ref":"unknown"}).status_code==404
        assert c.post("/api/translate",headers=h,json={"ref":ref}).status_code==422

def test_hot_candidates_obey_date_range(monkeypatch):
    import app.cli as cli
    from datetime import timedelta
    end=datetime.now(timezone.utc)
    recent={**candidate(),"published_at":(end-timedelta(hours=1)).isoformat()}
    old={**candidate(),"source_id":"2001.00001","published_at":(end-timedelta(days=400)).isoformat()}
    monkeypatch.setattr(cli,"hot_papers",lambda limit:[{**recent,"evidence":{"upvotes":3}},{**old,"evidence":{"upvotes":4}}])
    monkeypatch.setattr(cli,"arxiv_by_ids",lambda ids:[recent,old])
    assert [p["source_id"] for p in cli.fetch_candidates("hot",7,5,"","day")]==[recent["source_id"]]

def test_translation_api_success_and_missing_key(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    import app.server as server
    monkeypatch.delenv("DEEPSEEK_API_KEY",raising=False)
    app=server.create_app(tmp_path/"library",tmp_path/".env")
    s=app.state.store;ref=s.register(candidate())
    p=s.directory(ref)/"paper.md";p.parent.mkdir(parents=True)
    p.write_text("# Research\n\nOriginal result $x$.\n",encoding="utf-8")
    s.record_artifact(ref,"markdown",p)
    def respond(request):
        data=json.loads(request.content)
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{"content":
            json.dumps({"translation":data["messages"][-1]["content"].replace("Research","研究")})}}]})
    with TestClient(app,base_url="http://127.0.0.1") as c:
        h={"X-Local-Token":c.get("/api/session").json()["token"]}
        assert c.post("/api/translate",headers=h,json={"ref":ref}).status_code==422
        with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
            monkeypatch.setattr(server,"Researcher",lambda *args:Researcher("test-only",client=transport))
            response=c.post("/api/translate",headers=h,json={"ref":ref})
        assert response.status_code==202
        job=c.get("/api/jobs/"+response.json()["job_id"]).json()
        assert job["status"]=="succeeded",job
        files=c.get("/api/papers").json()[0]["files"]
        translated=next(f for f in files if f["path"].endswith("paper.zh.md"))
        assert "研究" in c.get("/api/files",params={"path":translated["path"]}).text

def test_orphan_translation_is_not_overwritten(tmp_path):
    from workflows.translate import translate_paper
    s=Store(tmp_path);ref=s.register(candidate())
    p=s.directory(ref)/"paper.md";p.parent.mkdir(parents=True)
    p.write_text("Original text",encoding="utf-8");s.record_artifact(ref,"markdown",p)
    target=p.with_name("paper.zh.md");target.write_text("Keep my edited translation",encoding="utf-8")
    with pytest.raises(ValueError,match="译文"):translate_paper(s,ref,None)
    assert target.read_text(encoding="utf-8")=="Keep my edited translation"
