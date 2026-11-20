import csv
import json
from pathlib import Path


def import_urls(path: Path, limit: int = 1000) -> list[str]:
    text = Path(path).read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".csv":
        rows = list(csv.DictReader(text.splitlines()))
        urls = [
            row.get("url") or row.get("URL") or row.get("source_url") or ""
            for row in rows
        ]
    else:
        urls = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    if len(urls) > limit:
        raise ValueError(f"Batch exceeds {limit} items")
    return [url for url in urls if url]


def export_manifest(store, path: Path):
    rows = store.rows()
    if path.suffix.lower() == ".csv":
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            fields = (
                list(rows[0]) if rows else ["id", "display", "status", "path", "sha256"]
            )
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                # Prevent spreadsheet formula evaluation of untrusted source metadata.
                writer.writerow(
                    {
                        k: "'" + v
                        if isinstance(v, str)
                        and v.startswith(("=", "+", "-", "@", "\t", "\r"))
                        else v
                        for k, v in row.items()
                    }
                )
    else:
        path.write_text(
            json.dumps({"schema_version": 1, "jobs": rows}, indent=2), encoding="utf-8"
        )
