from pathlib import Path
import pytest
from fbmd import native


@pytest.mark.native
def test_broken_explicit_override_never_falls_back(tmp_path, monkeypatch):
    invalid = tmp_path / "ffmpeg.exe"
    invalid.write_bytes(b"not executable")
    monkeypatch.setenv("FBMD_FFMPEG", str(invalid))
    result = native.multimedia()
    assert result["source"] == "external override"
    assert result["status"] == "BROKEN"
    from fbmd.engine import ffmpeg_path

    with pytest.raises(RuntimeError):
        ffmpeg_path()


@pytest.mark.native
def test_native_merge_hls_and_split_selection(tmp_path):
    if native.multimedia()["status"] != "READY":
        pytest.skip("Native bundle not provisioned")
    from fbmd.native_acceptance import run_checks

    result = run_checks(tmp_path / "media")
    assert result["status"] == "PASS"
    assert any(
        p["processor"] == "Merger" and p["status"] == "finished"
        for p in result["postprocessors"]
    )
    assert {s["codec_type"] for s in result["separate_stream_merge"]["streams"]} == {
        "video",
        "audio",
    }
    existing = tmp_path / "preserve.mp4"
    existing.write_bytes(b"preserve user content")
    with pytest.raises(FileExistsError):
        native.merge_local(Path("unused"), Path("unused"), existing)
    assert existing.read_bytes() == b"preserve user content"


@pytest.mark.native
def test_bundled_selenium_discovery(tmp_path, server):
    if not (
        native.application_directory() / ".toolchain/discovery/chromedriver.exe"
    ).exists():
        pytest.skip("Native driver not provisioned")
    from fbmd.discovery import discover
    from fbmd.store import Store

    store = Store(tmp_path / "state", tmp_path / "media", allow_local=True)
    result = discover(store, server[0] + "/page", engine="selenium", rounds=1)
    assert result["status"] == "found" and len(result["urls"]) == 2, result
