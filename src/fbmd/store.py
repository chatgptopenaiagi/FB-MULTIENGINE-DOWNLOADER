from __future__ import annotations
from contextlib import contextmanager
import hashlib
from pathlib import Path
import sqlite3
import time
from .network import check_public
from urllib.parse import urlsplit, parse_qs, urlunsplit
from .security import Vault, redact, safe_url


def validate_url(url: str) -> str:
    url = url.strip()
    p = urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
        raise ValueError("Use an HTTP(S) URL without embedded credentials")
    if len(url) > 16000:
        raise ValueError("URL is too long")
    return url


def identity(url: str) -> str:
    p = urlsplit(validate_url(url))
    host = p.hostname.lower()
    if host == "facebook.com" or host.endswith(".facebook.com"):
        import re

        match = re.search(r"/(?:reel|videos)/(\d+)", p.path)
        vid = match[1] if match else parse_qs(p.query).get("v", [None])[0]
        if vid and vid.isdigit():
            return "facebook:" + vid
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", p.query, ""))


class Store:
    def __init__(self, directory: Path, media: Path, *, allow_local: bool = False):
        self.allow_local = (
            allow_local  # Embedded fixture harness only; never exposed by CLI/API.
        )
        self.directory, self.media = Path(directory).resolve(), Path(media).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.media.mkdir(parents=True, exist_ok=True)
        self.vault = Vault(self.directory / "vault")
        self.path = self.directory / "queue.sqlite3"
        with self.connection() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS jobs(
              id INTEGER PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL, url TEXT NOT NULL,
              display TEXT NOT NULL, engine TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
              downloaded INTEGER NOT NULL DEFAULT 0, total INTEGER NOT NULL DEFAULT 0,
              attempts INTEGER NOT NULL DEFAULT 0, next_try REAL NOT NULL DEFAULT 0,
              error TEXT NOT NULL DEFAULT '', path TEXT NOT NULL DEFAULT '',
              sha256 TEXT NOT NULL DEFAULT '', etag TEXT NOT NULL DEFAULT '',
              created REAL NOT NULL, updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, job_id INTEGER, at REAL, kind TEXT, message TEXT);
            CREATE TABLE IF NOT EXISTS discovery(id INTEGER PRIMARY KEY, at REAL, engine TEXT, source TEXT, outcome TEXT, found INTEGER, detail TEXT);
            """)
            columns = {r[1] for r in db.execute("PRAGMA table_info(jobs)")}
            for name, definition in {
                "quality": "TEXT NOT NULL DEFAULT 'best'",
                "title": "TEXT NOT NULL DEFAULT ''",
                "resolution": "TEXT NOT NULL DEFAULT ''",
                "content_type": "TEXT NOT NULL DEFAULT ''",
                "rate": "REAL NOT NULL DEFAULT 0",
            }.items():
                if name not in columns:
                    db.execute(f"ALTER TABLE jobs ADD COLUMN {name} {definition}")
            db.execute("PRAGMA user_version=1")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def enqueue(self, url: str, engine="auto", quality="best") -> int:
        url = validate_url(url)
        check_public(url, self.allow_local)
        if quality not in ("best", "1080", "720", "480", "360", "mp4"):
            raise ValueError("Unknown quality ceiling")
        if engine not in ("auto", "http", "yt-dlp"):
            raise ValueError("Unknown download engine")
        fingerprint = hashlib.sha256(identity(url).encode()).hexdigest()
        now = time.time()
        with self.connection() as db:
            db.execute(
                "INSERT OR IGNORE INTO jobs(fingerprint,url,display,engine,quality,created,updated) VALUES(?,?,?,?,?,?,?)",
                (
                    fingerprint,
                    self.vault.seal(url),
                    safe_url(url),
                    engine,
                    quality,
                    now,
                    now,
                ),
            )
            return db.execute(
                "SELECT id FROM jobs WHERE fingerprint=?", (fingerprint,)
            ).fetchone()[0]

    def rows(self):
        with self.connection() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT id,display,engine,status,downloaded,total,attempts,error,path,sha256,created,updated,quality,title,resolution,content_type,rate FROM jobs ORDER BY id DESC"
                )
            ]

    def job(self, job_id: int):
        with self.connection() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise ValueError("Job not found")
        result = dict(row)
        result["url"] = self.vault.open(result["url"])
        return result

    def update(self, job_id, **fields):
        allowed = {
            "status",
            "downloaded",
            "total",
            "attempts",
            "next_try",
            "error",
            "path",
            "sha256",
            "etag",
            "engine",
            "quality",
            "title",
            "resolution",
            "content_type",
            "rate",
        }
        if not fields.keys() <= allowed:
            raise ValueError("Invalid job field")
        fields["updated"] = time.time()
        with self.connection() as db:
            db.execute(
                "UPDATE jobs SET " + ",".join(f"{k}=?" for k in fields) + " WHERE id=?",
                (*fields.values(), job_id),
            )

    def pause(self, job_id=None):
        with self.connection() as db:
            sql = "UPDATE jobs SET status='paused',updated=? WHERE status IN ('queued','running','retry')"
            db.execute(
                sql + (" AND id=?" if job_id is not None else ""),
                (time.time(), job_id) if job_id is not None else (time.time(),),
            )

    def resume(self, job_id=None):
        with self.connection() as db:
            sql = "UPDATE jobs SET status='queued',attempts=0,next_try=CASE WHEN error LIKE 'RATE_LIMITED:%' THEN next_try ELSE 0 END,error='',updated=? WHERE status IN ('paused','failed','blocked','retry')"
            db.execute(
                sql + (" AND id=?" if job_id is not None else ""),
                (time.time(), job_id) if job_id is not None else (time.time(),),
            )

    def cancel(self, job_id=None):
        with self.connection() as db:
            sql = "UPDATE jobs SET status='cancelled',updated=? WHERE status IN ('queued','running','retry','paused','failed','blocked')"
            db.execute(
                sql + (" AND id=?" if job_id is not None else ""),
                (time.time(), job_id) if job_id is not None else (time.time(),),
            )

    def recover(self):
        with self.connection() as db:
            db.execute(
                "UPDATE jobs SET status='queued',error='Recovered interrupted worker' WHERE status='running'"
            )

    def claim(self):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT id FROM jobs WHERE status IN ('queued','retry') AND next_try<=? ORDER BY id LIMIT 1",
                (time.time(),),
            ).fetchone()
            if row:
                db.execute(
                    "UPDATE jobs SET status='running',attempts=attempts+1,updated=? WHERE id=?",
                    (time.time(), row[0]),
                )
                return row[0]
        return None

    def event(self, job_id, kind, message):
        with self.connection() as db:
            db.execute(
                "INSERT INTO events(job_id,at,kind,message) VALUES(?,?,?,?)",
                (job_id, time.time(), kind, redact(message)),
            )

    def record_discovery(self, engine, url, result):
        with self.connection() as db:
            db.execute(
                "INSERT INTO discovery(at,engine,source,outcome,found,detail) VALUES(?,?,?,?,?,?)",
                (
                    time.time(),
                    engine,
                    safe_url(url),
                    result["status"],
                    len(result["urls"]),
                    redact(result.get("detail", "")),
                ),
            )

    def diagnostics(self):
        with self.connection() as db:
            events = [
                dict(r)
                for r in db.execute("SELECT * FROM events ORDER BY id DESC LIMIT 200")
            ]
            discovery = [
                dict(r)
                for r in db.execute("SELECT * FROM discovery ORDER BY id DESC LIMIT 50")
            ]
        return {"jobs": self.rows(), "events": events, "discovery": discovery}
