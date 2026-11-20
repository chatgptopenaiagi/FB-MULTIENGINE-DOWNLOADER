"""Scan staged public files for secret signatures and known saved-session values without printing secrets."""
import json
from pathlib import Path
import re
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
from fbmd.security import Vault

names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
patterns=[rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{40,}',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'xox[baprs]-[A-Za-z0-9-]{20,}']
values=[]
state=Path('F:/AILAB/FB-MULTIENGINE-DOWNLOADER/verification-20261120/desktop-state/vault')
if state.is_dir():
    try:
        browser=Vault(state).get('browser',{})
        values=[c['value'].encode() for c in browser.get('cookies',[]) if len(c.get('value',''))>=20]
    except Exception as e:raise RuntimeError('Cannot verify known session exclusion') from e
errors=[]
for name in names:
    if not name:continue
    path=root/name
    if path.suffix.lower() in ('.jks','.keystore','.enc','.sqlite','.sqlite3','.db','.dpapi') or any(p in path.parts for p in ('.private','.toolchain','.venv')):errors.append({'file':name,'reason':'forbidden private artifact'})
    data=path.read_bytes()
    if any(re.search(p,data) for p in patterns) or any(value in data for value in values):errors.append({'file':name,'reason':'secret signature or saved-session match'})
result={'status':'PASS' if not errors else 'FAIL','tracked_files':len([n for n in names if n]),'known_session_values_checked':len(values),'errors':errors,'scope':'Tracked bytes and known saved-session values; screenshots additionally reviewed visually. No secret values are printed.'}
(root/'evidence/public-scan.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
raise SystemExit(bool(errors))
