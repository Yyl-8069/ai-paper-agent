import pytest
from fastapi.testclient import TestClient
from app.server import create_app
from app.jobs import JobRunner
from app.store import Store
from test_api import web
from test_store import candidate


def test_control_character_key_is_rejected_without_echo(web):
    app, client, headers = web
    marker = "sensitive-key-marker"
    response = client.put("/api/config", headers=headers,
                          json={"api_key": marker + "\u0000", "model": "deepseek-flash"})
    assert response.status_code == 422
    assert marker not in response.text
    assert not app.state.config_path.exists()


def test_background_exception_text_cannot_persist_key(web, monkeypatch):
    app, client, headers = web
    import app.server as server
    monkeypatch.setattr(server, "fetch_candidates", lambda *args: [candidate()])
    found = client.post("/api/search", headers=headers, json={"limit": 1}).json()
    marker = "sensitive-key-marker"
    def fail(*args, **kwargs):
        raise RuntimeError("Illegal header value b'Bearer " + marker + "'")
    monkeypatch.setattr(server, "collect_candidates", fail)
    response = client.post("/api/collect", headers=headers,
                           json={"search_id": found["search_id"], "indices": [1], "summarize": False})
    assert response.status_code == 202
    job = client.get("/api/jobs/" + response.json()["job_id"])
    assert job.json()["status"] == "failed"
    assert marker not in job.text
    with app.state.store.connect() as db:
        raw = db.execute("SELECT error FROM api_jobs WHERE id=?", (response.json()["job_id"],)).fetchone()[0]
    assert marker not in raw


def test_second_app_does_not_interrupt_live_service_jobs(web):
    app, client, headers = web
    with app.state.store.connect() as db:
        db.execute("INSERT INTO api_jobs VALUES(?,?,?,?,?,?,?)",
                   ("live", "collect", "running", "2026", "2026", None, None))
    second = create_app(app.state.store.root, config_path=app.state.config_path)
    assert client.get("/api/jobs/live").json()["status"] == "running"
    with pytest.raises(RuntimeError, match="already running"):
        with TestClient(second, base_url="http://127.0.0.1"):
            pass
    assert client.get("/api/jobs/live").json()["status"] == "running"
