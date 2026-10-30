from concurrent.futures import ThreadPoolExecutor
import pytest
from app.store import Store


def candidate(version=1):
    return dict(source="arxiv", source_id="1706.03762", version=version,
                title="Attention Is All You Need", authors=["A. Author"],
                published_at="2017-06-12T00:00:00+00:00", abstract="A transformer.",
                pdf_url="https://arxiv.org/pdf/1706.03762v1", evidence={})


def test_versions_keep_identity_and_deleted_number_not_reused(tmp_path):
    s = Store(tmp_path)
    a = s.register(candidate())
    assert a == "P000001/v1"
    assert s.register(candidate()) == a
    assert s.register(candidate(2)) == "P000001/v2"
    s.set_state(a, "deleted")
    other = candidate()
    other["source_id"] = "2001.00001"
    assert s.register(other) == "P000002/v1"
    assert s.lookup(a)["title"] == "Attention Is All You Need"


def test_concurrent_registration_is_idempotent(tmp_path):
    Store(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        refs = list(pool.map(lambda _: Store(tmp_path).register(candidate()), range(8)))
    assert set(refs) == {"P000001/v1"}
    assert len(Store(tmp_path).papers()) == 1


def test_artifact_escape_and_invalid_identity_rejected(tmp_path):
    s = Store(tmp_path)
    ref = s.register(candidate())
    with pytest.raises(ValueError):
        s.record_artifact(ref, "pdf", tmp_path.parent / "escape.pdf")
    with pytest.raises(ValueError):
        s.register({**candidate(), "version": -1})
    with pytest.raises(ValueError):
        s.directory("../escape")
