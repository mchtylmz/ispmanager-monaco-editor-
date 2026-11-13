"""Package 0.3.0 around the immutable 0.2.5 editor payload; no frontend build."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.3.0'
PREVIOUS_SHA = 'd5ba2d595adf7eee1dd2a671ddeb10d0375f7cccb0c4328376ffb5c84785dcc5'


def main():
    old = ROOT / 'dist/ismonaco-editor-0.2.5.zip'
    if hashlib.sha256(old.read_bytes()).hexdigest() != PREVIOUS_SHA:
        raise SystemExit('Previous release identity mismatch')
    with zipfile.ZipFile(str(old)) as z:
        previous = z.read('manifest.json')
        payloads = {n: z.read(n) for n in z.namelist() if n.startswith('payload/')}
    changes = [
        ('integration/plugin/ispmgr_mod_ismonaco_preview.xml', 'etc/xml/ispmgr_mod_ismonaco_preview.xml', 0o644),
        ('integration/site-notice/site_notice.py', 'addon/ismonaco_site_notice_0_3_0.py', 0o640),
        ('integration/site-notice/site_notice.sh', 'addon/ismonaco_site_notice_0_3_0.sh', 0o750),
        ('integration/site-notice/defaults.json', 'etc/ismonaco-editor/site-notice-v1.json', 0o600),
    ]
    modes = {i['target']: i['mode'] for i in json.loads(previous)['files']}
    for source, target, mode in changes:
        payloads['payload/' + target] = (ROOT / source).read_bytes()
        modes[target] = mode
    entries = []
    for name, data in sorted(payloads.items()):
        target = name[len('payload/'):]
        item = dict(target=target, mode=modes[target], size=len(data), sha256=hashlib.sha256(data).hexdigest())
        if target in ('etc/ismonaco-editor/defaults-v2.json', 'etc/ismonaco-editor/site-notice-v1.json'):
            item['mutable'] = True
        entries.append(item)
    payloads['manifest.json'] = (json.dumps({'version': 1, 'files': entries}, indent=2) + '\n').encode()
    payloads['previous-manifest.json'] = previous
    for source, target in [('integration/plugin/install.py', 'install.py'), ('integration/plugin/update.py', 'update.py'),
                           ('docs/PLUGIN_0_3_0.md', 'README.md')]:
        payloads[target] = (ROOT / source).read_bytes()
    archive = ROOT / ('dist/ismonaco-plugin-' + VERSION + '.zip')
    with zipfile.ZipFile(str(archive), 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, (2026, 11, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.sha256').write_text(digest + '  ' + archive.name + '\n')
    print(digest + '  ' + str(archive))


if __name__ == '__main__':
    main()
