"""Optional explicit wheel provisioning; Windows portable/installer already include engines."""

import hashlib
import json
from pathlib import Path
import platform
import shutil
import zipfile
import requests
from .native import application_directory


def provision() -> dict:
    if platform.system() != "Windows" or platform.machine().lower() not in (
        "amd64",
        "x86_64",
    ):
        raise RuntimeError("This pinned native provisioner supports Windows x64 only")
    lock = json.loads(Path(__file__).with_name("native-windows.lock.json").read_text())
    root = application_directory()
    cache = root / "native-downloads"
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / lock["asset"]
    if not archive.exists():
        urls = [
            lock["url"],
            "https://github.com/chatgptopenaiagi/FB-MULTIENGINE-DOWNLOADER/releases/download/v0.2.0-alpha.1/FBMD-0.2.0-alpha.1-native-windows-x64.zip",
        ]
        for url in urls:
            response = requests.get(url, stream=True, timeout=(20, 180))
            if response.status_code == 404:
                response.close()
                continue
            response.raise_for_status()
            with response, archive.with_suffix(".part").open("wb") as f:
                for chunk in response.iter_content(1048576):
                    f.write(chunk)
            archive.with_suffix(".part").rename(archive)
            break
    with archive.open("rb") as f:
        actual = hashlib.file_digest(f, "sha256").hexdigest()
    if actual != lock["sha256"]:
        raise RuntimeError("Native checksum mismatch")
    destination = root / "engines/ffmpeg"
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if item.is_dir():
                continue
            relative = Path(*Path(item.filename).parts[1:])
            if ".." in relative.parts or relative.is_absolute():
                raise ValueError("Unsafe archive path")
            if (
                relative.parts
                and relative.parts[0] == "bin"
                and (
                    relative.name in ("ffmpeg.exe", "ffprobe.exe")
                    or relative.suffix.lower() == ".dll"
                )
            ):
                target = destination / relative.name
            elif relative.name.lower().startswith(("license", "copying")):
                target = destination / "licenses" / relative.name
            else:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(item) as source, target.open("wb") as out:
                shutil.copyfileobj(source, out)
    (destination / "provenance.json").write_text(
        json.dumps(lock, indent=2), encoding="utf-8"
    )
    return {"status": "provisioned", "directory": str(destination), "sha256": actual}
