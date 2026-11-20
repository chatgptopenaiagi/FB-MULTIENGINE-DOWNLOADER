"""Project-controlled, checksum-pinned native runtime provisioning (no global install)."""

import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import requests

root = Path(__file__).resolve().parents[1]
lock = json.loads((root / "tools/native-windows.lock.json").read_text())
cache = root / ".toolchain/downloads"
cache.mkdir(parents=True, exist_ok=True)
archive = cache / lock["asset"]
if not archive.is_file():
    with requests.get(lock["url"], stream=True, timeout=(20, 180)) as response:
        response.raise_for_status()
        with archive.with_suffix(".part").open("wb") as f:
            for chunk in response.iter_content(1048576):
                f.write(chunk)
    archive.with_suffix(".part").rename(archive)
with archive.open("rb") as f:
    digest = hashlib.file_digest(f, "sha256").hexdigest()
if digest != lock["sha256"]:
    raise RuntimeError("Native archive checksum mismatch")
destination = root / ".toolchain/native/ffmpeg"
destination.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(archive) as z:
    for item in z.infolist():
        relative = Path(*Path(item.filename).parts[1:])
        if (
            not str(relative)
            or str(relative) == "."
            or ".." in relative.parts
            or relative.is_absolute()
        ):
            continue
        if "bin" in relative.parts:
            if (
                relative.name not in ("ffmpeg.exe", "ffprobe.exe")
                and relative.suffix.lower() != ".dll"
            ):
                continue
            target = destination / relative.name
        elif relative.parts[0] in (
            "LICENSE",
            "LICENSE.txt",
            "licenses",
            "doc",
        ) or relative.name.lower().startswith(("license", "readme")):
            target = destination / "upstream" / relative
        else:
            continue
        if item.is_dir():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with z.open(item) as source, target.open("wb") as out:
            shutil.copyfileobj(source, out)
(destination / "provenance.json").write_text(
    json.dumps(lock, indent=2), encoding="utf-8"
)
print("PINNED_NATIVE_RUNTIME_READY", len(list(destination.glob("*.dll"))), "DLLs")
