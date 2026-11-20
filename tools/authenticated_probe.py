"""Use only an explicitly saved dedicated-app session; never reads other browser profiles."""

import json
from pathlib import Path
import time
from fbmd.store import Store
from fbmd.discovery import discover
from fbmd.engine import Worker

root = Path(__file__).resolve().parents[1]
state = Path("F:/AILAB/FB-MULTIENGINE-DOWNLOADER/verification-20261120/desktop-state")
assert (state / "vault/browser.enc").is_file(), "No dedicated opt-in saved session"
store = Store(
    state, Path("F:/AILAB/FB-MULTIENGINE-DOWNLOADER/authenticated-acceptance")
)
profile = "https://www.facebook.com/profile.php?id=61595152335606&sk=reels_tab"
started = time.time()
result = discover(store, profile, rounds=20)
report = {
    "profile": profile,
    "engine": "playwright",
    "session": "explicitly saved in dedicated app; values excluded",
    "discovery_status": result["status"],
    "discovered_count": len(result["urls"]),
    "coverage": result["detail"],
    "scroll_limit": 20,
    "downloads": [],
}
if result["status"] == "found":
    for url in result["urls"][:2]:
        job = store.enqueue(url)
        report["downloads"].append(job)
    Worker(store).run()
    report["downloads"] = [
        {
            k: v
            for k, v in store.job(job).items()
            if k
            in (
                "id",
                "status",
                "downloaded",
                "path",
                "sha256",
                "attempts",
                "error",
                "engine",
            )
        }
        for job in report["downloads"]
    ]
report["elapsed_seconds"] = round(time.time() - started, 3)
(root / "evidence/authenticated-profile-check.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(json.dumps(report, indent=2))
