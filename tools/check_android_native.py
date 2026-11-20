"""Inspect APK ELF architecture, imported libraries and page alignment per ABI."""

import io
import json
from pathlib import Path
import sys
import zipfile
from elftools.elf.elffile import ELFFile

apk = Path(sys.argv[1])
records = []
errors = []
system = {
    "libc.so",
    "libm.so",
    "libdl.so",
    "liblog.so",
    "libandroid.so",
    "libz.so",
    "libstdc++.so",
    "libOpenSLES.so",
    "libmediandk.so",
    "libjnigraphics.so",
    "libEGL.so",
    "libGLESv2.so",
    "libvulkan.so",
}
with zipfile.ZipFile(apk) as package:
    for abi, expected in [("arm64-v8a", "EM_AARCH64"), ("x86_64", "EM_X86_64")]:
        entries = {}
        for name in package.namelist():
            if name.startswith("lib/" + abi + "/") or name == 'assets/native/ffmpeg-'+abi+'.zip':
                data = package.read(name)
                if data.startswith(b"PK"):
                    with zipfile.ZipFile(io.BytesIO(data)) as nested:
                        for part in nested.namelist():
                            if not part.endswith("/") and (".so" in Path(part).name):
                                entries[name + "!" + part] = nested.read(part)
                else:
                    entries[name] = data
        available = {Path(name.split("!")[-1]).name for name in entries}
        for name, data in entries.items():
            if not data.startswith(b"\x7fELF"):
                continue
            elf = ELFFile(io.BytesIO(data))
            needed = []
            dynamic = elf.get_section_by_name(".dynamic")
            if dynamic:
                needed = [
                    tag.needed
                    for tag in dynamic.iter_tags()
                    if tag.entry.d_tag == "DT_NEEDED"
                ]
            missing = [n for n in needed if n not in available and n not in system]
            align = [
                segment["p_align"]
                for segment in elf.iter_segments()
                if segment["p_type"] == "PT_LOAD"
            ]
            record = {
                "path": name,
                "abi": abi,
                "machine": elf["e_machine"],
                "bits": elf.elfclass,
                "needed": needed,
                "missing": missing,
                "load_alignment": min(align) if align else None,
            }
            records.append(record)
            if missing or elf["e_machine"] != expected or elf.elfclass != 64:
                errors.append(record)
result = {
    "status": "PASS" if not errors else "REVIEW_REQUIRED",
    "apk": apk.name,
    "elf_count": len(records),
    "errors": errors,
    "files": records,
    "runtime_scope": "Static ABI/dependency inspection; device execution evidence is separate.",
    "has_sub_16k_alignment": any(
        r["load_alignment"] and r["load_alignment"] < 16384 for r in records
    ),
}
Path(sys.argv[2]).write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k != "files"}, indent=2))
raise SystemExit(bool(errors))
