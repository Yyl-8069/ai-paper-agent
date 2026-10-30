import json
import re
import uuid
from pathlib import Path
from app.store import atomic_text,digest

def plan_cleanup(root,selection,mode,store):
    if Path(root).resolve()!=store.root or mode not in {"pdf","markdown","summary","all"}:
        raise ValueError("清理范围或方式无效")
    refs=set(selection.get("refs",[]));reports=set(selection.get("reports",[]))
    for ref in refs:store.lookup(ref)
    report_rows={r["id"]:r for r in store.reports()}
    if not reports<=report_rows.keys():raise ValueError("未知总结编号")
    chosen_reports={report_rows[r]["path"] for r in reports}
    arts=store.artifacts()
    selected=[]
    for a in arts:
        if a["status"]!="present":continue
        match=(a["ref"] in refs and a["kind"] in {
            "pdf":{"pdf"},"markdown":{"markdown","asset"},"summary":set(),
            "all":{"pdf","markdown","asset","validation","metadata"}}[mode])
        match=match or (mode in {"summary","all"} and a["path"] in chosen_reports)
        if match:selected.append(a)
    selected_paths={a["path"] for a in selected}
    remaining_md=[store.safe_path(a["path"]) for a in arts
                  if a["kind"]=="markdown" and a["path"] not in selected_paths
                  and store.safe_path(a["path"]).exists()]
    # Preserve an asset if another registered document references it.
    protected=set()
    for md in remaining_md:
        for match in re.findall(r"!\[[^\]]*\]\(([^)]+)\)",md.read_text(encoding="utf-8")):
            try:protected.add((md.parent/match.strip("<>")).resolve())
            except (OSError,ValueError):pass
    targets=[]
    for a in selected:
        p=store.safe_path(a["path"])
        if a["kind"]=="asset" and p in protected:continue
        if p.exists():
            if not p.is_file():raise ValueError("清理目标不是普通文件")
            targets.append({"path":a["path"],"kind":a["kind"],"ref":a["ref"],
                            "sha256":digest(p),"size":p.stat().st_size,
                            "mtime_ns":p.stat().st_mtime_ns})
    plan={"id":uuid.uuid4().hex,"root":str(store.root),"mode":mode,
          "targets":targets,"bytes_total":sum(t["size"] for t in targets)}
    directory=store.safe_path("temp/cleanup");directory.mkdir(parents=True,exist_ok=True)
    atomic_text(directory/(plan["id"]+".json"),json.dumps(plan,ensure_ascii=False,indent=2))
    return plan

def execute_cleanup(plan,confirmation,store):
    ident=plan.get("id","")
    if not re.fullmatch("[a-f0-9]{32}",ident) or confirmation!=ident:
        raise ValueError("删除尚未确认")
    saved=store.safe_path("temp/cleanup/"+ident+".json")
    if json.loads(saved.read_text(encoding="utf-8"))!=plan or plan["root"]!=str(store.root):
        raise ValueError("删除预览发生变化")
    registered={a["path"] for a in store.artifacts()}
    for item in plan["targets"]:
        p=store.safe_path(item["path"])
        if item["path"] not in registered:raise ValueError("未登记目标")
        if p.exists() and (not p.is_file() or digest(p)!=item["sha256"]
                           or p.stat().st_mtime_ns!=item["mtime_ns"]):
            raise ValueError("文件已变化，请重新预览")
    result={"deleted":[],"missing":[],"failed":[]}
    for item in plan["targets"]:
        try:
            p=store.safe_path(item["path"])
            if p.exists():
                if digest(p)!=item["sha256"] or p.stat().st_mtime_ns!=item["mtime_ns"]:
                    raise ValueError("文件已变化")
                p.unlink();result["deleted"].append(item["path"])
            else:result["missing"].append(item["path"])
            with store.connect() as c:
                c.execute("UPDATE artifacts SET status='deleted' WHERE path=?",(item["path"],))
        except (OSError,ValueError) as e:
            result["failed"].append({"path":item["path"],"error":type(e).__name__})
    store.event(ident,"cleanup",result)
    store.export_index()
    return result
