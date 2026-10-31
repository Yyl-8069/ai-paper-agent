import json
import os
from contextlib import contextmanager
import uuid
from app.cli import library_lock
from app.store import now


class JobRunner:
    """Single-process jobs; state persists, interrupted work is never called success."""

    def __init__(self, store):
        self.store = store
        with store.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS api_jobs(
                id TEXT PRIMARY KEY, kind TEXT, status TEXT, created TEXT,
                updated TEXT, result TEXT, error TEXT)""")

    def recover(self):
        with self.store.connect() as db:
            db.execute("UPDATE api_jobs SET status='interrupted',updated=?,error=? "
                       "WHERE status IN ('queued','running')",
                       (now(), "服务重启，任务中断；请查看已有文件后重试。"))

    def list(self):
        with self.store.connect() as db:
            rows = db.execute("SELECT * FROM api_jobs ORDER BY created DESC LIMIT 100").fetchall()
        return [self._decode(row) for row in rows]

    def get(self, ident):
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM api_jobs WHERE id=?", (ident,)).fetchone()
        if row is None:
            raise KeyError(ident)
        return self._decode(row)

    @staticmethod
    def _decode(row):
        return {**dict(row), "result": json.loads(row["result"]) if row["result"] else None}

    def submit(self, background, kind, operation):
        guard = library_lock(self.store.root)
        guard.__enter__()
        ident = uuid.uuid4().hex
        try:
            timestamp = now()
            with self.store.connect() as db:
                db.execute("INSERT INTO api_jobs VALUES(?,?,?,?,?,?,?)",
                           (ident, kind, "queued", timestamp, timestamp, None, None))
            background.add_task(self._run, ident, guard, operation)
        except BaseException:
            guard.__exit__(None, None, None)
            raise
        return {"job_id": ident, "status": "queued"}

    def _run(self, ident, guard, operation):
        try:
            self._update(ident, "running")
            result = operation()
            status = "succeeded"
            error = None
            if isinstance(result, dict) and result.get("failed"):
                status = "partial" if result.get("refs") else "failed"
                error = "部分论文处理失败，请查看结果中的 failed。"
            self._update(ident, status, result, error)
        except Exception as error:
            self._update(ident, "failed", error="Task failed (" + type(error).__name__ + "). Check inputs, network, and model configuration.")
            self.store.event(ident, "api_job_failed", {"error_type": type(error).__name__})
        finally:
            guard.__exit__(None, None, None)

    def _update(self, ident, status, result=None, error=None):
        serialized = json.dumps(result, ensure_ascii=False, default=str) if result is not None else None
        with self.store.connect() as db:
            db.execute("UPDATE api_jobs SET status=?,updated=?,result=?,error=? WHERE id=?",
                       (status, now(), serialized, error, ident))


@contextmanager
def service_lock(store):
    handle = store.safe_path(".api-service.lock").open("a+b")
    try:
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError("API service already running for this library") from error
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()
