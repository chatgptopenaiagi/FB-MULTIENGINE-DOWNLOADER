"""Unauthenticated normal-access checks; never changes access mechanisms after denial."""

import json
from datetime import datetime, timezone
from pathlib import Path
from fbmd.store import Store
from fbmd.discovery import discover, launch_browser
from fbmd.security import redact
from playwright.sync_api import sync_playwright
import yt_dlp

root = Path(__file__).resolve().parents[1]
store = Store(
    root / ".private/live-state", Path("F:/AILAB/FB-MULTIENGINE-DOWNLOADER/live-check")
)
profile = "https://www.facebook.com/profile.php?id=61595152335606&sk=reels_tab"
result = {
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "authenticated": False,
    "profile": profile,
    "discovery": discover(store, profile, rounds=3),
    "videos": [],
}
with sync_playwright() as p:
    browser = launch_browser(p, True)
    page = browser.new_page()
    try:
        response = page.goto(profile, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(1800)
        result["page"] = {
            "http": response.status if response else None,
            "title": page.title(),
            "body_excerpt": redact(page.inner_text("body")[:1200]),
        }
        page.screenshot(path=str(root / "evidence/facebook-profile.png"))
    except Exception as e:
        result["page"] = {"error_type": type(e).__name__}
    finally:
        browser.close()


class Logger:
    def debug(self, *args):
        pass

    def warning(self, *args):
        pass

    def error(self, *args):
        pass


for kind, url in [
    ("reel", "https://www.facebook.com/reel/1195289147628387"),
    ("long_video", "https://www.facebook.com/radiokicksfm/videos/3676516585958356/"),
]:
    record = {
        "kind": kind,
        "url": url,
        "source": "yt-dlp Facebook extractor public regression example",
        "downloaded": False,
    }
    try:
        with yt_dlp.YoutubeDL(
            {
                "quiet": True,
                "logger": Logger(),
                "skip_download": True,
                "noplaylist": True,
                "retries": 0,
                "extractor_retries": 0,
                "socket_timeout": 20,
            }
        ) as y:
            info = y.extract_info(url, download=False)
            record.update(
                status="metadata_accessible",
                duration=info.get("duration"),
                formats=len(info.get("formats", [])),
            )
    except Exception as e:
        message = redact(str(e))
        record.update(
            status="unavailable", error_type=type(e).__name__, detail=message[:600]
        )
    result["videos"].append(record)
(root / "evidence/facebook-live-check.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8"
)
print(json.dumps(result, indent=2))
