import json
import re
import uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
from app.store import atomic_text
from tools.validate import validate_markdown

BEIJING=timezone(timedelta(hours=8))

def week_bounds(week):
    match=re.fullmatch(r"([0-9]{4})-W([0-9]{2})",week)
    if not match:raise ValueError("周格式应为 2026-W44")
    start=datetime.fromisocalendar(int(match[1]),int(match[2]),1).replace(tzinfo=BEIJING)
    return start.astimezone(timezone.utc),(start+timedelta(days=7)).astimezone(timezone.utc)

def _material(store,p):
    path=store.directory(p["ref"])/"paper.md"
    if path.exists():
        text=path.read_text(encoding="utf-8");coverage="extracted_unverified"
    else:
        text=p.get("abstract","");coverage="abstract_only" if text.strip() else "missing_content"
    return {"ref":p["ref"],"title":p["title"],"text":text,"coverage":coverage,
            "evidence":p.get("evidence",{})}

def materials_for(store,refs):
    return [_material(store,store.lookup(ref)) for ref in refs]

def write_report(store,kind,period,data):
    if kind not in {"brief","weekly"}:raise ValueError("报告类型无效")
    ident=uuid.uuid4().hex
    heading="每周总结" if kind=="weekly" else "本次收集简报"
    refs=sorted({ref for s in data["sections"] for ref in s["refs"]})
    for ref in refs:store.lookup(ref)
    coverage=data["coverage"]
    cutoff=datetime.now(BEIJING).isoformat(timespec="seconds")
    lines=[f"# {heading} {period}","",f"Generated / coverage cutoff: {cutoff}",""]
    for section in data["sections"]:
        title=" ".join(section["heading"].split()).lstrip("# ")
        lines += [f"## {title}","",section["text"].strip(),"",
                  "依据编号："+ "、".join(section["refs"]),""] if section["refs"] else [
                    f"## {title}","",section["text"].strip(),""]
    lines+=["## 材料覆盖情况",""]
    for ref,cov in coverage.items():
        lines.append(f"- {ref}：{cov}")
    lines+=["","说明：extracted_unverified 为未经人工完整性核对的转换文本；"
            "abstract_only 为仅摘要；excerpt 为正文节选。",""]
    folder="weekly" if kind=="weekly" else "briefs"
    path=store.safe_path(Path(folder)/(period+"-"+ident[:8]+".md"))
    atomic_text(path,"\n".join(lines).rstrip()+"\n")
    validation=validate_markdown(path)
    atomic_text(path.with_suffix(".validation.json"),json.dumps(validation,ensure_ascii=False,indent=2))
    report={"id":ident,"kind":kind,"period":period,"path":path,"references":refs,
            "coverage":coverage,"validation":validation}
    store.record_report(report)
    store.record_artifact(None,"validation",path.with_suffix(".validation.json"))
    store.event(ident,"report",{"kind":kind,"references":refs,"validation":validation["status"],
                              "usage":data.get("usage",[])})
    return report

def summarize_week(week,store,researcher=None,force=False):
    start,end=week_bounds(week)
    deleted={a["path"] for a in store.artifacts() if a["status"]=="deleted"}
    history=sorted([r for r in store.reports() if r["kind"]=="weekly" and r["period"]==week],key=lambda r:r["created"])
    if not force and history and history[-1]["path"] in deleted:
        raise ValueError("Report was intentionally deleted; use --force to regenerate")
    existing=[r for r in store.reports() if r["kind"]=="weekly" and r["period"]==week
              and store.safe_path(r["path"]).exists()]
    papers=[p for p in store.papers() if start<=datetime.fromisoformat(p["collected"])<end]
    if existing and not force:
        r=existing[-1]
        if {p["ref"] for p in papers}<=set(r["coverage"]):
            return {**r,"path":store.safe_path(r["path"])}
    if not papers:
        data={"sections":[{"heading":"本周情况","text":"本周无新增收集论文。","refs":[]}],"coverage":{}}
    else:
        if researcher is None:raise ValueError("请配置 DeepSeek 后生成周报")
        data=researcher.summarize([_material(store,p) for p in papers],"weekly")
    return write_report(store,"weekly",week,data)

def due_weeks(now,store):
    local=now.astimezone(BEIJING)
    current_start=local.date()-timedelta(days=local.weekday())
    groups={}
    current_due=local.weekday()==6 and local.hour>=21
    for p in store.papers():
        d=datetime.fromisoformat(p["collected"]).astimezone(BEIJING).date()
        if d<current_start or current_due:
            iso=d.isocalendar();week=f"{iso.year}-W{iso.week:02d}"
            groups.setdefault(week,set()).add(p["ref"])
    deleted={a["path"] for a in store.artifacts() if a["status"]=="deleted"}
    due=[]
    reports=store.reports()
    for week,refs in groups.items():
        previous=[r for r in reports if r["kind"]=="weekly" and r["period"]==week]
        previous.sort(key=lambda r:r["created"])
        if previous and previous[-1]["path"] in deleted:continue
        if not any(store.safe_path(r["path"]).exists() and refs<=set(r["coverage"]) for r in previous):
            due.append(week)
    return sorted(due)
