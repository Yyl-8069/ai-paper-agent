from datetime import datetime,timezone
import httpx
import pytest
from tools.search import search_papers, hot_papers
from tools.download import download_pdf
ATOM=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2401.00001v2</id><title>AI study</title><summary>Abstract.</summary><published>2024-01-02T00:00:00Z</published><author><name>Jane</name></author></entry></feed>'''

def test_arxiv_parses_identity_version_and_date():
    def handler(request):
        assert "submittedDate" in request.url.params["search_query"]
        return httpx.Response(200,content=ATOM)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        rows=search_papers("agent",datetime(2024,1,1,tzinfo=timezone.utc),
                          datetime(2024,1,3,tzinfo=timezone.utc),5,client=client)
    assert rows[0]["source_id"]=="2401.00001"
    assert rows[0]["version"]==2
    assert rows[0]["evidence"]=={}
    assert rows[0]["pdf_url"]=="https://arxiv.org/pdf/2401.00001v2"

def test_hot_source_keeps_observed_votes_and_fails_explicitly():
    data=[{"paper":{"id":"2401.00001","title":"AI","authors":[{"name":"Jane"}],
                    "summary":"Text","publishedAt":"2024-01-01T00:00:00Z","upvotes":12}}]
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=data))) as c:
        result=hot_papers(3,client=c)
    assert result[0]["evidence"]["upvotes"]==12
    assert result[0]["evidence"]["source"].startswith("https://huggingface.co/")
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(503))) as c:
        with pytest.raises(httpx.HTTPStatusError):
            hot_papers(3,client=c)

@pytest.mark.parametrize("url",["http://arxiv.org/pdf/1","https://evil.test/a","https://arxiv.org@evil.test/a"])
def test_download_rejects_untrusted_url_before_request(tmp_path,url):
    with pytest.raises(ValueError):
        download_pdf({"pdf_url":url},tmp_path/"out.pdf")

def test_download_rejects_nonpdf_and_oversize(tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b"not PDF"))) as c:
        with pytest.raises(ValueError):
            download_pdf({"pdf_url":"https://arxiv.org/pdf/2401.00001v1"},tmp_path/"a.pdf",client=c)
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b"%PDF-"+b"x"*40))) as c:
        with pytest.raises(ValueError):
            download_pdf({"pdf_url":"https://arxiv.org/pdf/2401.00001v1"},tmp_path/"a.pdf",client=c,max_bytes=20)
    assert not (tmp_path/"a.pdf").exists()
