import json
import shutil
import uuid
from pathlib import Path
from app.store import atomic_text,digest,now
from tools.download import download_pdf
from tools.convert import convert_pdf
from tools.validate import validate_markdown

def collect_candidates(candidates,store,downloader=download_pdf,restore=False):
    run_id=uuid.uuid4().hex
    result={"run_id":run_id,"refs":[],"skipped":[],"failed":[]}
    for candidate in candidates:
        ref=store.register(candidate)
        directory=store.directory(ref)
        directory.mkdir(parents=True,exist_ok=True)
        artifacts=[a for a in store.artifacts() if a["ref"]==ref]
        if not restore and any(a["status"]=="deleted" for a in artifacts):
            result["skipped"].append(ref);continue
        try:
            metadata=directory/"metadata.json"
            atomic_text(metadata,json.dumps({**candidate,"ref":ref},ensure_ascii=False,indent=2))
            store.record_artifact(ref,"metadata",metadata)
            pdf=directory/"original.pdf";md=directory/"paper.md"
            if not md.exists():
                if not pdf.exists():
                    downloader(candidate,pdf)
                    store.set_state(ref,"downloaded")
                store.record_artifact(ref,"pdf",pdf)
                converted=convert_pdf(pdf,directory)
                atomic_text(directory/"conversion.json",json.dumps(converted,ensure_ascii=False,indent=2))
                for image in converted["assets"]:
                    store.record_artifact(ref,"asset",image)
            validation=validate_markdown(md)
            atomic_text(directory/"validation.json",json.dumps(validation,ensure_ascii=False,indent=2))
            store.record_artifact(ref,"markdown",md)
            store.record_artifact(ref,"validation",directory/"validation.json")
            if (directory/"conversion.json").exists():
                store.record_artifact(ref,"validation",directory/"conversion.json")
            store.set_state(ref,"converted_needs_review")
            store.event(run_id,"collected",{"ref":ref,"validation":validation["status"]})
            result["refs"].append(ref)
        except Exception as error:
            store.set_state(ref,"failed")
            failure={"ref":ref,"error":type(error).__name__,"message":str(error)[:400]}
            result["failed"].append(failure)
            store.event(run_id,"failed",{"ref":ref,"error":type(error).__name__})
    store.export_index()
    store.event(run_id,"collection_result",{"refs":result["refs"],"skipped":result["skipped"],
                                           "failed":[p["ref"] for p in result["failed"]]})
    return result

def import_pdf(source,title,store):
    source=Path(source).resolve()
    if not source.is_file():raise FileNotFoundError(source)
    if source.stat().st_size>50*1024*1024:raise ValueError("PDF exceeds 50 MiB")
    with source.open("rb") as f:
        if f.read(5)!=b"%PDF-":raise ValueError("所选文件不是 PDF")
    candidate={"source":"local","source_id":digest(source),"version":1,"title":title or source.stem,
               "authors":[],"published_at":now(),"abstract":"","pdf_url":"","evidence":{}}
    def copy(_candidate,target):
        shutil.copyfile(source,target)
        return target
    return collect_candidates([candidate],store,downloader=copy)
