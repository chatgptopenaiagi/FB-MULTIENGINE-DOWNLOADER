"""Native runtime registry, verified capabilities, and local media processing."""

from __future__ import annotations
from functools import lru_cache
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import uuid


def application_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    source = Path(__file__).resolve().parents[2]
    if (source / "pyproject.toml").is_file():
        return source
    from platformdirs import user_data_dir

    return Path(user_data_dir("FBMultiEngine", "DragonHydra"))


def pe_architecture(path: Path) -> str:
    with path.open("rb") as stream:
        if stream.read(2) != b"MZ":
            return "not-PE"
        stream.seek(0x3C)
        offset = struct.unpack("<I", stream.read(4))[0]
        stream.seek(offset)
        if stream.read(4) != b"PE\0\0":
            return "invalid-PE"
        machine = struct.unpack("<H", stream.read(2))[0]
        return {0x8664: "x64", 0x14C: "x86", 0xAA64: "ARM64"}.get(machine, hex(machine))


def candidates() -> tuple[Path | None, str]:
    override = os.environ.get("FBMD_FFMPEG")
    if override:
        return Path(override).resolve(), "external override"
    root = application_directory()
    for folder, source in (
        (root / "engines/ffmpeg", "bundled"),
        (root / ".toolchain/native/ffmpeg", "project provisioned"),
    ):
        target = folder / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if folder.exists():
            return target, source
    found = shutil.which("ffmpeg") if not getattr(sys, "frozen", False) else None
    return (Path(found), "system PATH") if found else (None, "missing")


def execute(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


@lru_cache(maxsize=8)
def _probe_runtime(path: str, source: str, stamp: int) -> dict:
    ffmpeg = Path(path)
    ffprobe = ffmpeg.with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
    report = {
        "name": "FFmpeg / FFprobe",
        "source": source,
        "path": path,
        "ffprobe_path": str(ffprobe),
        "status": "BROKEN",
        "version": "",
        "architecture": "unknown",
        "capabilities": [],
        "diagnostic": "",
    }
    try:
        if os.name == "nt":
            report["architecture"] = pe_architecture(ffmpeg)
            if report["architecture"] != "x64" or pe_architecture(ffprobe) != "x64":
                raise RuntimeError("Native executables must both be Windows x64")
        else:
            report["architecture"] = platform.machine()
        versions = [
            execute([str(executable), "-version"]) for executable in (ffmpeg, ffprobe)
        ]
        for name, result in zip(("ffmpeg", "ffprobe"), versions):
            if result.returncode or not result.stdout.startswith(name + " version "):
                raise RuntimeError("Executable version probe failed")
        report["version"] = versions[0].stdout.splitlines()[0]
        report["ffprobe_version"] = versions[1].stdout.splitlines()[0]
        report["configuration"] = next(
            (
                x
                for x in versions[0].stdout.splitlines()
                if x.startswith("configuration:")
            ),
            "",
        )
        outputs = {}
        for option in ("decoders", "encoders", "formats", "protocols"):
            result = execute([str(ffmpeg), "-hide_banner", "-" + option])
            if result.returncode:
                raise RuntimeError("Capability probe failed")
            outputs[option] = result.stdout
        required = ("h264", "aac")
        if (
            not all(codec in outputs["decoders"] for codec in required)
            or "mp4" not in outputs["formats"]
        ):
            raise RuntimeError("Required H.264/AAC/MP4 support is missing")
        report["capabilities"] = [
            "H.264 decode",
            "AAC decode",
            "MP4 inspect",
            "local stream-copy merge",
            "decode integrity check",
        ]
        if "hls" in outputs["formats"]:
            report["capabilities"].append("HLS demux/remux")
        if "dash" in outputs["formats"]:
            report["capabilities"].append("DASH demux/remux")
        if "https" in outputs["protocols"]:
            report["capabilities"].append("HTTPS transport")
        report["codec_lines"] = [
            x.strip()
            for x in outputs["decoders"].splitlines()
            if any(
                c in x.split() for c in ("h264", "hevc", "aac", "opus", "vp9", "av1")
            )
        ]
        report.update(
            status="READY",
            diagnostic="Both executables and required codec/container capabilities passed.",
        )
    except Exception as error:
        report["diagnostic"] = (
            f"{type(error).__name__}: native runtime verification failed; repair the bundle or select a valid override."
        )
    return report


def multimedia() -> dict:
    path, source = candidates()
    if path is None:
        return {
            "name": "FFmpeg / FFprobe",
            "source": source,
            "status": "MISSING",
            "version": "",
            "architecture": platform.machine(),
            "capabilities": [],
            "diagnostic": "Native runtime not provisioned.",
        }
    probe = path.with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
    stamp = max((p.stat().st_mtime_ns for p in (path, probe) if p.exists()), default=0)
    return dict(_probe_runtime(str(path), source, stamp))


def registry() -> dict:
    engines = [multimedia()]
    for label, package in (
        ("yt-dlp", "yt-dlp"),
        ("Qt / PySide", "PySide6"),
        ("Playwright", "playwright"),
        ("Selenium", "selenium"),
    ):
        try:
            version = importlib.metadata.version(package)
            status = "INSTALLED"
        except importlib.metadata.PackageNotFoundError:
            version, status = "", "MISSING"
        engines.append(
            {
                "name": label,
                "version": version,
                "architecture": platform.machine(),
                "source": "bundled"
                if getattr(sys, "frozen", False)
                else "Python environment",
                "status": status,
                "diagnostic": "Package metadata present; operational checks are reported separately."
                if version
                else "Optional package absent.",
            }
        )
    engines.append(
        {
            "name": "Python",
            "version": platform.python_version(),
            "architecture": platform.machine(),
            "source": "bundled" if getattr(sys, "frozen", False) else "interpreter",
            "status": "READY",
            "diagnostic": "Current application runtime.",
        }
    )
    return {
        "application_directory": str(application_directory()),
        "frozen": bool(getattr(sys, "frozen", False)),
        "engines": engines,
    }


def require_runtime() -> dict:
    runtime = multimedia()
    if runtime["status"] != "READY":
        raise RuntimeError(runtime["diagnostic"])
    return runtime


def inspect_media(path: Path) -> dict:
    runtime = require_runtime()
    result = execute(
        [
            runtime["ffprobe_path"],
            "-v",
            "error",
            "-protocol_whitelist",
            "file,crypto,data",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(Path(path).resolve()),
        ]
    )
    if result.returncode:
        raise ValueError("Media inspection failed")
    data = json.loads(result.stdout)
    if not data.get("streams"):
        raise ValueError("No media streams found")
    return {
        "format": data.get("format", {}).get("format_name"),
        "duration": float(data.get("format", {}).get("duration") or 0),
        "streams": [
            {
                key: stream.get(key)
                for key in (
                    "index",
                    "codec_type",
                    "codec_name",
                    "width",
                    "height",
                    "sample_rate",
                    "channels",
                    "start_time",
                    "duration",
                )
            }
            for stream in data["streams"]
        ],
    }


def merge_local(video: Path, audio: Path, output: Path) -> dict:
    runtime = require_runtime()
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError("Output already exists; preserved")
    output.parent.mkdir(parents=True, exist_ok=True)
    part = output.with_name(output.name + "." + uuid.uuid4().hex + ".part")
    args = [runtime["path"], "-nostdin", "-v", "error", "-xerror"]
    for path in (video, audio):
        args += [
            "-protocol_whitelist",
            "file,crypto,data",
            "-i",
            str(Path(path).resolve()),
        ]
    args += [
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        "-f",
        "mp4",
        str(part),
    ]
    result = execute(args, timeout=600)
    if result.returncode:
        raise ValueError("Local merge failed; partial retained for diagnostics")
    info = inspect_media(part)
    if not {"video", "audio"} <= {s["codec_type"] for s in info["streams"]}:
        raise ValueError("Merged output is missing audio or video")
    # A hard link creates the destination atomically and refuses existing files.
    os.link(part, output)
    part.unlink()
    return info
