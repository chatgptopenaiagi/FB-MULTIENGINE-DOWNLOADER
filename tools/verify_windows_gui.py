"""Drive the packaged EXE outside source through real accessible GUI controls."""

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from pywinauto import Application
from pywinauto.timings import wait_until

root = Path(sys.argv[1]).resolve()
exe = root / "windows/FBMD/FBMD.exe"
state = root / "desktop-acceptance-state"
media = root / "desktop-acceptance-media"
env = os.environ.copy()
env.pop("PYTHONPATH", None)
env.update(FBMD_STATE=str(state), FBMD_MEDIA=str(media))
proc = subprocess.Popen([str(exe)], cwd=str(root), env=env)
app = Application(backend="uia").connect(process=proc.pid, timeout=45)
win = app.window(title="FB MultiEngine Downloader")
win.wait("visible", timeout=45)
edits = [e for e in win.descendants(control_type="Edit") if e.is_visible()]
print("VISIBLE_EDITS", len(edits), flush=True)
url = "https://www.facebook.com/reel/1195289147628387"
edits[0].set_edit_text(url)
win.child_window(title="Add URLs", control_type="Button").invoke()
time.sleep(1)
win.child_window(title="Start", control_type="Button").invoke()


def rows():
    with sqlite3.connect(state / "queue.sqlite3") as db:
        db.row_factory = sqlite3.Row
        return [
            dict(r)
            for r in db.execute(
                "SELECT id,status,display,path,sha256,downloaded,attempts,error FROM jobs"
            )
        ]


wait_until(
    120,
    1,
    lambda: bool(rows()) and rows()[0]["status"] in ("complete", "failed", "blocked"),
)
record = rows()[0]
assert record["status"] == "complete", record
win.capture_as_image().save(root / "windows-packaged-ui-review.png")
win.close()
proc.wait(timeout=20)
proc = subprocess.Popen([str(exe)], cwd=str(root), env=env)
app = Application(backend="uia").connect(process=proc.pid, timeout=45)
win = app.window(title="FB MultiEngine Downloader")
win.wait("visible", timeout=45)
edits = [e for e in win.descendants(control_type="Edit") if e.is_visible()]
edits[0].set_edit_text(url)
win.child_window(title="Add URLs", control_type="Button").invoke()
time.sleep(1)
assert len(rows()) == 1 and rows()[0]["status"] == "complete"
win.close()
proc.wait(timeout=20)
result = {
    "artifact": str(exe),
    "outside_source": True,
    "real_ui_enqueue_start_download": True,
    "relaunch_no_duplicate": True,
    "job": record,
}
(root / "windows-verification.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8"
)
print(json.dumps(result, indent=2))
