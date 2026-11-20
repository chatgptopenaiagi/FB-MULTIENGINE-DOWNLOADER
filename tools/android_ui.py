"""Device UI helper: dumps, taps by visible text, screenshots. No app-private data reads."""

import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
adb = str(root / ".toolchain/android-sdk/platform-tools/adb.exe")


def run(*args):
    return subprocess.run(
        [adb, "-s", "emulator-5556", *args], capture_output=True, check=True
    ).stdout


def nodes():
    run("shell", "uiautomator", "dump", "/sdcard/fbmd-ui.xml")
    return ET.fromstring(run("shell", "cat", "/sdcard/fbmd-ui.xml")).iter("node")


if sys.argv[1] == "dump":
    for n in nodes():
        if n.get("text") or n.get("content-desc"):
            print(n.get("text"), n.get("content-desc"), n.get("bounds"))
elif sys.argv[1] == "tap":
    text = sys.argv[2]
    matches = [
        n for n in nodes() if n.get("text") == text or n.get("content-desc") == text
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one visible match for {text}; got {len(matches)}")
    x1, y1, x2, y2 = map(int, re.findall(r"\d+", matches[0].get("bounds")))
    run("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
    time.sleep(0.5)
elif sys.argv[1] == "screenshot":
    Path(sys.argv[2]).write_bytes(run("exec-out", "screencap", "-p"))
