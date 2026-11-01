import httpx
import pytest
from datetime import datetime, timezone
from test_api import web
from test_store import candidate

ATOM = '''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
<opensearch:totalResults>25</opensearch:totalResults>
<entry><id>http://arxiv.org/abs/2401.00001v1</id><title>Agent harness</title><summary>Evaluation framework.</summary><published>2024-01-02T00:00:00Z</published><author><name>Jane</name></author></entry></feed>'''

def test_topic_search_historical_relevance_or_and_pagination():
    from tools.search import search_topic
    def handler(request):
        params=request.url.params
        expr=params["search_query"]
        assert "submittedDate" not in expr and "cat:" not in expr
        assert 'ti:"harness"' in expr and 'abs:"harness"' in expr
        assert 'abs:"evaluation framework"' in expr and " OR " in expr
        assert params["sortBy"]=="relevance" and params["start"]=="10"
        return httpx.Response(200,text=ATOM)
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        result=search_topic("harness","evaluation framework",None,datetime.now(timezone.utc),10,10,client=c)
    assert result["candidates"][0]["published_at"]=="2024-01-02T00:00:00Z"
    assert result["total"]==25 and result["has_more"] and result["offset"]==10

def test_topic_search_respects_optional_date_and_rejects_blank():
    from tools.search import search_topic
    def handler(request):
        assert "submittedDate:[202401010000 TO 202401030000]" in request.url.params["search_query"]
        return httpx.Response(200,text=ATOM)
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        result=search_topic("harness","",datetime(2024,1,1,tzinfo=timezone.utc),datetime(2024,1,3,tzinfo=timezone.utc),10,0,client=c)
        assert len(result["candidates"])==1
        with pytest.raises(ValueError):search_topic("!!!","",None,datetime.now(timezone.utc),10,0,client=c)

def test_topic_api_pages_have_independent_collection_snapshots(web,monkeypatch):
    import app.server as server
    app,c,h=web
    def topic(query,related,start,end,limit,offset):
        assert start is None and query=="harness"
        item={**candidate(),"source_id":"2401.00001" if offset else "1706.03762"}
        return {"candidates":[item],"total":2,"offset":offset,"has_more":offset==0}
    monkeypatch.setattr(server,"search_topic",topic,raising=False)
    pages=[]
    for offset in (0,1):
        response=c.post("/api/search",headers=h,json={"mode":"related","query":"harness","limit":1,"offset":offset})
        assert response.status_code==200,response.text
        pages.append(response.json())
    assert pages[0]["search_id"]!=pages[1]["search_id"]
    picked=[]
    monkeypatch.setattr(server,"collect_candidates",lambda chosen,*args,**kwargs: picked.extend(chosen) or {"refs":[]})
    response=c.post("/api/collect",headers=h,json={"search_id":pages[1]["search_id"],"indices":[1],"summarize":False})
    assert response.status_code==202 and picked[0]["source_id"]=="2401.00001"
    assert c.post("/api/search",headers=h,json={"mode":"related","query":"harness","offset":-1}).status_code==422

def test_search_cache_avoids_duplicate_upstream_calls(web,monkeypatch):
    import app.server as server
    app,c,h=web
    calls=[]
    def topic(*args):
        calls.append(args)
        return {"candidates":[candidate()],"total":1,"offset":0,"has_more":False}
    monkeypatch.setattr(server,"search_topic",topic)
    first=c.post("/api/search",headers=h,json={"mode":"related","query":"harness"}).json()
    second=c.post("/api/search",headers=h,json={"mode":"related","query":"harness"}).json()
    assert len(calls)==1 and not first["cached"] and second["cached"]
    assert first["search_id"]==second["search_id"]
    c.post("/api/search",headers=h,json={"mode":"related","query":"different"})
    assert len(calls)==2

def test_source_timeout_returns_useful_error_not_server_trace(web,monkeypatch):
    import app.server as server
    app,c,h=web
    def timeout(*args):raise httpx.ReadTimeout("upstream private exception")
    monkeypatch.setattr(server,"search_topic",timeout)
    response=c.post("/api/search",headers=h,json={"mode":"related","query":"harness"})
    assert response.status_code==504
    assert "private" not in response.text and response.json()["detail"]
