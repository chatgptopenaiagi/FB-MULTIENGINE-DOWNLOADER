import hashlib
import json
from pathlib import Path
import threading
import time
import pytest
from fbmd.store import Store
from fbmd.engine import Worker, worker_lock, output_folder
from fbmd.discovery import discover, meta_lookup
from conftest import PAYLOAD


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "state", tmp_path / "media", allow_local=True)


def test_download_and_content_duplicate(store, server):
    base, _ = server
    a = store.enqueue(base + "/a.mp4")
    b = store.enqueue(base + "/b.mp4")
    assert store.enqueue(base + "/a.mp4") == a
    Worker(store).run()
    one, two = store.job(a), store.job(b)
    assert one["status"] == two["status"] == "complete"
    assert one["path"] == two["path"]
    assert Path(one["path"]).read_bytes() == PAYLOAD
    assert one["sha256"] == hashlib.sha256(PAYLOAD).hexdigest()


def test_pause_resume_uses_range_and_persists(store, server):
    base, requests = server
    job = store.enqueue(base + "/slow.mp4")
    worker = Worker(store)
    thread = threading.Thread(target=worker.run)
    thread.start()
    deadline = time.time() + 8
    while store.job(job)["downloaded"] < 65536 and time.time() < deadline:
        time.sleep(0.02)
    store.pause(job)
    thread.join(10)
    assert not thread.is_alive()
    assert store.job(job)["status"] == "paused"
    reopened = Store(store.directory, store.media, allow_local=True)
    reopened.resume(job)
    Worker(reopened).run()
    assert reopened.job(job)["status"] == "complete"
    assert any(r["range"] for r in requests)
    assert Path(reopened.job(job)["path"]).read_bytes() == PAYLOAD


@pytest.mark.parametrize("endpoint", ["sample.mp4", "ignore-range.mp4"])
def test_recover_partial_after_crash(store, server, endpoint):
    base, _ = server
    job = store.enqueue(base + "/" + endpoint)
    folder = output_folder(store, store.job(job))
    folder.mkdir()
    (folder / "media.mp4.part").write_bytes(PAYLOAD[:100000])
    store.update(job, status="running", etag='"fixture-v1"', downloaded=100000)
    Worker(store).run()
    assert store.job(job)["status"] == "complete"
    assert Path(store.job(job)["path"]).read_bytes() == PAYLOAD


def test_invalid_range_never_completed(store, server):
    base, _ = server
    job = store.enqueue(base + "/bad-range.mp4")
    folder = output_folder(store, store.job(job))
    folder.mkdir()
    (folder / "media.mp4.part").write_bytes(PAYLOAD[:1000])
    store.update(job, etag='"fixture-v1"')
    Worker(store).run()
    assert store.job(job)["status"] == "failed"
    assert not (folder / "media.mp4").exists()


def test_auth_and_html_rejected_without_retries(store, server):
    base, _ = server
    a = store.enqueue(base + "/blocked.mp4")
    b = store.enqueue(base + "/html.mp4")
    Worker(store).run()
    assert store.job(a)["status"] == "blocked"
    assert store.job(a)["attempts"] == 1
    assert store.job(b)["status"] == "failed"


def test_url_and_credentials_encrypted(store, server):
    base, _ = server
    secret = "test-only-secret-marker-8294"
    job = store.enqueue(base + "/sample.mp4?access_token=" + secret)
    store.vault.put("meta-token", secret)
    assert store.job(job)["url"].endswith(secret)
    assert store.vault.get("meta-token") == secret
    assert secret not in json.dumps(store.diagnostics())
    for path in store.directory.rglob("*"):
        if path.is_file():
            assert secret.encode() not in path.read_bytes()
    store.vault.forget()
    assert store.vault.get("meta-token") is None


def test_worker_lock_rejects_second_worker(store):
    with worker_lock(store.directory / "worker.lock"):
        with pytest.raises(RuntimeError):
            Worker(store).run()


def test_facebook_alias_duplicate(store):
    a = store.enqueue("https://www.facebook.com/reel/12345/?tracking=1")
    b = store.enqueue("https://www.facebook.com/watch/?v=12345")
    assert a == b


def test_meta_missing_token_is_blocked(store):
    result = meta_lookup(store, "me")
    assert result["status"] == "blocked" and not result["urls"]


def test_playwright_discovery_and_login_boundary(store, server):
    base, _ = server
    result = discover(store, base + "/page", rounds=1)
    assert result["status"] == "found", result
    assert len(result["urls"]) == 2
    gate = discover(store, base + "/login", rounds=1)
    assert gate["status"] == "blocked" and gate["urls"] == []


def test_ytdlp_direct_engine(store, server):
    base, _ = server
    job = store.enqueue(base + "/sample.mp4", "yt-dlp")
    Worker(store).run()
    assert store.job(job)["status"] == "complete", store.job(job)
    assert Path(store.job(job)["path"]).read_bytes() == PAYLOAD
