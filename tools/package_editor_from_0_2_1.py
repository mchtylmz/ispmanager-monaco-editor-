"""Package a direct 0.2.1 upgrade using the immutable, fixed 0.2.3 payload."""
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RELEASES = {
    'ismonaco-editor-0.2.1.zip': '922326c9999b530cf7e0b15a2748dd2500ba067e40addac864a7614f097dc7a0',
    'ismonaco-editor-0.2.3.zip': '33eca6e919f7e4a0815ff698a42fe4687d95ce552652cdcf3cde38916a7d3b62',
}

def main():
    for name, digest in RELEASES.items():
        if hashlib.sha256((ROOT/'dist'/name).read_bytes()).hexdigest() != digest:
            raise SystemExit('RELEASE_IDENTITY_MISMATCH: ' + name)
    with zipfile.ZipFile(str(ROOT/'dist/ismonaco-editor-0.2.3.zip')) as source:
        entries = {name: source.read(name) for name in source.namelist()}
    with zipfile.ZipFile(str(ROOT/'dist/ismonaco-editor-0.2.1.zip')) as base:
        entries['previous-manifest.json'] = base.read('manifest.json')
    entries['update.py'] = (ROOT/'integration/editor/update_from_0_2_1.py').read_bytes()
    entries['README.md'] = (ROOT/'docs/EDITOR_0_2_3_FROM_0_2_1.md').read_bytes()
    output = ROOT/'dist/ismonaco-editor-0.2.3-from-0.2.1.zip'
    with zipfile.ZipFile(str(output), 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in sorted(entries.items()):
            item=zipfile.ZipInfo(name,(2026,11,9,0,0,0)); item.compress_type=zipfile.ZIP_DEFLATED
            item.external_attr=0o100644 << 16; bundle.writestr(item,data)
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.sha256').write_text(digest+'  '+output.name+'\n')
    print(digest+'  '+str(output))

if __name__ == '__main__': main()
