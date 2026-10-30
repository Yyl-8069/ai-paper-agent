import argparse
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
import getpass
import json
import os
from pathlib import Path
import sys
from app.config import PROJECT,researcher
from app.store import Store,atomic_text
from tools.search import search_papers,hot_papers,arxiv_by_ids
from tools.cleanup import plan_cleanup,execute_cleanup
from workflows.collect import collect_candidates,import_pdf
from workflows.reports import materials_for,write_report,summarize_week,due_weeks,BEIJING

@contextmanager
def library_lock(root):
    lock=root/".operation.lock"
    try:
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError("资料库有任务正在执行；若曾强制终止，确认无任务后删除 .operation.lock")
    try:
        os.write(fd,str(os.getpid()).encode());os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)

def print_result(value):
    print(json.dumps(value,ensure_ascii=False,indent=2,default=str))

def configure():
    key=getpass.getpass("输入 DeepSeek API Key（不显示，保存到本机 .env）：").strip()
    if not key or any(c.isspace() for c in key):raise ValueError("密钥为空或包含空白")
    model=input("模型名称 [deepseek-flash]：").strip() or "deepseek-flash"
    if any(c.isspace() for c in model):raise ValueError("模型名称无效")
    atomic_text(PROJECT/".env","DEEPSEEK_API_KEY="+key+"\nDEEPSEEK_MODEL="+model+"\n")
    print("配置已保存。PDF 本机解析；生成摘要和周报时会把提取文本发送到 DeepSeek，并产生 API 费用。")

def previous_week():
    d=datetime.now(BEIJING).date()
    previous=d-timedelta(days=d.weekday()+1)
    iso=previous.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"

def fetch_candidates(mode,days,limit,query):
    if mode=="hot":
        hot=hot_papers(limit)
        if not hot:return []
        canonical=arxiv_by_ids([p["source_id"] for p in hot])
        by_id={p["source_id"]:p for p in canonical}
        return [{**by_id[p["source_id"]],"evidence":p["evidence"]}
                for p in hot if p["source_id"] in by_id]
    end=datetime.now(timezone.utc)
    return search_papers(query,end-timedelta(days=days),end,limit)

def select_cleanup(store,mode,refs,reports,since=None,until=None):
    if refs==["all"]:refs=[p["ref"] for p in store.papers()]
    if since or until:
        start=datetime.fromisoformat(since).replace(tzinfo=BEIJING) if since else datetime.min.replace(tzinfo=BEIJING)
        end=datetime.fromisoformat(until).replace(tzinfo=BEIJING)+timedelta(days=1) if until else datetime.max.replace(tzinfo=BEIJING)
        dated={p["ref"] for p in store.papers() if start<=datetime.fromisoformat(p["collected"])<end}
        refs=sorted(dated & set(refs)) if refs else sorted(dated)
    plan=plan_cleanup(store.root,{"refs":refs,"reports":reports},mode,store)
    print_result(plan)
    print(f"预计释放 {plan['bytes_total']/1024/1024:.2f} MiB；删除后无法直接撤销。")
    if not plan["targets"]:
        print("没有符合条件的文件。");return
    if input("确认以上清单请输入 DELETE，其余输入取消：").strip()=="DELETE":
        print_result(execute_cleanup(plan,plan["id"],store))
    else:print("已取消。")

def show(store):
    store.export_index()
    print((store.root/"index.md").read_text(encoding="utf-8"))
    print("简报和周报：")
    for r in store.reports():print(r["id"],r["kind"],r["period"],r["path"])

def menu(store):
    while True:
        print("\nAI 论文助手\n1 配置 DeepSeek\n2 收集最新论文\n3 收集社区热门论文\n4 导入本地 PDF"
              "\n5 生成所选论文简报\n6 生成每周总结\n7 查看编号索引\n8 选择性清理\n0 退出")
        option=input("选择：").strip()
        try:
            if option=="0":return
            if option=="1":configure();continue
            if option=="7":show(store);continue
            with library_lock(store.root):
                if option in {"2","3"}:
                    ai=researcher()
                    limit=int(input("收集数量，最多 10 [5]：").strip() or "5")
                    if not 1<=limit<=10:raise ValueError("每批数量需在 1–10")
                    query=input("主题关键词，留空覆盖 AI：").strip() if option=="2" else ""
                    days=int(input("最近几天 [7]：").strip() or "7") if option=="2" else 7
                    candidates=fetch_candidates("latest" if option=="2" else "hot",days,limit,query)
                    for i,p in enumerate(candidates,1):print(i,p["title"],p["source_id"])
                    if not candidates:print("未找到论文。");continue
                    choice=input("选择要收集的序号，用逗号分隔；all 全选；留空取消：").strip()
                    if not choice:continue
                    picked=candidates if choice=="all" else [candidates[int(i)-1] for i in choice.split(",")]
                    result=collect_candidates(picked,store);print_result(result)
                    if result["refs"]:
                        data=ai.summarize(materials_for(store,result["refs"]),"brief")
                        print_result(write_report(store,"brief",datetime.now(BEIJING).date().isoformat(),data))
                elif option=="4":
                    source=input("PDF 路径：").strip().strip('"')
                    title=input("标题，留空使用文件名：").strip()
                    print_result(import_pdf(source,title,store))
                elif option=="5":
                    show(store)
                    refs=[r.strip() for r in input("论文编号，逗号分隔：").split(",") if r.strip()]
                    if not refs:continue
                    data=researcher().summarize(materials_for(store,refs),"brief")
                    print_result(write_report(store,"brief",datetime.now(BEIJING).date().isoformat(),data))
                elif option=="6":
                    week=input(f"周编号 [{previous_week()}]：").strip() or previous_week()
                    print_result(summarize_week(week,store,researcher()))
                elif option=="8":
                    show(store)
                    modes={"1":"pdf","2":"markdown","3":"summary","4":"all"}
                    mode=modes[input("1 只删PDF；2 只删Markdown；3 只删总结；4 全部删除：").strip()]
                    refs=[r.strip() for r in input("论文编号，逗号分隔；all 全选；留空不选论文：").split(",") if r.strip()]
                    reports=[r.strip() for r in input("总结ID，逗号分隔；留空保留所有总结：").split(",") if r.strip()]
                    select_cleanup(store,mode,refs,reports)
                else:print("请选择菜单中的选项。")
        except (Exception,KeyboardInterrupt) as error:
            print("任务未完成："+str(error))

def main(argv=None):
    parser=argparse.ArgumentParser(description="本地 AI 论文收集与周报")
    parser.add_argument("--library",type=Path,default=PROJECT/"library")
    commands=parser.add_subparsers(dest="command")
    commands.add_parser("configure")
    commands.add_parser("list")
    commands.add_parser("catch-up")
    p=commands.add_parser("search");p.add_argument("--mode",choices=["latest","hot"],default="latest")
    p.add_argument("--days",type=int,default=7);p.add_argument("--limit",type=int,default=5);p.add_argument("--query",default="")
    p=commands.add_parser("collect");p.add_argument("--mode",choices=["latest","hot"],default="latest")
    p.add_argument("--days",type=int,default=7);p.add_argument("--limit",type=int,default=5);p.add_argument("--query",default="")
    p.add_argument("--no-summary",action="store_true");p.add_argument("--restore",action="store_true")
    p=commands.add_parser("import-pdf");p.add_argument("path",type=Path);p.add_argument("--title",default="")
    p=commands.add_parser("brief");p.add_argument("refs",nargs="+")
    p=commands.add_parser("weekly");p.add_argument("--week",default=None);p.add_argument("--force",action="store_true")
    p=commands.add_parser("cleanup");p.add_argument("--mode",choices=["pdf","markdown","summary","all"],required=True)
    p.add_argument("--refs",nargs="*",default=[]);p.add_argument("--reports",nargs="*",default=[])
    p.add_argument("--since");p.add_argument("--until")
    args=parser.parse_args(argv)
    store=Store(args.library)
    if args.command is None:return menu(store)
    if args.command=="configure":return configure()
    if args.command=="list":return show(store)
    if args.command=="search":return print_result(fetch_candidates(args.mode,args.days,args.limit,args.query))
    with library_lock(store.root):
        if args.command=="import-pdf":
            return print_result(import_pdf(args.path,args.title,store))
        if args.command=="collect":
            if not 1<=args.limit<=10:raise ValueError("每批最多 10 篇")
            ai=None if args.no_summary else researcher()
            rows=fetch_candidates(args.mode,args.days,args.limit,args.query)
            result=collect_candidates(rows,store,restore=args.restore);print_result(result)
            if ai and result["refs"]:
                data=ai.summarize(materials_for(store,result["refs"]),"brief")
                print_result(write_report(store,"brief",datetime.now(BEIJING).date().isoformat(),data))
            return
        if args.command=="brief":
            data=researcher().summarize(materials_for(store,args.refs),"brief")
            return print_result(write_report(store,"brief",datetime.now(BEIJING).date().isoformat(),data))
        if args.command=="weekly":
            return print_result(summarize_week(args.week or previous_week(),store,researcher(),args.force))
        if args.command=="catch-up":
            weeks=due_weeks(datetime.now(timezone.utc),store)
            if not weeks:return print("没有待补充的周总结。")
            ai=researcher()
            for week in weeks:print_result(summarize_week(week,store,ai))
            return
        if args.command=="cleanup":
            return select_cleanup(store,args.mode,args.refs,args.reports,args.since,args.until)

if __name__=="__main__":
    try:main()
    except KeyboardInterrupt:
        print("已取消。");sys.exit(130)
    except Exception as error:
        print("任务未完成："+str(error),file=sys.stderr);sys.exit(1)
