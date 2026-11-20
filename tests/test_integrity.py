import time
from pathlib import Path
import pytest
from fbmd.store import Store
from fbmd.engine import Worker, output_folder, verified_existing, InvalidMedia


def test_existing_unverified_media_is_preserved(tmp_path, server):
    store = Store(tmp_path / "state", tmp_path / "media", allow_local=True)
    job = store.enqueue(server[0] + "/sample.mp4")
    folder = output_folder(store, store.job(job))
    folder.mkdir()
    existing = folder / "media.mp4"
    existing.write_bytes(b"valuable existing user file")
    Worker(store).run()
    assert store.job(job)["status"] == "failed"
    assert existing.read_bytes() == b"valuable existing user file"


def test_modified_previous_media_is_not_used_for_dedup(tmp_path, server):
    store = Store(tmp_path / "state", tmp_path / "media", allow_local=True)
    first = store.enqueue(server[0] + "/sample.mp4")
    Worker(store).run()
    old = Path(store.job(first)["path"])
    old.write_bytes(b"user modified this file")
    second = store.enqueue(server[0] + "/second.mp4")
    Worker(store).run()
    assert store.job(second)["status"] == "complete"
    assert Path(store.job(second)["path"]) != old
    assert old.read_bytes() == b"user modified this file"
    with pytest.raises(InvalidMedia):
        verified_existing(old)


def test_resume_preserves_retry_after(tmp_path, server):
    store = Store(tmp_path / "state", tmp_path / "media", allow_local=True)
    job = store.enqueue(server[0] + "/sample.mp4")
    after = time.time() + 600
    store.update(job, status="paused", next_try=after, error="RATE_LIMITED: 600")
    store.resume(job)
    assert store.job(job)["next_try"] == after
    assert store.claim() is None


def test_size_quota_rejects_without_finalization(tmp_path, server, monkeypatch):
    monkeypatch.setenv("FBMD_MAX_FILE_BYTES", "100")
    store = Store(tmp_path / "state", tmp_path / "media", allow_local=True)
    job = store.enqueue(server[0] + "/sample.mp4")
    Worker(store).run()
    assert store.job(job)["status"] == "failed"
    assert not list(store.media.rglob("media.mp4"))
