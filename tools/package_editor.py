"""Package the editor release; preserve all previously distributed archives."""

import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.2.5'
FILES = [
    ('integration/editor/ismonaco_editor.py', 'addon/ismonaco_0_2_5.py', 0o640),
    ('integration/editor/ismonaco_editor.sh', 'addon/ismonaco_0_2_5.sh', 0o750),
    ('integration/editor/ispmgr_mod_ismonaco_preview.xml', 'etc/xml/ispmgr_mod_ismonaco_preview.xml', 0o644),
    ('integration/editor/defaults.json', 'etc/ismonaco-editor/defaults-v2.json', 0o600),
]


def main():
    frontend = ROOT / 'dist/frontend'
    for name in ('app.js', 'app.css', 'frame.html', 'editor.worker.js', 'MONACO-LICENSE.txt', 'ThirdPartyNotices.txt'):
        if not (frontend / name).is_file():
            raise SystemExit('Run npm run build first')
    assets = [(str(path.relative_to(ROOT)), 'skins/ismonaco-editor-' + VERSION + '/' + path.relative_to(frontend).as_posix(), 0o644)
              for path in sorted(frontend.rglob('*')) if path.is_file()]
    entries, payloads = [], {}
    for source, target, mode in FILES + assets:
        data = (ROOT / source).read_bytes()
        entry = {'target': target, 'mode': mode, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        if target == 'etc/ismonaco-editor/defaults-v2.json':
            entry['mutable'] = True
        entries.append(entry)
        payloads['payload/' + target] = data
    payloads['manifest.json'] = (json.dumps({'version': 1, 'files': entries}, indent=2) + '\n').encode()
    previous = ROOT / 'dist/ismonaco-editor-0.2.4.zip'
    if hashlib.sha256(previous.read_bytes()).hexdigest() != 'dd30a7247c659897208b5f26bf3dd590e7d654a24d68f48594f8453f8781f424':
        raise SystemExit('Previous release identity mismatch')
    with zipfile.ZipFile(str(previous)) as release:
        payloads['previous-manifest.json'] = release.read('manifest.json')
    for source, target in (('integration/editor/install.py', 'install.py'), ('integration/editor/update.py', 'update.py'),
                           ('docs/EDITOR_0_2_5.md', 'README.md')):
        payloads[target] = (ROOT / source).read_bytes()
    archive = ROOT / 'dist' / ('ismonaco-editor-' + VERSION + '.zip')
    with zipfile.ZipFile(str(archive), 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, (2026, 11, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.sha256').write_text(digest + '  ' + archive.name + '\n')
    print(digest + '  ' + str(archive))


if __name__ == '__main__':
    main()
