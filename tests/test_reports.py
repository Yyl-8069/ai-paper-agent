from datetime import datetime,timezone
import json
import httpx
import pytest
from app.store import Store
from agents.researcher import Researcher
from workflows.reports import write_report,week_bounds,due_weeks,summarize_week
from test_store import candidate

def test_deepseek_payload_and_unknown_reference_rejected():
    def handle(request):
        body=json.loads(request.content)
        assert request.url.host=="api.deepseek.com"
        assert body["model"]=="deepseek-flash"
        assert "Authorization" in request.headers
        return httpx.Response(200,json={"choices":[{"message":{"content":json.dumps({
            "sections":[{"heading":"研究","text":"结果","refs":["P999999/v1"]}]})}}],
            "usage":{"prompt_tokens":10,"completion_tokens":5}})
    with httpx.Client(transport=httpx.MockTransport(handle)) as c:
        researcher=Researcher("test-only",client=c)
        with pytest.raises(ValueError,match="reference"):
            researcher.summarize([{"ref":"P000001/v1","text":"Source"}],"brief")

def test_report_saved_with_real_validation_and_reference_lookup(tmp_path):
    s=Store(tmp_path);ref=s.register(candidate())
    data={"sections":[{"heading":"研究进展","text":"基于摘要，研究 Transformer。","refs":[ref]}],
          "coverage":{ref:"abstract_only"},"usage":[]}
    report=write_report(s,"brief","2026-10-30",data)
    assert report["path"].is_file()
    assert ref in report["path"].read_text(encoding="utf-8")
    assert report["validation"]["status"]=="passed"
    assert s.reports()[0]["refs"]==[ref]

def test_week_boundary_is_beijing_and_empty_week_no_model_call(tmp_path):
    start,end=week_bounds("2026-W44")
    assert start.isoformat()=="2026-10-25T16:00:00+00:00"
    assert end.isoformat()=="2026-11-01T16:00:00+00:00"
    s=Store(tmp_path)
    report=summarize_week("2026-W44",s,researcher=None)
    assert "无新增" in report["path"].read_text(encoding="utf-8")
    assert summarize_week("2026-W44",s,researcher=None)["path"]==report["path"]

def test_late_start_due_weeks_and_missing_fulltext(tmp_path):
    s=Store(tmp_path);ref=s.register(candidate())
    with s.connect() as c:
        c.execute("UPDATE versions SET collected=? WHERE ref=?",("2026-10-28T00:00:00+00:00",ref))
    assert due_weeks(datetime(2026,11,2,2,tzinfo=timezone.utc),s)==["2026-W44"]
    class Fake:
        def summarize(self,materials,kind):
            assert materials[0]["coverage"]=="abstract_only"
            return {"sections":[{"heading":"摘要归纳","text":"仅基于摘要。","refs":[ref]}],
                    "coverage":{ref:"abstract_only"},"usage":[]}
    r=summarize_week("2026-W44",s,Fake())
    assert r["coverage"][ref]=="abstract_only"
    assert due_weeks(datetime(2026,11,2,2,tzinfo=timezone.utc),s)==[]

def test_missing_key_stops_before_network():
    with pytest.raises(ValueError,match="DEEPSEEK_API_KEY"):
        Researcher("")
