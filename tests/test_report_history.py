from datetime import datetime,timezone
from app.store import Store
from tools.cleanup import plan_cleanup,execute_cleanup
from workflows.reports import write_report,summarize_week,due_weeks
from test_store import candidate

def test_deleting_old_weekly_does_not_disable_newer_weekly_or_late_update(tmp_path):
    s=Store(tmp_path);ref=s.register(candidate())
    with s.connect() as c:c.execute("UPDATE versions SET collected=? WHERE ref=?",("2026-10-28T00:00:00+00:00",ref))
    data={"sections":[{"heading":"Overview","text":"Based on abstracts.","refs":[ref]}],"coverage":{ref:"abstract_only"}}
    old=write_report(s,"weekly","2026-W44",data)
    newer=write_report(s,"weekly","2026-W44",data)
    plan=plan_cleanup(tmp_path,{"reports":[old["id"]]},"summary",s)
    execute_cleanup(plan,plan["id"],s)
    assert summarize_week("2026-W44",s)["path"]==newer["path"]
    ref2=s.register({**candidate(),"source_id":"2401.00005"})
    with s.connect() as c:c.execute("UPDATE versions SET collected=? WHERE ref=?",("2026-10-29T00:00:00+00:00",ref2))
    assert due_weeks(datetime(2026,11,2,2,tzinfo=timezone.utc),s)==["2026-W44"]

def test_forced_rebuild_clears_effective_deletion_suppression(tmp_path):
    s=Store(tmp_path)
    old=summarize_week("2026-W44",s)
    plan=plan_cleanup(tmp_path,{"reports":[old["id"]]},"summary",s)
    execute_cleanup(plan,plan["id"],s)
    rebuilt=summarize_week("2026-W44",s,force=True)
    assert rebuilt["path"].exists()
    assert summarize_week("2026-W44",s)["path"]==rebuilt["path"]
