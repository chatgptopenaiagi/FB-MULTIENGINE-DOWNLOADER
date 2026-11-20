"""Archive the tested complete Windows tree and record every file's checksum."""
import hashlib
import json
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parents[1]
source=root/'dist/windows/FBMD'
destination=root/'dist/release/FBMD-0.2.0-alpha.1-windows-x64.zip'
if destination.exists():raise FileExistsError('Preserve the prior archive before creating another')
records=[]
with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as archive:
    for path in sorted(source.rglob('*')):
        if not path.is_file():continue
        with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        name=path.relative_to(source).as_posix()
        archive.write(path,'FBMD/'+name)
        records.append({'path':name,'bytes':path.stat().st_size,'sha256':digest})
(root/'evidence/windows-package-inventory.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('ARCHIVED',len(records),'files',destination.stat().st_size,'bytes')
