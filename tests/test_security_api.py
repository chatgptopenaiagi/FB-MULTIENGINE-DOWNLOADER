import json
import socket
import pytest
from fastapi.testclient import TestClient
from fbmd.api import create_app
from fbmd.store import Store, validate_url, identity
from fbmd.network import check_public
from fbmd.security import redact
from fbmd.accounts import import_cookies, status
from fbmd.manifest import import_urls, export_manifest


@pytest.mark.parametrize(
    "url",
    [
        "file:///C:/Windows/win.ini",
        "http://127.0.0.1/a",
        "http://[::1]/a",
        "http://169.254.169.254/latest",
        "http://10.1.2.3/a",
        "http://192.168.1.2/a",
        "http://user:pass@example.com/a",
        "http://localhost/a",
        "http://example.com:5000/a",
    ],
)
def test_reject_internal_urls(url):
    with pytest.raises(ValueError):
        check_public(url)


def test_dns_rebinding_validation(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))
        ],
    )
    with pytest.raises(ValueError):
        check_public("https://public-looking.example/video.mp4")


def test_exact_profile_url_preserved():
    url = "https://www.facebook.com/profile.php?id=61595152335606&sk=reels_tab"
    assert validate_url(url) == url
    assert identity(url) == url
    assert identity("https://fb.watch/abc/") == "https://fb.watch/abc/"


def test_redaction_bearer_and_queries():
    assert "dummy-secret-1829" not in redact("Authorization: Bearer dummy-secret-1829")
    assert "dummy-secret-1829" not in redact(
        "https://example.com/a?token=dummy-secret-1829"
    )


def test_api_auth_validation_and_no_secret_echo(tmp_path, server):
    store = Store(tmp_path / "state", tmp_path / "media", allow_local=True)
    client = TestClient(create_app(store, "a" * 40))
    assert client.get("/jobs").status_code == 401
    client.headers["Authorization"] = "Bearer " + "a" * 40
    response = client.post(
        "/jobs",
        json={
            "urls": [server[0] + "/sample.mp4?token=dummy-only-274"],
            "engine": "http",
        },
    )
    assert response.status_code == 200
    assert "dummy-only-274" not in client.get("/jobs").text
    assert client.post("/jobs/1/pause").status_code == 200
    assert store.job(1)["status"] == "paused"
    invalid = client.post("/jobs", json={"urls": "dummy-only-274"})
    assert invalid.status_code == 422 and "dummy-only-274" not in invalid.text


def test_cookie_import_scope_expiry_and_account_isolation(tmp_path):
    one = Store(tmp_path / "one", tmp_path / "media-one")
    two = Store(tmp_path / "two", tmp_path / "media-two")
    source = tmp_path / "selected.json"
    source.write_text(
        json.dumps(
            [
                {
                    "name": "c_user",
                    "value": "dummy-cookie-1837",
                    "domain": ".facebook.com",
                    "expires": -1,
                },
                {
                    "name": "foreign",
                    "value": "must-not-import",
                    "domain": ".example.com",
                },
                {
                    "name": "expired",
                    "value": "expired",
                    "domain": ".facebook.com",
                    "expires": 1,
                },
            ]
        )
    )
    assert import_cookies(one, source) == 1
    assert status(one)["browser_session"] == "saved_unverified"
    assert status(two)["browser_session"] == "missing_or_expired"
    assert (
        b"dummy-cookie-1837" not in (one.directory / "vault/browser.enc").read_bytes()
    )


def test_csv_and_json_manifest(tmp_path, server):
    csvfile = tmp_path / "urls.csv"
    csvfile.write_text("url\n" + server[0] + "/sample.mp4\n")
    store = Store(tmp_path / "state", tmp_path / "media", allow_local=True)
    store.enqueue(import_urls(csvfile)[0])
    store.update(1, title="=DANGEROUS()")
    out = tmp_path / "export.csv"
    export_manifest(store, out)
    assert "'=DANGEROUS()" in out.read_text(encoding="utf-8-sig")
    out = tmp_path / "export.json"
    export_manifest(store, out)
    assert json.loads(out.read_text())["schema_version"] == 1


def test_cancel_is_terminal(tmp_path, server):
    store = Store(tmp_path / "state", tmp_path / "media", allow_local=True)
    job = store.enqueue(server[0] + "/a.mp4")
    store.cancel(job)
    store.resume(job)
    assert store.job(job)["status"] == "cancelled" and store.claim() is None
