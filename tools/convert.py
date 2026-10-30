import json
import os
from pathlib import Path
import subprocess
import sys

def _worker(source,target):
    import contextlib
    import io
    import pymupdf
    import pymupdf4llm
    from app.store import atomic_text
    target=Path(target).resolve();target.mkdir(parents=True,exist_ok=True)
    with pymupdf.open(source) as doc:
        if doc.page_count>200:raise ValueError("PDF exceeds 200 page limit")
        pages=doc.page_count
        blank=[i+1 for i,p in enumerate(doc) if not p.get_text().strip()]
        if len(blank)==pages:raise ValueError("PDF has no extractable text; scanned/OCR documents unsupported")
        previous=Path.cwd()
        try:
            os.chdir(target)
            with contextlib.redirect_stdout(io.StringIO()):
                chunks=pymupdf4llm.to_markdown(doc,write_images=True,image_path="assets",
                    page_chunks=True,show_progress=False)
        finally:
            os.chdir(previous)
    text="\n\n".join(f"<!-- PDF page {i+1} -->\n\n"+p["text"] for i,p in enumerate(chunks)).strip()+"\n"
    if len(text.strip())<40:raise ValueError("PDF extraction produced too little text")
    atomic_text(target/"paper.md",text)
    return {"markdown_path":str(target/"paper.md"),"pages":pages,
            "assets":[str(p) for p in (target/"assets").glob("*") if p.is_file()],
            "warnings":["公式、表格与双栏阅读顺序未经人工核对"]+
                       ([f"无文本页面: {blank}"] if blank else []),
            "completeness":"needs_review"}

def convert_pdf(pdf_path,output_dir,timeout=180):
    source=Path(pdf_path).resolve()
    target=Path(output_dir).resolve()
    if source.stat().st_size>50*1024*1024:raise ValueError("PDF exceeds 50 MiB")
    if (target/"paper.md").exists():raise FileExistsError(target/"paper.md")
    r=subprocess.run([sys.executable,"-m","tools.convert",str(source),str(target)],
                     cwd=Path(__file__).resolve().parents[1],capture_output=True,
                     text=True,encoding="utf-8",errors="replace",timeout=timeout)
    if r.returncode:raise ValueError(r.stderr.strip()[-1200:])
    return json.loads(r.stdout)

if __name__=="__main__":
    print(json.dumps(_worker(sys.argv[1],sys.argv[2]),ensure_ascii=True))
