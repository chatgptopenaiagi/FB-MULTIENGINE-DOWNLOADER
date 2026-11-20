"""Collect upstream notices from the exact installed build dependencies."""

from pathlib import Path
import importlib.metadata as metadata
import json, shutil, sys

dest = Path(sys.argv[1]) / "THIRD_PARTY_LICENSES"
dest.mkdir(parents=True, exist_ok=True)
records = []
for distribution in metadata.distributions():
    name = distribution.metadata["Name"]
    version = distribution.version
    copied = []
    for f in distribution.files or []:
        if any(
            word in str(f).lower() for word in ("license", "copying", "notice")
        ) and (
            ".dist-info/" in str(f) or name.lower().startswith(("pyside", "shiboken"))
        ):
            source = Path(distribution.locate_file(f))
            if source.is_file() and source.stat().st_size < 5_000_000:
                target = dest / name / str(f).replace("/", "_")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                copied.append(target.name)
    records.append(
        {
            "name": name,
            "version": version,
            "license": distribution.metadata.get("License-Expression")
            or distribution.metadata.get("License"),
            "notices": copied,
        }
    )
(dest / "installed-dependencies.json").write_text(
    json.dumps(records, indent=2), encoding="utf-8"
)
print("DEPENDENCY_NOTICES_COLLECTED", len(records))
