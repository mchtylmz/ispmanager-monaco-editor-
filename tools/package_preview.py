"""Build an immutable preview ZIP from the already built local frontend."""

import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / "package.json").read_text())["version"]
FILES = [
    ("integration/preview/ismonaco_preview.py", "addon/ismonaco_preview.py", 0o640),
    ("integration/preview/ismonaco_preview.sh", "addon/ismonaco_preview.sh", 0o750),
    ("integration/preview/ispmgr_mod_ismonaco_preview.xml", "etc/xml/ispmgr_mod_ismonaco_preview.xml", 0o644),
]


def main():
    frontend = ROOT / "dist/frontend"
    for name in ("app.js", "app.css", "frame.html", "editor.worker.js", "MONACO-LICENSE.txt", "ThirdPartyNotices.txt"):
        if not (frontend / name).is_file():
            raise SystemExit("Run npm run build first")
    assets = [(str(path.relative_to(ROOT)), "skins/ismonaco-preview-0.1.2/" + path.relative_to(frontend).as_posix(), 0o644)
              for path in sorted(frontend.rglob("*")) if path.is_file()]
    entries, payloads = [], {}
    for source, target, mode in FILES + assets:
        data = (ROOT / source).read_bytes()
        entries.append({"target": target, "mode": mode, "size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest()})
        payloads["payload/" + target] = data
    payloads["manifest.json"] = (json.dumps({"version": 1, "files": entries}, indent=2) + "\n").encode()
    previous = ROOT / 'dist/ismonaco-preview-0.1.1.zip'
    if hashlib.sha256(previous.read_bytes()).hexdigest() != '0f1e8e8da171cf92d50c34963dfccc33e35ae90303b0d09152375cadd98bc233':
        raise SystemExit('Previous release identity mismatch')
    with zipfile.ZipFile(str(previous)) as release:
        payloads['previous-manifest.json'] = release.read('manifest.json')
    for source, target in (("integration/preview/install.py", "install.py"),
                           ("integration/preview/update.py", "update.py"),
                           ("docs/MONACO_ONIZLEME_KURULUM.md", "README.md")):
        payloads[target] = (ROOT / source).read_bytes()
    archive = ROOT / "dist" / ("ismonaco-preview-" + VERSION + ".zip")
    with zipfile.ZipFile(str(archive), "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, (2026, 11, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".sha256").write_text(digest + "  " + archive.name + "\n")
    print(digest + "  " + str(archive))


if __name__ == "__main__":
    main()
