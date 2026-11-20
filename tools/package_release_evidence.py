"""Assemble evidence/source assets only after platform acceptance has passed."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

root=Path(__file__).resolve().parents[1];release=root/'dist/release';tag='v0.2.0-alpha.1'
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()
def read(name):return json.loads((root/'evidence'/name).read_text(encoding='utf-8-sig'))
for name in ('portable-isolation.json','portable-archive-verification.json','installer-verification.json','android-native-dependencies.json','public-scan.json'):
    assert read(name)['status']=='PASS',name
assert read('android-release-native.json')['status']=='READY'
assert not read('windows-native-dependencies.json')['errors']
assert read('wheel-verification.json')['record']['status']=='complete'
for filename,report,key in [('FBMD-0.2.0-alpha.1-windows-x64.zip','portable-archive-verification.json','sha256'),('FBMD-0.2.0-alpha.1-windows-x64-setup.exe','installer-verification.json','installer_sha256'),('FBMD-0.2.0-alpha.1-android-arm64-x86_64.apk','android-release-native.json','release_apk_sha256')]:
    with (release/filename).open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
    evidence=read(report);expected=evidence[key]
    assert actual==expected,filename
evidence_file=release/'FBMD-0.2.0-alpha.1-evidence.zip'
with zipfile.ZipFile(evidence_file,'x',compression=zipfile.ZIP_DEFLATED) as archive:
    for folder in ('evidence','docs','contracts'):
        for path in sorted((root/folder).rglob('*')):
            if path.is_file():archive.write(path,path.relative_to(root).as_posix())
application=root/'.private/release-application-source.zip'
subprocess.run(['git','archive','--format=zip','--prefix=application/','--output='+str(application),commit],cwd=root,check=True)
sources=release/'FBMD-0.2.0-alpha.1-sources.zip'
upstream=root/'.private/corresponding-sources'
with zipfile.ZipFile(sources,'x',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
    archive.write(application,'application-'+commit+'.zip')
    for path in sorted(upstream.rglob('*')):
        if path.is_file() and path.suffix!='.part':archive.write(path,'upstream/'+path.relative_to(upstream).as_posix())
    archive.writestr('README.txt','Application source commit: '+commit+'\nSee application/docs/BUILD.md for application builds and upstream FFmpeg-Builds/Termux/youtubedl-android build recipes for native libraries. Original upstream native binaries were not rebuilt in this mission. Archive manifests retain exact fetched source URLs/hashes. The Termux recipe snapshot was selected from upstream runtime dates; upstream does not provide a complete native build lockfile. Do not infer byte-identical native reproducibility. No private state, media or signing keys are included.\n')
checks={name:'PASS' for name in ('windows_packaged_ui','windows_native_merge','windows_installer','wheel_installed','android_release_local_download','android_native_merge','portable_archive','public_secret_scan')}
report={'release_tag':tag,'source_commit':commit,'status':'VERIFIED_PARTIAL','checks':checks,'test_scope':'Windows x64 portable and installer; installed Python 3.11 wheel; signed Android release on x86_64 Android 11 emulator. ARM64 static inspection only.','limitations':['Physical ARM64 execution not available','Some Android ELF segments have less than 16 KB alignment','Authenticated Meta Graph/OAuth unverified; OAuth not implemented','Long-video extraction regression sources failed ordinary unauthenticated access','Bounded discovery does not establish complete coverage','Windows binaries unsigned'],'artifacts':[]}
for path in sorted(release.iterdir()):
    if path.name in ('verification.json','SHA256SUMS.txt'):continue
    with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    report['artifacts'].append({'file':path.name,'bytes':path.stat().st_size,'sha256':digest})
(release/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
lines=[]
for path in sorted(release.iterdir()):
    if path.name=='SHA256SUMS.txt':continue
    with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    lines.append(digest+'  '+path.name)
(release/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
