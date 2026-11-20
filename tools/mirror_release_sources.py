"""Recreate an already verified source ZIP byte-for-byte from pinned public upstreams."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import requests

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'release-support/source-archive.json').read_text())
cache=root/'.private/corresponding-sources';cache.mkdir(parents=True,exist_ok=True)
output=root/'.private/mirrored-assets';output.mkdir(parents=True,exist_ok=True)
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def fetch(item):
    if 'text' in item:return item
    path=root/item['local'] if 'local' in item else cache/item['cache_path']
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        with requests.get(item['url'],stream=True,timeout=(30,240)) as response:
            response.raise_for_status()
            with path.with_suffix('.part').open('wb') as f:
                for chunk in response.iter_content(1048576):f.write(chunk)
        path.with_suffix('.part').rename(path)
    if digest(path)!=item['sha256']:raise ValueError('Upstream source checksum mismatch: '+item['name'])
    return {**item,'path':path}
with ThreadPoolExecutor(max_workers=6) as pool:items=list(pool.map(fetch,manifest['items']))
target=output/manifest['name']
with zipfile.ZipFile(target,'w',allowZip64=True) as archive:
    for item in items:
        info=zipfile.ZipInfo(item['name'],date_time=tuple(item['date_time']))
        for key in ('compress_type','create_system','create_version','extract_version','external_attr','internal_attr'):setattr(info,key,item[key])
        info.extra=bytes.fromhex(item['extra']);info.comment=bytes.fromhex(item['comment'])
        if 'text' in item:archive.writestr(info,item['text'].encode())
        else:
            with archive.open(info,'w') as out,item['path'].open('rb') as source:shutil.copyfileobj(source,out,1048576)
if digest(target)!=manifest['sha256']:raise ValueError('Reconstructed archive differs from independently verified local asset')
print('SOURCE_ARCHIVE_IDENTICAL',manifest['sha256'],flush=True)
if '--upload' in sys.argv:
    repo='chatgptopenaiagi/FB-MULTIENGINE-DOWNLOADER';tag='v0.2.0-alpha.1'
    release=json.loads(subprocess.check_output(['gh','release','view',tag,'--repo',repo,'--json','isDraft,assets']))
    if not release['isDraft']:raise RuntimeError('Only the existing draft may receive mirrored assets')
    lock=json.loads((root/'tools/native-windows.lock.json').read_text())
    native=output/'FBMD-0.2.0-alpha.1-native-windows-x64.zip'
    with requests.get(lock['url'],stream=True,timeout=(30,240)) as response:
        response.raise_for_status()
        with native.open('wb') as f:
            for chunk in response.iter_content(1048576):f.write(chunk)
    if digest(native)!=lock['sha256']:raise ValueError('Native mirror checksum mismatch')
    present={a['name'] for a in release['assets']}
    for path in (target,native):
        if path.name not in present:subprocess.run(['gh','release','upload',tag,'--repo',repo,str(path)],check=True)
    print('PINNED_MIRRORS_UPLOADED')
