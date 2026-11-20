"""Inspect every packaged PE import, architecture and native library inventory."""

import hashlib
import json
import os
from pathlib import Path
import sys
import pefile

root = Path(sys.argv[1]).resolve()
files = [p for p in root.rglob("*") if p.suffix.lower() in (".dll", ".pyd", ".exe")]
by_name = {}
for path in files:
    by_name.setdefault(path.name.lower(), []).append(path)
system = Path(os.environ["SystemRoot"]) / "System32"
records = []
errors = []
for path in files:
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories(
        directories=[
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
        ]
    )
    arch = {0x8664: "x64", 0x14C: "x86", 0xAA64: "ARM64"}.get(
        pe.FILE_HEADER.Machine, hex(pe.FILE_HEADER.Machine)
    )
    missing = []
    imports = []
    for entry in [
        *getattr(pe, "DIRECTORY_ENTRY_IMPORT", []),
        *getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", []),
    ]:
        name = entry.dll.decode().lower()
        if name.startswith(("api-ms-", "ext-ms-")):
            kind = "Windows API set"
        elif (path.parent / name).is_file():
            kind = "same directory"
        elif name in by_name:
            kind = "packaged dependency"
        elif (system / name).is_file():
            kind = "Windows system"
        else:
            kind = "MISSING"
            missing.append(name)
        imports.append({"name": name, "resolution": kind})
    if missing or arch != "x64":
        errors.append(
            {
                "path": str(path.relative_to(root)),
                "architecture": arch,
                "missing": missing,
            }
        )
    with path.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    records.append(
        {
            "path": str(path.relative_to(root)),
            "bytes": path.stat().st_size,
            "sha256": digest,
            "architecture": arch,
            "imports": imports,
        }
    )
    pe.close()
report = {
    "package": str(root),
    "pe_count": len(records),
    "errors": errors,
    "status": "PASS" if not errors else "REVIEW_REQUIRED",
    "scope": "Static import/architecture inspection. Runtime operation tests are recorded separately.",
    "files": records,
}
Path(sys.argv[2]).write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"pe_count": len(records), "errors": errors}, indent=2))
raise SystemExit(bool(errors))
