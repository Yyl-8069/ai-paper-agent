from pathlib import Path
import pytest
from app.store import Store
from tools.cleanup import plan_cleanup,execute_cleanup
from test_store import candidate

def setup_library(root):
    store=Store(root); ref=store.register(candidate()); directory=store.directory(ref);directory.mkdir(parents=True)
    for name,kind in [("original.pdf","pdf"),("paper.md","markdown"),("assets/image.png","asset")]:
        p=directory/name;p.parent.mkdir(exist_ok=True);p.write_bytes(b"content");store.record_artifact(ref,kind,p)
    summary=root/"weekly/week.md";summary.parent.mkdir();summary.write_text("# Week\n")
    store.record_report(dict(id="week",kind="weekly",period="2026-W44",path=summary,
                             references=[ref],coverage={}))
    return store,ref,summary

@pytest.mark.parametrize("mode,expected",[
    ("pdf",["original.pdf"]),("markdown",["image.png","paper.md"]),
    ("summary",["week.md"]),("all",["image.png","original.pdf","paper.md","week.md"])])
def test_four_modes_delete_exact_preview_and_keep_index(tmp_path,mode,expected):
    store,ref,summary=setup_library(tmp_path)
    plan=plan_cleanup(tmp_path,{"refs":[ref],"reports":["week"]},mode,store)
    assert sorted(Path(t["path"]).name for t in plan["targets"])==expected
    with pytest.raises(ValueError):
        execute_cleanup(plan,"wrong",store)
    result=execute_cleanup(plan,plan["id"],store)
    assert len(result["deleted"])==len(expected)
    assert result["failed"]==[]
    assert store.lookup(ref)["title"]=="Attention Is All You Need"
    again=execute_cleanup(plan,plan["id"],store)
    assert len(again["missing"])==len(expected)

def test_paper_selection_does_not_delete_shared_weekly(tmp_path):
    store,ref,summary=setup_library(tmp_path)
    plan=plan_cleanup(tmp_path,{"refs":[ref],"reports":[]},"all",store)
    execute_cleanup(plan,plan["id"],store)
    assert summary.exists()

def test_changed_file_aborts_entire_preview(tmp_path):
    store,ref,summary=setup_library(tmp_path)
    plan=plan_cleanup(tmp_path,{"refs":[ref],"reports":[]},"all",store)
    (store.directory(ref)/"original.pdf").write_bytes(b"changed")
    with pytest.raises(ValueError):
        execute_cleanup(plan,plan["id"],store)
    assert (store.directory(ref)/"paper.md").exists()

def test_library_outside_target_and_link_escape_rejected(tmp_path):
    store,ref,summary=setup_library(tmp_path/"lib")
    with pytest.raises(ValueError):
        store.record_artifact(ref,"pdf",tmp_path/"outside.pdf")
    with pytest.raises(ValueError):
        plan_cleanup(tmp_path/"other",{"refs":[ref]},"pdf",store)

def test_shared_assets_kept_when_other_markdown_references_them(tmp_path):
    store,ref,summary=setup_library(tmp_path)
    second=store.register({**candidate(),"source_id":"2401.00002"})
    d=store.directory(second);d.mkdir(parents=True)
    m=d/"paper.md";m.write_text("![x](../../P000001/v1/assets/image.png)\n")
    store.record_artifact(second,"markdown",m)
    plan=plan_cleanup(tmp_path,{"refs":[ref]},"markdown",store)
    assert all(Path(t["path"]).name!="image.png" for t in plan["targets"])
