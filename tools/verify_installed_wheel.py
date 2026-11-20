"""Execute with an independently installed wheel; source tree must not be on sys.path."""

import hashlib
import json
import sys
from pathlib import Path
from fbmd.client import Downloader
import fbmd

destination = Path(sys.argv[1])
assert "site-packages" in str(fbmd.__file__), fbmd.__file__
app = Downloader(destination / "state", destination / "media")
url = "https://www.facebook.com/reel/1195289147628387"
job = app.enqueue(url)
assert app.enqueue(url) == job
app.run()
record = app.history()[0]
if record["status"] != "complete":
    print(json.dumps(record))
    raise SystemExit(2)
path = Path(record["path"])
with path.open("rb") as stream:
    digest = hashlib.file_digest(stream, "sha256").hexdigest()
assert digest == record["sha256"]
assert (
    Downloader(destination / "state", destination / "media").history()[0]["sha256"]
    == digest
)
result = {
    "installed_module": str(fbmd.__file__),
    "python": sys.version,
    "real_facebook_reel": url,
    "record": record,
    "reopen_and_duplicate_checks": "passed",
}
(destination / "wheel-verification.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8"
)
print(json.dumps(result, indent=2))
