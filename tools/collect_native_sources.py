"""Collect pinned native-library sources from upstream build recipes without executing them."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import tarfile
import requests

root=Path(__file__).resolve().parents[1]
dest=root/'.private/corresponding-sources/native-libraries'
dest.mkdir(parents=True,exist_ok=True)
items=[]
def expand(value,variables):
    for _ in range(8):
        old=value
        value=re.sub(r'\$\{(\w+)%\.\*\}',lambda m:variables.get(m[1],'').rsplit('.',1)[0],value)
        value=re.sub(r'\$\{(\w+)\}|\$(\w+)',lambda m:variables.get(m[1] or m[2],m[0]),value)
        if value==old:break
    return value
names={'libx264','libx265','xvidcore','libgnutls','libssh','libvidstab','rubberband','libsoxr','libmp3lame','libbluray','game-music-emu','fribidi','libgmp','libnettle','libunistring','libiconv'}
with tarfile.open(root/'.private/corresponding-sources/termux-packages-2ae8e839-source.tar.gz') as archive:
    for member in archive.getmembers():
        if not member.isfile() or not member.name.endswith('/build.sh') or member.name.split('/')[-2] not in names:continue
        name=member.name.split('/')[-2];body=archive.extractfile(member).read().decode();variables={}
        for line in body.splitlines():
            match=re.fullmatch(r'(\w+)=(.+)',line)
            if match:variables[match[1]]=expand(match[2].strip('"\''),variables)
        url=expand(variables.get('TERMUX_PKG_SRCURL',''),variables).replace('https://ftp.gnu.org/pub/gnu/','https://mirrors.kernel.org/gnu/')
        items.append({'component':'android-'+name,'url':url,'expected_sha256':variables.get('TERMUX_PKG_SHA256'),'recipe':member.name,'version':variables.get('TERMUX_PKG_VERSION')})
with tarfile.open(root/'.private/corresponding-sources/FFmpeg-Builds-7f2a6b1050d3-source.tar.gz') as archive:
    for member in archive.getmembers():
        if not member.isfile() or '/scripts.d/' not in member.name or not member.name.endswith('.sh'):continue
        body=archive.extractfile(member).read().decode();repo=re.search(r'^SCRIPT_REPO="(https://github.com/[^" ]+?)(?:\.git)?"',body,re.M);commit=re.search(r'^SCRIPT_COMMIT="([0-9a-f]{40})"',body,re.M)
        if repo and commit:
            items.append({'component':'windows-'+Path(member.name).stem,'url':'https://codeload.github.com/'+repo[1].split('github.com/')[1]+'/tar.gz/'+commit[1],'commit':commit[1],'recipe':member.name})
def fetch(item):
    item=dict(item);path=dest/(item['component']+'.source.tar')
    try:
        if '$' in item['url'] or not item['url'].startswith('https://'):raise ValueError('Recipe requires manual expansion')
        if not path.is_file():
            with requests.get(item['url'],stream=True,timeout=(20,120)) as response:
                response.raise_for_status()
                with path.with_suffix('.part').open('wb') as f:
                    for chunk in response.iter_content(1048576):f.write(chunk)
            path.with_suffix('.part').rename(path)
        with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        if item.get('expected_sha256') and item['expected_sha256']!=digest:raise ValueError('Recipe checksum mismatch')
        with tarfile.open(path) as archive:archive.getmembers()
        item.update(status='DOWNLOADED',file=path.name,sha256=digest,bytes=path.stat().st_size)
    except Exception as exc:item.update(status='SOURCE_URL_RETAINED',detail=type(exc).__name__)
    return item
with ThreadPoolExecutor(max_workers=6) as pool:records=list(pool.map(fetch,items))
(dest/'SOURCES.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in r.items() if k in ('component','status','detail')} for r in records],indent=2))
