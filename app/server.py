import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from agents.researcher import Researcher
from app.cli import fetch_candidates, library_lock, previous_week
from app.config import PROJECT, load_config
from app.jobs import JobRunner, service_lock
from tools.credentials import validate_api_key
from app.store import Store, atomic_text, now
from tools.cleanup import execute_cleanup, plan_cleanup
from workflows.collect import collect_candidates, import_pdf
from workflows.reports import BEIJING, due_weeks, materials_for, summarize_week, week_bounds, write_report


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchBody(Body):
    mode: Literal["latest", "hot"] = "latest"
    days: int = Field(default=7, ge=1, le=365)
    period: Literal["day", "week", "month", "half_year", "year"] | None = None
    limit: int = Field(default=5, ge=1, le=10)
    query: str = Field(default="", max_length=300)


class TranslateBody(Body):
    ref: str = Field(min_length=1, max_length=80)


class CollectBody(Body):
    search_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    indices: list[Annotated[int, Field(ge=1, le=10, strict=True)]] = Field(min_length=1, max_length=10)
    summarize: bool = True
    restore: bool = False


class BriefBody(Body):
    refs: list[str] = Field(min_length=1, max_length=100)


class WeeklyBody(Body):
    week: str | None = Field(default=None, pattern=r"^[0-9]{4}-W[0-9]{2}$")
    force: bool = False


class CleanupBody(Body):
    mode: Literal["pdf", "markdown", "summary", "all"]
    refs: list[str] = Field(default_factory=list, max_length=1000)
    reports: list[str] = Field(default_factory=list, max_length=1000)


class ConfirmBody(Body):
    plan_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    confirmation: Literal["DELETE"]


class ConfigBody(Body):
    api_key: SecretStr | None = None
    model: str = Field(default="deepseek-flash", min_length=1, max_length=100,
                       pattern=r"^[A-Za-z0-9_.:/-]+$")

    @field_validator("api_key")
    @classmethod
    def validate_key(cls, value):
        if value is not None:
            plain = value.get_secret_value()
            if plain:
                validate_api_key(plain)
            if len(plain) > 4096:
                raise ValueError("密钥长度或空白字符无效")
        return value


def create_app(library=None, config_path=None):
    store = Store(library or PROJECT / "library")
    config_path = Path(config_path or PROJECT / ".env")
    runner = JobRunner(store)
    token = secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(application):
        with service_lock(store):
            runner.recover()
            yield

    app = FastAPI(lifespan=lifespan, title="AI 论文助手", version="0.2.0",
                  description="本机论文收集、PDF 转 Markdown、总结与可预览确认的清理。")
    app.state.store = store
    app.state.config_path = config_path
    app.state.jobs = runner
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    header = APIKeyHeader(name="X-Local-Token", auto_error=False)

    def authorize(request: Request, supplied: str | None = Depends(header)):
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            raise HTTPException(403, "拒绝跨站请求")
        if not supplied or not secrets.compare_digest(supplied, token):
            raise HTTPException(403, "请刷新本机页面，或先从 /api/session 获取 X-Local-Token")

    auth = [Depends(authorize)]

    @app.middleware("http")
    async def response_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Never echo submitted API keys or full request bodies in validation errors.
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
            for item in error.errors()]})

    @app.exception_handler(KeyError)
    async def missing_record(request, error):
        return JSONResponse(status_code=404, content={"detail": "指定记录不存在"})

    @app.exception_handler(ValueError)
    async def invalid_value(request, error):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.exception_handler(RuntimeError)
    async def operation_conflict(request, error):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    def ai():
        settings = load_config(config_path)
        return Researcher(settings.get("DEEPSEEK_API_KEY", ""),
                          settings.get("DEEPSEEK_MODEL", "deepseek-flash"))

    def settings_status():
        values = load_config(config_path)
        return {"model": values.get("DEEPSEEK_MODEL", "deepseek-flash"),
                "key_configured": bool(values.get("DEEPSEEK_API_KEY")),
                "library": str(store.root)}

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.2.0"}

    @app.get("/api/session")
    def session():
        return {"token": token}

    @app.get("/api/config")
    def read_settings():
        return settings_status()

    @app.put("/api/config", dependencies=auth)
    def save_settings(body: ConfigBody):
        with library_lock(store.root):
            old = load_config(config_path)
            key = body.api_key.get_secret_value() if body.api_key else ""
            key = key or old.get("DEEPSEEK_API_KEY", "")
            atomic_text(config_path, f"DEEPSEEK_API_KEY={key}\nDEEPSEEK_MODEL={body.model}\n")
        return settings_status()

    @app.get("/")
    def home():
        return FileResponse(PROJECT / "app/static/index.html", media_type="text/html")

    @app.get("/api/papers")
    def papers():
        artifacts = store.artifacts()
        return [{**paper, "files": [
            {**item, "exists": store.safe_path(item["path"]).is_file()}
            for item in artifacts if item["ref"] == paper["ref"]]} for paper in store.papers()]

    @app.get("/api/reports")
    def reports():
        return [{**report, "exists": store.safe_path(report["path"]).is_file()}
                for report in store.reports()]

    @app.get("/api/files")
    def get_file(path: str = Query(max_length=1000)):
        try:
            target = store.safe_path(path)
            relative = target.relative_to(store.root).as_posix()
        except ValueError:
            raise HTTPException(404, "文件不存在")
        registered = any(item["path"] == relative and item["status"] == "present"
                         for item in store.artifacts())
        if not registered or not target.is_file():
            raise HTTPException(404, "文件不存在或未登记")
        return FileResponse(target, filename=target.name, media_type="application/octet-stream")

    @app.post("/api/search", dependencies=auth)
    def search(body: SearchBody):
        rows = fetch_candidates(body.mode, body.days, body.limit, body.query, body.period)
        ident = uuid.uuid4().hex
        record = {"created": now(), "candidates": rows}
        path = store.safe_path(f"temp/search/{ident}.json")
        atomic_text(path, json.dumps(record, ensure_ascii=False))
        return {"search_id": ident, "candidates": rows}

    @app.post("/api/collect", status_code=202, dependencies=auth)
    def collect(body: CollectBody, background: BackgroundTasks):
        path = store.safe_path(f"temp/search/{body.search_id}.json")
        if not path.is_file():
            raise HTTPException(404, "检索清单不存在，请重新检索")
        record = json.loads(path.read_text(encoding="utf-8"))
        if datetime.now(timezone.utc) - datetime.fromisoformat(record["created"]) > timedelta(hours=24):
            raise HTTPException(409, "检索清单已过期，请重新检索")
        indices = sorted(set(body.indices))
        if max(indices) > len(record["candidates"]):
            raise HTTPException(422, "论文序号超出候选范围")
        chosen = [record["candidates"][index - 1] for index in indices]
        model = ai() if body.summarize else None

        def operation():
            result = collect_candidates(chosen, store, restore=body.restore)
            if model and result["refs"]:
                data = model.summarize(materials_for(store, result["refs"]), "brief")
                result["report"] = write_report(store, "brief", datetime.now(BEIJING).date().isoformat(), data)
            return result

        return runner.submit(background, "collect", operation)

    @app.post("/api/import", status_code=202, dependencies=auth)
    async def upload_pdf(request: Request, background: BackgroundTasks,
                         title: str = Query(default="", max_length=500),
                         filename: str = Query(default="paper.pdf", max_length=250)):
        if request.headers.get("content-type", "").split(";")[0] != "application/pdf":
            raise HTTPException(415, "请使用 application/pdf 上传")
        limit = 50 * 1024 * 1024
        path = store.safe_path("temp/uploads/" + uuid.uuid4().hex + ".pdf")
        path.parent.mkdir(parents=True, exist_ok=True)
        submitted = False
        try:
            size = 0
            with path.open("wb") as output:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > limit:
                        raise HTTPException(413, "PDF 超过 50 MiB")
                    output.write(chunk)
            with path.open("rb") as source:
                if source.read(5) != b"%PDF-":
                    raise HTTPException(422, "上传内容不是 PDF")
            paper_title = title.strip() or Path(filename.replace("\\", "/")).stem

            def operation():
                try:
                    return import_pdf(path, paper_title, store)
                finally:
                    path.unlink(missing_ok=True)

            response = runner.submit(background, "import", operation)
            submitted = True
            return response
        finally:
            if not submitted:
                path.unlink(missing_ok=True)

    @app.post("/api/translate", status_code=202, dependencies=auth)
    def translate(body: TranslateBody, background: BackgroundTasks):
        from workflows.translate import translate_paper
        store.lookup(body.ref)
        source = store.directory(body.ref)/"paper.md"
        if not source.is_file():
            raise HTTPException(422, "请先收集或恢复本地 Markdown 全文")
        model = ai()
        return runner.submit(background, "translate", lambda: translate_paper(store, body.ref, model))

    @app.post("/api/brief", status_code=202, dependencies=auth)
    def brief(body: BriefBody, background: BackgroundTasks):
        for ref in body.refs:
            store.lookup(ref)
        model = ai()

        def operation():
            data = model.summarize(materials_for(store, body.refs), "brief")
            return write_report(store, "brief", datetime.now(BEIJING).date().isoformat(), data)

        return runner.submit(background, "brief", operation)

    @app.post("/api/weekly", status_code=202, dependencies=auth)
    def weekly(body: WeeklyBody, background: BackgroundTasks):
        week = body.week or previous_week()
        week_bounds(week)

        def operation():
            # A model is only needed if there are collected papers in this week.
            start, end = week_bounds(week)
            has_material = any(start <= datetime.fromisoformat(p["collected"]) < end for p in store.papers())
            return summarize_week(week, store, ai() if has_material else None, body.force)

        return runner.submit(background, "weekly", operation)

    @app.post("/api/catch-up", status_code=202, dependencies=auth)
    def catch_up(background: BackgroundTasks):
        def operation():
            weeks = due_weeks(datetime.now(timezone.utc), store)
            model = ai() if weeks else None
            return [summarize_week(week, store, model) for week in weeks]
        return runner.submit(background, "catch-up", operation)

    @app.get("/api/jobs")
    def jobs():
        return runner.list()

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str):
        return runner.get(job_id)

    @app.post("/api/cleanup/preview", dependencies=auth)
    def preview_cleanup(body: CleanupBody):
        with library_lock(store.root):
            return plan_cleanup(store.root, {"refs": body.refs, "reports": body.reports}, body.mode, store)

    @app.post("/api/cleanup/execute", dependencies=auth)
    def confirm_cleanup(body: ConfirmBody):
        with library_lock(store.root):
            path = store.safe_path(f"temp/cleanup/{body.plan_id}.json")
            if not path.is_file():
                raise HTTPException(404, "清理预览不存在")
            plan = json.loads(path.read_text(encoding="utf-8"))
            try:
                return execute_cleanup(plan, body.plan_id, store)
            except ValueError as error:
                raise HTTPException(409, str(error))

    static_dir = PROJECT / "app/static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    return app


app = create_app()
