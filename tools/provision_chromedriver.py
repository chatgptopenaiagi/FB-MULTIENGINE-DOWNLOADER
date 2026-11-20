"""Obtain the driver matching the pinned Playwright browser from Google's official distribution."""

import hashlib
import json
from pathlib import Path
import zipfile
import requests
import playwright

root = Path(__file__).resolve().parents[1]
metadata = json.loads(
    (Path(playwright.__file__).parent / "driver/package/browsers.json").read_text()
)
version = next(
    x["browserVersion"] for x in metadata["browsers"] if x["name"] == "chromium"
)
url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/win64/chromedriver-win64.zip"
archive = root / ".toolchain/downloads" / f"chromedriver-{version}.zip"
if not archive.exists():
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    archive.write_bytes(response.content)
dest = root / ".toolchain/discovery"
dest.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(archive) as z:
    for item in z.infolist():
        if item.is_dir():
            continue
        name = Path(item.filename).name
        (dest / name).write_bytes(z.read(item))
record = {
    "source": url,
    "version": version,
    "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    "verification": "Official HTTPS distribution; exact runtime version and Selenium operation tested separately. No upstream checksum was supplied.",
}
(dest / "provenance.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps(record, indent=2))
