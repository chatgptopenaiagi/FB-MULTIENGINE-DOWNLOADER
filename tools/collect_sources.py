"""Fetch upstream corresponding sources, retain checksums; never executes upstream scripts."""

import hashlib
import json
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor

root = Path(__file__).resolve().parents[1]
dest = root / ".private/corresponding-sources"
dest.mkdir(parents=True, exist_ok=True)
sources = {
    "qtbase-6.12.0.tar.xz": "https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtbase-everywhere-src-6.12.0.tar.xz",
    "qtsvg-6.12.0.tar.xz": "https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtsvg-everywhere-src-6.12.0.tar.xz",
    "pyside-6.12.0-source.tar.gz": "https://codeload.github.com/pyside/pyside-setup/tar.gz/refs/tags/v6.12.0",
    "Python-3.13.0.tar.xz": "https://www.python.org/ftp/python/3.13.0/Python-3.13.0.tar.xz",
    "FFmpeg-8c7ef49002-windows-source.tar.gz": "https://codeload.github.com/FFmpeg/FFmpeg/tar.gz/8c7ef49002",
    "FFmpeg-Builds-7f2a6b1050d3-source.tar.gz": "https://codeload.github.com/FFmpeg-Builds/FFmpeg-Builds/tar.gz/7f2a6b1050d302144de8366afa37a75e46f326aa",
    "ffmpeg-7.1.1.tar.xz": "https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz",
    "youtubedl-android-0.18.1.zip": "https://codeload.github.com/yausername/youtubedl-android/zip/refs/tags/0.18.1",
    "yt-dlp-2025.11.12.tar.gz": "https://codeload.github.com/yt-dlp/yt-dlp/tar.gz/335653be82d5ef999cfc2879d005397402eebec1",
    "gdbm-1.26.tar.gz": "https://mirrors.kernel.org/gnu/gdbm/gdbm-1.26.tar.gz",
    "readline-8.3.tar.gz": "https://mirrors.kernel.org/gnu/readline/readline-8.3.tar.gz",
    "Python-3.12.11.tar.xz": "https://www.python.org/ftp/python/3.12.11/Python-3.12.11.tar.xz",
    "termux-packages-2ae8e839-source.tar.gz": "https://codeload.github.com/termux/termux-packages/tar.gz/2ae8e83931e61c1ee7af387d822599ef610014e1",
    "mutagen-1.47.0.tar.gz": "https://codeload.github.com/quodlibet/mutagen/tar.gz/refs/tags/release-1.47.0",
    "pycryptodome-3.23.0.tar.gz": "https://codeload.github.com/Legrandin/pycryptodome/tar.gz/refs/tags/v3.23.0",
}


def fetch(item):
    name, url = item
    path = dest / name
    if not path.is_file():
        with requests.get(url, stream=True, timeout=(20, 180)) as response:
            response.raise_for_status()
            with path.with_suffix(path.suffix + ".part").open("wb") as f:
                for chunk in response.iter_content(1024 * 1024):
                    f.write(chunk)
        path.with_suffix(path.suffix + ".part").rename(path)
    with path.open("rb") as f:
        sha = hashlib.file_digest(f, "sha256").hexdigest()
    return {"file": name, "url": url, "bytes": path.stat().st_size, "sha256": sha}


with ThreadPoolExecutor(max_workers=4) as pool:
    records = list(pool.map(fetch, sources.items()))
(dest / "UPSTREAM-SOURCES.json").write_text(
    json.dumps(records, indent=2), encoding="utf-8"
)
print(json.dumps(records, indent=2))
