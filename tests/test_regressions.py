import json
from datetime import datetime,timezone
import pytest
from app.store import Store
from tools.cleanup import plan_cleanup,execute_cleanup
from workflows.reports import due_weeks,summarize_week,materials_for
from test_store import candidate

def test_deleted_weekly_not_recreated_by_catchup(tmp_path):
    s=Store(tmp_path);ref=s.register(candidate())
    with s.connect() as c:c.execute("UPDATE versions SET collected=? WHERE ref=?",("2026-10-28T00:00:00+00:00",ref))
    p=tmp_path/"weekly/a.md";p.parent.mkdir();p.write_text("# Report\n")
    s.record_report(dict(id="week",kind="weekly",period="2026-W44",path=p,references=[ref],coverage={}))
    plan=plan_cleanup(tmp_path,{"reports":["week"]},"summary",s)
    execute_cleanup(plan,plan["id"],s)
    assert due_weeks(datetime(2026,11,2,2,tzinfo=timezone.utc),s)==[]
    with pytest.raises(ValueError,match="force"):
        summarize_week("2026-W44",s)

def test_missing_local_fulltext_not_described_as_abstract(tmp_path):
    s=Store(tmp_path);p={**candidate(),"source":"local","abstract":""};ref=s.register(p)
    m=materials_for(s,[ref])[0]
    assert m["coverage"]=="missing_content"
    assert m["text"]==""

def test_cleanup_partial_failure_keeps_other_targets_and_records_state(tmp_path,monkeypatch):
    s=Store(tmp_path);ref=s.register(candidate());d=s.directory(ref);d.mkdir(parents=True)
    for name in ["a.pdf","b.pdf"]:
        path=d/name;path.write_bytes(b"original");s.record_artifact(ref,"pdf",path)
    plan=plan_cleanup(tmp_path,{"refs":[ref]},"pdf",s)
    from pathlib import Path
    real=Path.unlink
    def unlink(path,*a,**k):
        if path.name=="a.pdf":raise PermissionError("locked")
        return real(path,*a,**k)
    monkeypatch.setattr(Path,"unlink",unlink)
    result=execute_cleanup(plan,plan["id"],s)
    assert len(result["failed"])==1
    assert len(result["deleted"])==1
    assert (d/"a.pdf").exists()
    assert not (d/"b.pdf").exists()
