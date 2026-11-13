"""Build one offline Python zipapp from the immutable, tested 0.3.0 release."""
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_SHA256 = 'fe3c2fafcc986c64b2dde6d8cb1149a443fc8ad2ae48120888b3554b7a1762b3'


def main():
    data = (ROOT / 'dist/ismonaco-plugin-0.3.0.zip').read_bytes()
    if hashlib.sha256(data).hexdigest() != BUNDLE_SHA256:
        raise SystemExit('Released 0.3.0 identity mismatch')
    launcher = (ROOT / 'integration/standalone/launcher.py').read_bytes()
    compile(launcher, '__main__.py', 'exec')
    archive = ROOT / 'dist/ismonaco-setup-0.3.1.pyz'
    with zipfile.ZipFile(str(archive), 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as app:
        for name, content in [('__main__.py', launcher), ('bundle.zip', data),
                              ('README.md', (ROOT / 'docs/TEK_DOSYA_KURULUM.md').read_bytes())]:
            info = zipfile.ZipInfo(name, (2026, 11, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            app.writestr(info, content)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.sha256').write_text(digest + '  ' + archive.name + '\n')
    print(digest + '  ' + str(archive))


if __name__ == '__main__':
    main()
