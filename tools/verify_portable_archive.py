"""Verify delivered ZIP bytes and execute its extracted app with a minimal environment."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

root=Path(__file__).resolve().parents[1]
archive=Path(sys.argv[1]).resolve();destination=Path(sys.argv[2]).resolve()
destination.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name in z.namelist():
        target=(destination/name).resolve()
        if not target.is_relative_to(destination):raise ValueError('Unsafe ZIP path')
    z.extractall(destination)
inventory=json.loads((root/'evidence/windows-package-inventory.json').read_text())
for item in inventory:
    with (destination/'FBMD'/item['path']).open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=item['sha256']:raise ValueError('Extracted checksum mismatch')
env=os.environ.copy()
for name in ('PYTHONPATH','PYTHONHOME','FBMD_FFMPEG','VIRTUAL_ENV'):env.pop(name,None)
env.update(PATH=str(Path(os.environ['SystemRoot'])/'System32'),FBMD_STATE=str(destination/'state'),FBMD_MEDIA=str(destination/'media'))
reports={}
for name,args in [('engines',['engines']),('native',['native-test',str(destination/'fixture')]),('gui',['gui-check',str(destination/'gui')])]:
    report=destination/(name+'.json')
    subprocess.run([str(destination/'FBMD/FBMD.exe'),'--report',str(report),*args],cwd=destination,env=env,timeout=180,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    reports[name]=json.loads(report.read_text())
with archive.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
result={'status':'PASS','archive':archive.name,'sha256':digest,'all_files_matched':len(inventory),'path_used':env['PATH'],'checks':reports}
(root/'evidence/portable-archive-verification.json').write_text(json.dumps(result,indent=2))
print('ZIP_EXTRACTION_AND_RUNTIME_PASS',len(inventory))
