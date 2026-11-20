from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
import http.cookiejar
import os
from pathlib import Path
import re
import shutil
import sys
import threading
import time
from urllib.parse import urlsplit
import subprocess
import random
from email.utils import parsedate_to_datetime
from .network import check_public, get_public
from .security import redact
from .store import Store


class AccessBlocked(Exception):
    pass


class Paused(Exception):
    pass


class InvalidMedia(Exception):
    pass


class RateLimited(Exception):
    def __init__(self, delay):
        self.delay = delay


@contextmanager
def worker_lock(path):
    f = open(path, "a+b")
    f.seek(0)
    if os.fstat(f.fileno()).st_size == 0:
        f.write(b"0")
        f.flush()
    f.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        raise RuntimeError("Another worker is already using this queue") from None
    try:
        yield
    finally:
        f.close()


def file_hash(path: Path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ffmpeg_path():
    configured = os.environ.get("FBMD_FFMPEG")
    if configured and Path(configured).is_file():
        return configured
    bundled = Path(getattr(sys, "_MEIPASS", "")) / "ffmpeg.exe"
    return str(bundled) if bundled.is_file() else shutil.which("ffmpeg")


class Worker:
    def __init__(self, store: Store):
        self.store = store
        self.stop = threading.Event()

    def check(self, job_id):
        if self.stop.is_set() or self.store.job(job_id)["status"] in (
            "paused",
            "cancelled",
        ):
            raise Paused()

    def run(self, wait=False):
        with worker_lock(self.store.directory / "worker.lock"):
            self.store.recover()
            while not self.stop.is_set():
                job_id = self.store.claim()
                if job_id is None:
                    pending = any(
                        j["status"] in ("queued", "retry") for j in self.store.rows()
                    )
                    if not wait and not pending:
                        break
                    self.stop.wait(0.3)
                    continue
                self.execute(job_id)

    def execute(self, job_id):
        job = self.store.job(job_id)
        engine = job["engine"]
        if engine == "auto":
            ext = Path(urlsplit(job["url"]).path).suffix.lower()
            engine = (
                "http"
                if ext
                in (
                    ".mp4",
                    ".webm",
                    ".mov",
                    ".m4a",
                    ".mp3",
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".gif",
                )
                else "yt-dlp"
            )
        self.store.event(job_id, "start", f"Using {engine}; attempt {job['attempts']}")
        try:
            check_public(job["url"], self.store.allow_local)
            path = (
                self.download_http(job)
                if engine == "http"
                else self.download_ytdlp(job)
            )
            self.check(job_id)
            digest = file_hash(path)
            for other in self.store.rows():
                if (
                    other["id"] != job_id
                    and other["status"] == "complete"
                    and other["sha256"] == digest
                    and Path(other["path"]).is_file()
                    and file_hash(Path(other["path"])) == digest
                ):
                    # Only our just-created, per-job file is removed; existing media is preserved.
                    if Path(other["path"]) != path:
                        path.unlink()
                    path = Path(other["path"])
                    self.store.event(
                        job_id,
                        "deduplicated",
                        f"Identical content to job {other['id']}",
                    )
                    break
            self.store.update(
                job_id,
                status="complete",
                path=str(path),
                sha256=digest,
                downloaded=path.stat().st_size,
                total=path.stat().st_size,
                error="",
            )
            self.store.event(job_id, "complete", f"SHA256 {digest}")
        except Paused:
            if self.store.job(job_id)["status"] != "cancelled":
                self.store.update(job_id, status="paused")
            self.store.event(job_id, "paused", "Partial data retained")
        except RateLimited as e:
            self.store.update(
                job_id,
                status="paused" if e.delay > 300 or job["attempts"] >= 3 else "retry",
                next_try=time.time() + e.delay,
                error=f"RATE_LIMITED: retry after at least {e.delay} seconds",
            )
            self.store.event(
                job_id, "rate_limited", f"Retry-After {e.delay} seconds respected"
            )
        except AccessBlocked as e:
            self.store.update(job_id, status="blocked", error=redact(str(e)))
            self.store.event(job_id, "blocked", str(e))
        except Exception as e:
            # Never persist raw third-party exception text: it may include cookies or signed URLs.
            message = f"{type(e).__name__}: download failed; check network, source access and engine availability"
            status = (
                "failed"
                if job["attempts"] >= 3 or isinstance(e, InvalidMedia)
                else "retry"
            )
            self.store.update(
                job_id,
                status=status,
                error=message,
                next_try=time.time() + min(30, 2 ** job["attempts"]) + random.random(),
            )
            self.store.event(job_id, status, message)

    def download_http(self, job):
        job_id = job["id"]
        extension = Path(urlsplit(job["url"]).path).suffix.lower()
        if extension not in (
            ".mp4",
            ".webm",
            ".mov",
            ".m4a",
            ".mp3",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
        ):
            extension = ".media"
        folder = output_folder(self.store, job)
        folder.mkdir(exist_ok=True)
        part, final = (
            folder / ("media" + extension + ".part"),
            folder / ("media" + extension),
        )
        if final.exists():
            return verified_existing(final)
        offset = part.stat().st_size if part.exists() else 0
        headers = {"User-Agent": "FBMD/0.1", "Accept-Encoding": "identity"}
        # Resume only with a stable entity validator; otherwise restart safely.
        if offset and job["etag"]:
            headers.update({"Range": f"bytes={offset}-", "If-Range": job["etag"]})
        else:
            offset = 0
        with get_public(
            job["url"],
            allow_local=self.store.allow_local,
            headers=headers,
            stream=True,
            timeout=(15, 30),
        ) as response:
            if response.status_code == 429:
                retry = response.headers.get("Retry-After", "60")
                try:
                    delay = max(1, int(retry))
                except ValueError:
                    try:
                        delay = max(
                            1,
                            int(parsedate_to_datetime(retry).timestamp() - time.time()),
                        )
                    except Exception:
                        delay = 60
                raise RateLimited(delay)
            if response.status_code in (401, 403):
                raise AccessBlocked(
                    f"HTTP {response.status_code}: authentication or access permission required"
                )
            response.raise_for_status()
            if response.status_code == 206:
                match = re.fullmatch(
                    r"bytes (\d+)-(\d+)/(\d+)",
                    response.headers.get("Content-Range", ""),
                )
                if (
                    not match
                    or int(match[1]) != offset
                    or int(match[2]) < offset
                    or int(match[3]) <= int(match[2])
                ):
                    raise InvalidMedia("Invalid range response")
                total = int(match[3])
                validator = response.headers.get("ETag") or response.headers.get(
                    "Last-Modified", ""
                )
                if offset and validator != job["etag"]:
                    raise InvalidMedia("Entity changed during resume")
            elif response.status_code == 200:
                offset = 0
                total = int(response.headers.get("Content-Length") or 0)
            else:
                raise InvalidMedia("Unexpected HTTP status")
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/" in content_type or "json" in content_type:
                raise InvalidMedia("Server returned text instead of media")
            validator = response.headers.get("ETag", "")
            if validator.startswith("W/"):
                validator = ""
            validator = validator or response.headers.get("Last-Modified", "")
            self.store.update(
                job_id,
                downloaded=offset,
                total=total,
                etag=validator,
                content_type=content_type,
                engine="http",
            )
            max_bytes = int(os.environ.get("FBMD_MAX_FILE_BYTES", str(10 * 1024**3)))
            if total > max_bytes:
                raise InvalidMedia("File exceeds configured quota")
            if (
                total
                and shutil.disk_usage(folder).free
                < max(0, total - offset) + 1024 * 1024
            ):
                raise OSError("Insufficient free disk space")
            count = offset
            last_update = 0.0
            started = time.monotonic()
            with part.open("ab" if offset else "wb") as output:
                for chunk in response.iter_content(64 * 1024):
                    self.check(job_id)
                    if not chunk:
                        continue
                    if count == 0 and chunk.lstrip().lower().startswith(
                        (b"<!doctype html", b"<html", b'{"error')
                    ):
                        raise InvalidMedia("Server returned an error document")
                    output.write(chunk)
                    count += len(chunk)
                    if count > max_bytes:
                        raise InvalidMedia("File exceeds configured quota")
                    if time.monotonic() - last_update > 0.15:
                        self.store.update(
                            job_id,
                            downloaded=count,
                            total=total,
                            rate=(count - offset)
                            / max(0.001, time.monotonic() - started),
                        )
                        last_update = time.monotonic()
                output.flush()
                os.fsync(output.fileno())
            if not count or (total and count != total):
                raise InvalidMedia("Truncated or empty response")
            self.check(job_id)
            verify_media(part, extension)
            finalize(part, final)
            return final

    def download_ytdlp(self, job):
        import yt_dlp

        host = urlsplit(job["url"]).hostname or ""
        if not self.store.allow_local and not (
            host == "fb.watch"
            or host == "facebook.com"
            or host.endswith(".facebook.com")
        ):
            raise InvalidMedia(
                "yt-dlp extraction is limited to Facebook; use HTTP for public direct media"
            )
        folder = output_folder(self.store, job)
        folder.mkdir(exist_ok=True)
        staging = folder / "staging"
        staging.mkdir(exist_ok=True)
        observed = []

        def progress(data):
            self.check(job["id"])
            self.store.update(
                job["id"],
                downloaded=int(data.get("downloaded_bytes", 0)),
                total=int(
                    data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                ),
                rate=float(data.get("speed") or 0),
            )

        def finished(info):
            if info.get("status") == "finished":
                observed.append(info.get("info_dict", {}).get("filepath"))

        class QuietLogger:
            def debug(self, msg):
                pass

            def warning(self, msg):
                pass

            def error(self, msg):
                pass

        options = {
            "outtmpl": str(staging / "media.%(ext)s"),
            "noplaylist": True,
            "continuedl": True,
            "retries": 1,
            "fragment_retries": 1,
            "socket_timeout": 20,
            "quiet": True,
            "logger": QuietLogger(),
            "progress_hooks": [progress],
            "postprocessor_hooks": [finished],
            "windowsfilenames": True,
            "overwrites": False,
            "cachedir": False,
        }
        ffmpeg = ffmpeg_path()
        options["format"] = "bv*+ba/b" if ffmpeg else "b"
        if job["quality"].isdigit():
            height = job["quality"]
            options["format"] = (
                f"bv*[height<={height}]+ba/b[height<={height}]"
                if ffmpeg
                else f"b[height<={height}]"
            )
        elif job["quality"] == "mp4":
            options["format"] = (
                "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]" if ffmpeg else "b[ext=mp4]"
            )
        options["max_filesize"] = int(
            os.environ.get("FBMD_MAX_FILE_BYTES", str(10 * 1024**3))
        )
        if ffmpeg:
            options["ffmpeg_location"] = ffmpeg
        state = self.store.vault.get("browser", {})
        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                for c in state.get("cookies", []):
                    domain = c.get("domain", "")
                    if domain.lstrip(".") == "facebook.com" or domain.endswith(
                        ".facebook.com"
                    ):
                        downloader.cookiejar.set_cookie(
                            http.cookiejar.Cookie(
                                0,
                                c["name"],
                                c["value"],
                                None,
                                False,
                                domain,
                                True,
                                domain.startswith("."),
                                c.get("path", "/"),
                                True,
                                c.get("secure", True),
                                int(c["expires"]) if c.get("expires", -1) > 0 else None,
                                False,
                                None,
                                None,
                                {"HttpOnly": c.get("httpOnly", False)},
                                False,
                            )
                        )
                info = downloader.extract_info(job["url"], download=True)
                if not info or info.get("_type") in ("playlist", "multi_video"):
                    raise InvalidMedia("Submit individual video URLs")
                self.store.update(
                    job["id"],
                    title=redact(info.get("title", "")),
                    resolution=str(info.get("resolution") or ""),
                    content_type="video/" + str(info.get("ext", "unknown")),
                    engine="yt-dlp",
                )
                candidates = [
                    info.get("filepath"),
                    *observed,
                    downloader.prepare_filename(info),
                ]
                for path in candidates:
                    if path and Path(path).is_file() and Path(path).stat().st_size > 0:
                        verify_media(Path(path), Path(path).suffix)
                        final = folder / ("media" + Path(path).suffix)
                        finalize(Path(path), final)
                        return final
                files = [
                    p
                    for p in staging.iterdir()
                    if p.suffix in (".mp4", ".webm", ".mkv", ".mov", ".m4a", ".mp3")
                    and p.stat().st_size
                ]
                if len(files) == 1:
                    verify_media(files[0], files[0].suffix)
                    final = folder / ("media" + files[0].suffix)
                    finalize(files[0], final)
                    return final
                raise InvalidMedia("No completed media output")
        except yt_dlp.utils.DownloadError as e:
            if self.stop.is_set() or self.store.job(job["id"])["status"] == "paused":
                raise Paused() from None
            if any(
                word in str(e).lower()
                for word in (
                    "login",
                    "log in",
                    "private",
                    "403",
                    "401",
                    "checkpoint",
                    "captcha",
                    "not available",
                )
            ):
                raise AccessBlocked(
                    "Source requires authentication, is unavailable or is restricted. No bypass attempted."
                ) from None
            raise RuntimeError("Extractor failed") from None


def output_folder(store, job):
    return store.media / f"job-{job['id']:06d}-{job['fingerprint'][:12]}"


def verified_existing(path: Path):
    receipt = path.with_suffix(path.suffix + ".verified.json")
    if not receipt.is_file():
        raise InvalidMedia(
            "Existing unverified file preserved; select another destination"
        )
    with path.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if json.loads(receipt.read_text())["sha256"] != digest:
        raise InvalidMedia("Existing file checksum mismatch; file preserved")
    return path


def finalize(source: Path, target: Path):
    if target.exists():
        verified_existing(target)
        with source.open("rb") as f:
            a = hashlib.file_digest(f, "sha256").hexdigest()
        with target.open("rb") as f:
            b = hashlib.file_digest(f, "sha256").hexdigest()
        if a != b:
            raise InvalidMedia("Existing output differs; file preserved")
        source.unlink()
        return
    with source.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    receipt = target.with_suffix(target.suffix + ".verified.json")
    receipt.write_text(
        json.dumps({"sha256": digest, "bytes": source.stat().st_size}), encoding="utf-8"
    )
    # rename refuses an existing file on Windows; worker lock serializes this store.
    source.rename(target)


def verify_media(path: Path, extension: str):
    if extension in (".mp4", ".m4a", ".mov"):
        with path.open("rb") as f:
            header = f.read(64)
        if b"ftyp" not in header:
            raise InvalidMedia("Missing ISO media container header")
    ffmpeg = ffmpeg_path()
    if ffmpeg and extension in (".mp4", ".webm", ".mov", ".mkv", ".m4a", ".mp3"):
        result = subprocess.run(
            [ffmpeg, "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=600,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode:
            raise InvalidMedia("Media decode integrity check failed")
