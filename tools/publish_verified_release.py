"""Publish only an existing draft whose assets match an explicit acceptance receipt."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

tag = os.environ["RELEASE_TAG"]
if not re.fullmatch(r"v\d+\.\d+\.\d+-alpha\.\d+", tag):
    raise ValueError("Only explicit alpha tags supported")
repo = "chatgptopenaiagi/FB-MULTIENGINE-DOWNLOADER"
meta = json.loads(
    subprocess.check_output(
        ["gh", "release", "view", tag, "--repo", repo, "--json", "isDraft,tagName"]
    )
)
if not meta["isDraft"]:
    raise RuntimeError("Refusing to change an already public release")
dest = Path(".private/release-download")
dest.mkdir(parents=True, exist_ok=False)
subprocess.run(
    ["gh", "release", "download", tag, "--repo", repo, "--dir", str(dest)], check=True
)
report = json.loads((dest / "verification.json").read_text())
if report["release_tag"] != tag or report["status"] not in (
    "VERIFIED_PARTIAL",
    "VERIFIED",
):
    raise RuntimeError("Missing verified acceptance status")
required = {"windows_packaged_ui", "wheel_installed", "android_release_local_download"}
if any(report["checks"].get(name) != "PASS" for name in required):
    raise RuntimeError("Missing platform acceptance gate")
seen = set()
for line in (dest / "SHA256SUMS.txt").read_text().splitlines():
    expected, name = line.split("  ", 1)
    if Path(name).name != name or not re.fullmatch("[0-9a-f]{64}", expected):
        raise ValueError("Unsafe checksum entry")
    path = dest / name
    with path.open("rb") as f:
        actual = hashlib.file_digest(f, "sha256").hexdigest()
    if actual != expected:
        raise RuntimeError("Artifact checksum mismatch: " + name)
    seen.add(name)
if not {p.name for p in dest.iterdir() if p.name != "SHA256SUMS.txt"} <= seen:
    raise RuntimeError("Unlisted asset")
if (
    not any(n.endswith(".apk") for n in seen)
    or not any(n.endswith(".whl") for n in seen)
    or not any("windows-x64.zip" in n for n in seen)
):
    raise RuntimeError("Incomplete artifact set")
subprocess.run(
    ["gh", "release", "edit", tag, "--repo", repo, "--draft=false", "--prerelease"],
    check=True,
)
print("Published verified partial prerelease", tag, "assets", len(seen))
