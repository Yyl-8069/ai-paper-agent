from pathlib import Path
from urllib.parse import urlsplit,urljoin
import httpx

def trusted_url(url):
    p=urlsplit(url)
    if (p.scheme!="https" or p.hostname not in {"arxiv.org","export.arxiv.org"}
            or p.username or p.password or p.port not in (None,443)):
        raise ValueError("下载仅允许 arXiv HTTPS 地址")
    return url

def download_pdf(candidate,target,client=None,max_bytes=50*1024*1024):
    url=trusted_url(candidate["pdf_url"])
    target=Path(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():raise FileExistsError(target)
    part=target.with_suffix(".pdf.part")
    owned=client is None
    client=client or httpx.Client(timeout=httpx.Timeout(60,connect=15),follow_redirects=False,trust_env=False)
    try:
        for _ in range(4):
            with client.stream("GET",url,headers={"User-Agent":"PersonalPaperAgent/0.1"}) as r:
                if r.is_redirect:
                    url=trusted_url(urljoin(url,r.headers["location"]))
                    continue
                r.raise_for_status()
                count=0
                with part.open("wb") as out:
                    for block in r.iter_bytes():
                        count+=len(block)
                        if count>max_bytes:raise ValueError("PDF 超出大小上限")
                        out.write(block)
                with part.open("rb") as f:
                    if f.read(5)!=b"%PDF-":raise ValueError("下载内容不是 PDF")
                part.replace(target)
                return target
        raise ValueError("PDF 重定向过多")
    finally:
        part.unlink(missing_ok=True)
        if owned:client.close()
