from datetime import datetime,timezone
from app.store import Store
from workflows.reports import due_weeks,summarize_week
from test_store import candidate

def test_sunday_21_includes_current_week_and_late_additions(tmp_path):
    s=Store(tmp_path);ref=s.register(candidate())
    with s.connect() as c:c.execute("UPDATE versions SET collected=? WHERE ref=?",("2026-10-30T00:00:00+00:00",ref))
    assert due_weeks(datetime(2026,11,1,12,59,tzinfo=timezone.utc),s)==[]
    assert due_weeks(datetime(2026,11,1,13,0,tzinfo=timezone.utc),s)==["2026-W44"]
    class Fake:
        def summarize(self,materials,kind):
            return {"sections":[{"heading":"Overview","text":"Based on abstracts.","refs":[p["ref"] for p in materials]}],
                    "coverage":{p["ref"]:p["coverage"] for p in materials},"usage":[]}
    first=summarize_week("2026-W44",s,Fake())
    other=s.register({**candidate(),"source_id":"2401.00003"})
    with s.connect() as c:
        c.execute("UPDATE versions SET collected=? WHERE ref=?",("2026-11-01T14:00:00+00:00",other))
    assert due_weeks(datetime(2026,11,8,13,0,tzinfo=timezone.utc),s)==["2026-W44"]
    updated=summarize_week("2026-W44",s,Fake())
    assert updated["id"]!=first["id"]
    assert other in updated["references"]
    assert first["path"].exists()
