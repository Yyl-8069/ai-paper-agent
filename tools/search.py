import re
from datetime import datetime,timezone
import feedparser
import httpx

ARXIV="https://export.arxiv.org/api/query"
CATEGORIES="cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV OR cat:cs.RO OR cat:stat.ML"
ID_PATTERN=r"(?:[0-9]{4}\.[0-9]{4,5}|[a-z-]+(?:\.[A-Z]{2})?/[0-9]{7})"

def parse_id(value):
    value=value.removeprefix("https://arxiv.org/abs/").removeprefix("http://arxiv.org/abs/")
    match=re.fullmatch(f"({ID_PATTERN})(?:v([1-9][0-9]*))?",value)
    if not match:
        raise ValueError("无效 arXiv ID")
    return match[1],int(match[2]) if match[2] else None

def _entries(content):
    feed=feedparser.parse(content)
    if feed.bozo:
        raise ValueError("arXiv 返回了无法解析的元数据")
    result=[]
    for e in feed.entries:
        sid,v=parse_id(e.id)
        if v is None:
            raise ValueError("来源未提供版本")
        result.append(dict(source="arxiv",source_id=sid,version=v,
            title=" ".join(e.title.split()),authors=[a.name for a in e.get("authors",[])],
            abstract=" ".join(e.summary.split()),published_at=e.published,
            pdf_url=f"https://arxiv.org/pdf/{sid}v{v}",evidence={}))
    return result

def search_papers(query,start,end,limit,client=None):
    if not 1<=limit<=100 or start>=end:
        raise ValueError("数量需为 1–100，起始时间必须早于结束时间")
    period=f"submittedDate:[{start.astimezone(timezone.utc):%Y%m%d%H%M} TO {end.astimezone(timezone.utc):%Y%m%d%H%M}]"
    expr=f"({CATEGORIES}) AND {period}"
    if query.strip():
        terms=re.findall(r"[\w-]+",query,flags=re.UNICODE)
        if not terms:
            raise ValueError("请输入有效关键词")
        expr+=" AND ("+" AND ".join("all:"+t for t in terms[:12])+")"
    owned=client is None
    client=client or httpx.Client(timeout=45,follow_redirects=False,trust_env=False)
    try:
        r=client.get(ARXIV,params=dict(search_query=expr,start=0,max_results=limit,
                     sortBy="submittedDate",sortOrder="descending"))
        r.raise_for_status()
        rows=_entries(r.content)
        return [p for p in rows if start<=datetime.fromisoformat(p["published_at"].replace("Z","+00:00"))<=end]
    finally:
        if owned:client.close()

def arxiv_by_ids(ids,client=None):
    clean=[]
    for value in ids:
        sid,v=parse_id(value)
        clean.append(sid+(f"v{v}" if v else ""))
    owned=client is None
    client=client or httpx.Client(timeout=45,trust_env=False)
    try:
        r=client.get(ARXIV,params={"id_list":",".join(clean),"max_results":len(clean)})
        r.raise_for_status()
        return _entries(r.content)
    finally:
        if owned:client.close()

def hot_papers(limit,client=None):
    if not 1<=limit<=100:raise ValueError("数量需为 1–100")
    owned=client is None
    client=client or httpx.Client(timeout=45,trust_env=False)
    try:
        r=client.get("https://huggingface.co/api/daily_papers")
        r.raise_for_status()
        rows=r.json()
        if not isinstance(rows,list):raise ValueError("热门来源格式异常")
        result=[]
        for row in rows:
            p=row["paper"];sid,_=parse_id(p["id"])
            votes=p.get("upvotes")
            if type(votes) is not int or votes<0:continue
            result.append(dict(source="arxiv",source_id=sid,version=None,
                title=p["title"],authors=[a["name"] for a in p.get("authors",[])],
                published_at=p["publishedAt"],abstract=p.get("summary",""),pdf_url=None,
                evidence={"source":"https://huggingface.co/papers/"+sid,
                          "upvotes":votes,"observed_at":datetime.now(timezone.utc).isoformat()}))
        return sorted(result,key=lambda p:p["evidence"]["upvotes"],reverse=True)[:limit]
    finally:
        if owned:client.close()

def range_start(period, end):
    """Calendar ranges use Beijing local time and clip invalid month-end days."""
    import calendar
    from datetime import timedelta
    local = end.astimezone(timezone(timedelta(hours=8)))
    if period in {"day", "week"}:
        return end - timedelta(days=1 if period == "day" else 7)
    months = {"month": 1, "half_year": 6, "year": 12}
    if period not in months:raise ValueError("无效时间范围")
    index = local.year*12 + local.month-1-months[period]
    year, month = divmod(index, 12)
    start = local.replace(year=year, month=month+1,
                          day=min(local.day, calendar.monthrange(year, month+1)[1]))
    return start.astimezone(end.tzinfo)
