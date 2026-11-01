"""Full extracted-text translation; publish only after every chunk succeeds."""
import json
import re
import uuid
from app.store import atomic_text, digest
from tools.validate import validate_markdown

PROTECTED = re.compile(r"(\x60\x60\x60[\s\S]*?\x60\x60\x60|~~~[\s\S]*?~~~|\x60[^\x60]*\x60|\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|(?<!\\)\$[^\n$]+(?<!\\)\$|!?\[[^\]]*\]\([^)]+\)|<[^>]+>)")


def translate_paper(store, ref, model):
    store.lookup(ref)
    directory = store.directory(ref)
    source = directory/"paper.md"
    registered = {a["path"] for a in store.artifacts()
                  if a["ref"] == ref and a["kind"] == "markdown" and a["status"] == "present"}
    if not source.is_file() or source.relative_to(store.root).as_posix() not in registered:
        raise ValueError("请先收集或恢复本地 Markdown 全文，再执行翻译")
    fingerprint = digest(source)
    target = directory/"paper.zh.md"
    record = directory/"translation.validation.json"
    if target.is_file() and record.is_file():
        saved = json.loads(record.read_text(encoding="utf-8"))
        if saved.get("source_sha256") == fingerprint and saved.get("output_sha256") == digest(target):
            store.record_artifact(ref, "markdown", target)
            store.record_artifact(ref, "validation", record)
            return {"ref": ref, "path": target.relative_to(store.root).as_posix(), "cached": True,
                    "chunks": saved["chunks"]}
        raise ValueError("原文或译文已变化，请先预览清理旧译文后重新翻译")
    if target.exists():
        raise ValueError("已有译文缺少完整校验记录，拒绝覆盖；请人工核对后清理旧译文")
    text = source.read_text(encoding="utf-8")
    if not text.strip():raise ValueError("Markdown 全文为空")
    if len(text) > 500000:raise ValueError("全文超过 50 万字符，停止以避免过量 API 费用")
    prefix = "KEEP_" + uuid.uuid4().hex + "_"
    protected = {}
    def mask(match):
        key = prefix + str(len(protected)) + "_END"
        protected[key] = match[0]
        return key
    masked = PROTECTED.sub(mask, text)
    parts = re.findall(r"(?:\S+\s*|\s+)", masked)
    chunks = []
    current = ""
    for part in parts:
        if len(part) > 6000:raise ValueError("全文存在超长连续片段，请先检查 Markdown 格式")
        if current and len(current) + len(part) > 6000:
            chunks.append(current);current = ""
        current += part
    if current:chunks.append(current)
    output = []
    usage = []
    for chunk in chunks:
        result = model.translate(chunk)
        translated = result["translation"]
        expected = {key for key in protected if key in chunk}
        found = re.findall(re.escape(prefix) + r"[0-9]+_END", translated)
        if set(found) != expected or len(found) != len(expected):
            raise ValueError("翻译遗漏或改写公式、代码或链接占位符，未保存译文")
        for key in expected:translated = translated.replace(key, protected[key])
        output.append(translated)
        usage.append(result.get("usage"))
    if digest(source) != fingerprint:raise ValueError("翻译期间原文已变化，未保存译文")
    content = "# 中文全文译文\n\n论文编号：" + ref + "\n\n说明：基于本机提取的全文；机器翻译未经人工核对，公式与代码保留原样。\n\n" + "\n\n".join(output).strip() + "\n"
    stage = directory/"translation.pending.md"
    try:
        atomic_text(stage, content)
        validation = validate_markdown(stage)
        stage.replace(target)
    finally:stage.unlink(missing_ok=True)
    validation["path"] = str(target)
    validation.update(source_sha256=fingerprint, output_sha256=digest(target),
                      chunks=len(chunks), model=model.model)
    atomic_text(record, json.dumps(validation, ensure_ascii=False, indent=2))
    store.record_artifact(ref, "markdown", target)
    store.record_artifact(ref, "validation", record)
    store.event(uuid.uuid4().hex, "translate", {"ref": ref, "chunks":len(chunks),
                "model":model.model, "usage":usage, "validation":validation["status"]})
    return {"ref":ref, "path":target.relative_to(store.root).as_posix(),
            "cached":False, "chunks":len(chunks), "validation":validation["status"]}
