import json, os, subprocess, sys, zipfile
from pathlib import Path

assert Path('/.dockerenv').is_file()
scenario=sys.argv[1]
root=Path('/usr/local/mgr5'); project=Path('/workspace')
package=project/'dist/ismonaco-setup-0.3.1.pyz'
for name in ('addon','etc/xml','skins','sbin','var'): (root/name).mkdir(parents=True,exist_ok=True)
if not Path('/usr/bin/python3').exists(): os.symlink(sys.executable,'/usr/bin/python3')
manager=root/'sbin/mgrctl'
manager.write_text('#!/bin/sh\n[ "$#" -eq 3 ] && [ "$1" = "-m" ] && [ "$2" = "ispmgr" ] && [ "$3" = "exit" ] || exit 9\nif [ -f /tmp/fail-restart ]; then echo PRIVATE_NATIVE_OUTPUT >&2; exit 7; fi\nprintf "reload\\n" >> /tmp/panel-restarts\n')
manager.chmod(0o750)
def invoke(*args, expected=0, archive=package):
 r=subprocess.run([sys.executable,'-I','-B',str(archive)]+list(args),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
 assert r.returncode==expected,(r.returncode,r.stdout,r.stderr)
 if not expected: assert not r.stderr,r.stderr
 assert b'PRIVATE_NATIVE_OUTPUT' not in r.stderr+r.stdout
 assert not list(Path('/tmp').glob('ismonaco-setup-*'))
 print((r.stdout+r.stderr).decode().strip(),flush=True)
 return r.stdout+r.stderr
def count():
 p=Path('/tmp/panel-restarts'); return len(p.read_text().splitlines()) if p.exists() else 0
def identity(p): return p.read_bytes(),p.stat().st_ino,p.stat().st_mtime_ns
def snapshot(): return {p.relative_to(root).as_posix():identity(p) for p in root.rglob('*') if p.is_file()}
config=root/'etc/ismonaco-editor/defaults-v2.json'
old=Path('/tmp/old-stage')
if scenario=='update':
 with zipfile.ZipFile(str(project/'dist/ismonaco-editor-0.2.5.zip')) as z: z.extractall(str(old))
 r=subprocess.run([sys.executable,'-I','-B',str(old/'install.py'),'--install'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
 assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)
 value=json.loads(config.read_text());value.update(theme='light',fontSize=16,height=900)
 config.write_text(json.dumps(value));old_identity=identity(config)
 expected_mode=b'UPDATE_0_2_5'
else: expected_mode=b'NEW_INSTALL'
before=snapshot();assert expected_mode in invoke('check'); assert snapshot()==before and count()==0
if scenario=='update':
 assert b'RESTART_PENDING' in invoke('install','--no-restart')
 assert identity(config)==old_identity and count()==0
 invoke('restart')
else: assert expected_mode in invoke()  # The exact one-command path, no action flag.
assert count()==1
# Save through the actual installed settings wrapper, not direct preference replacement.
values=dict(AUTH_USER='root',AUTH_LEVEL='30',PARAM_func='ismonaco.settings',PARAM_lang='tr',PARAM_sok='ok',PARAM_theme='light',PARAM_font_size='16',PARAM_height='900',PARAM_wrap='on',PARAM_minimap='on',PARAM_fullscreen='on',PARAM_site_notice_style='warning',PARAM_site_notice_text='IP A: Web\nIP B: Mail')
r=subprocess.run([str(root/'addon/ismonaco_site_notice_0_3_0.sh')],env=values,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
assert r.returncode==0 and not r.stderr and b'<error' not in r.stdout,(r.stdout,r.stderr)
note=root/'etc/ismonaco-editor/site-notice-v1.json';assert json.loads(note.read_text())['text']==values['PARAM_site_notice_text']
before=snapshot(); assert b'ALREADY_CURRENT' in invoke();assert snapshot()==before and count()==1
invoke('verify')
# A failed reload is reported separately after a verified install, without changing settings.
Path('/tmp/fail-restart').touch();response=invoke('restart',expected=2)
assert b'ERROR=RESTART_REQUIRED' in response and snapshot()==before
Path('/tmp/fail-restart').unlink();invoke('restart');assert count()==2
# Alter only the embedded ZIP in a disposable copy: no staged/helper code is executed.
tampered=Path('/tmp/tampered.pyz')
with zipfile.ZipFile(str(package)) as source, zipfile.ZipFile(str(tampered),'w') as target:
 for name in source.namelist():
  data=source.read(name)
  target.writestr(name,data+b'x' if name=='bundle.zip' else data)
assert b'BUNDLE_INTEGRITY_FAILED' in invoke(expected=1,archive=tampered)
assert snapshot()==before and count()==2
# An altered installed handler is rejected rather than reset or overwritten.
handler=root/'addon/ismonaco_0_2_5.py';original=handler.read_bytes();handler.write_bytes(original+b'\n# external change\n')
modified=snapshot();assert b'UNSUPPORTED_OR_MODIFIED_INSTALLATION' in invoke(expected=1)
assert snapshot()==modified and count()==2
handler.write_bytes(original)
if scenario=='update':
 keep=identity(config),identity(note)
 invoke('rollback','--no-restart')
 assert (identity(config),identity(note))==keep
 r=subprocess.run([sys.executable,'-I','-B',str(old/'install.py'),'--verify'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
 assert r.returncode==0 and not r.stderr
else: assert b'NO_UPGRADE_BACKUP' in invoke('rollback',expected=1)
print('SINGLE_FILE_CLI_OK '+scenario+': check/apply/verify; automatic/pending reload; current idempotence; both settings preserved; corrupt bundle/modified handler refused; staging cleaned',flush=True)
