"""Keep only FFmpeg's required ELF dependency closure; no unused desktop-capture/plugin binaries."""
import hashlib
import io
import json
from pathlib import Path
import zipfile
import posixpath
from elftools.elf.elffile import ELFFile
import requests

root=Path(__file__).resolve().parents[1]
cache=root/'.toolchain/downloads';cache.mkdir(parents=True,exist_ok=True)
archives={}
expected={'library':'579b5fb480892b1abc2b218c2089699d52759cc8d7ba256bf876453f0365faef','ffmpeg':'0a87ffa6cf912b0fe76c1a99b9107f543ee2f247935fae2c71f0822eb7bc5f49'}
for component in ('library','ffmpeg'):
    existing=list((root/'.toolchain/gradle-home').rglob(component+'-0.18.1.aar'))
    path=existing[0] if existing else cache/(component+'-0.18.1.aar')
    if not path.exists():
        url=f'https://repo.maven.apache.org/maven2/io/github/junkfood02/youtubedl-android/{component}/0.18.1/{component}-0.18.1.aar'
        with requests.get(url,stream=True,timeout=180) as response:
            response.raise_for_status()
            with path.open('wb') as f:
                for chunk in response.iter_content(1048576):f.write(chunk)
    with path.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=expected[component]:raise RuntimeError('Upstream AAR checksum mismatch: '+component)
    archives[component]=zipfile.ZipFile(path)
dest=root/'.toolchain/android-assets/native';dest.mkdir(parents=True,exist_ok=True)
system={'libc.so','libm.so','libdl.so','liblog.so','libandroid.so','libz.so','libstdc++.so','libOpenSLES.so','libmediandk.so','libjnigraphics.so','libEGL.so','libGLESv2.so','libvulkan.so'}
def needed(data):
    if not data.startswith(b'\x7fELF'):return []
    dynamic=ELFFile(io.BytesIO(data)).get_section_by_name('.dynamic')
    return [tag.needed for tag in dynamic.iter_tags() if tag.entry.d_tag=='DT_NEEDED'] if dynamic else []
def resolve(archive,name,depth=0):
    if depth>12:raise RuntimeError('Native link cycle')
    data=archive.read(name)
    if data.startswith(b'\x7fELF'):return data
    if len(data)>300:raise RuntimeError('Expected ELF or native symlink')
    target=posixpath.normpath(posixpath.join(posixpath.dirname(name),data.decode()))
    if not target.startswith('usr/lib/'):raise RuntimeError('Unsafe native symlink')
    return resolve(archive,target,depth+1)
report=[]
for abi in ('arm64-v8a','x86_64'):
    ff=zipfile.ZipFile(io.BytesIO(archives['ffmpeg'].read(f'jni/{abi}/libffmpeg.zip.so')))
    py=zipfile.ZipFile(io.BytesIO(archives['library'].read(f'jni/{abi}/libpython.zip.so')))
    ff_entries={Path(n).name:n for n in ff.namelist() if not n.endswith('/') and n.startswith('usr/lib/') and n.count('/')==2}
    py_entries={Path(n).name:n for n in py.namelist() if not n.endswith('/') and n.startswith('usr/lib/') and n.count('/')==2}
    pending=[]
    for name in ('libffmpeg.so','libffprobe.so'):pending.extend(needed(archives['ffmpeg'].read(f'jni/{abi}/{name}')))
    retained=set();visited=set()
    while pending:
        name=pending.pop()
        if name in visited:continue
        visited.add(name)
        if name in ff_entries:
            retained.add(ff_entries[name]);pending.extend(needed(resolve(ff,ff_entries[name])))
        elif name in py_entries:
            pending.extend(needed(resolve(py,py_entries[name])))
        elif name not in system:raise RuntimeError(f'Missing required native dependency for {abi}: {name}')
    target=dest/f'ffmpeg-{abi}.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as output:
        for name in sorted(retained):
            info=zipfile.ZipInfo(name,date_time=(2026,11,20,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            output.writestr(info,resolve(ff,name))
    report.append({'abi':abi,'retained_libraries':len(retained),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'paths':sorted(retained)})
    ff.close();py.close()
for archive in archives.values():archive.close()
(dest/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(root/'evidence/android-runtime-pruning.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in r.items() if k!='paths'} for r in report],indent=2))
