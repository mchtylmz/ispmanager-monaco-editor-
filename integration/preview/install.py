"""Install/verify/disable the read-only Monaco preview; never restart the panel."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import tempfile


ROOT = Path("/usr/local/mgr5")
XML = "etc/xml/ispmgr_mod_ismonaco_preview.xml"
ASSETS = "skins/ismonaco-preview-0.1.2/"
HANDLERS = {"addon/ismonaco_preview.py": 0o640, "addon/ismonaco_preview.sh": 0o750, XML: 0o644}


class InstallError(Exception):
    pass


def read_file(path, limit=10 * 1024 * 1024):
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise InstallError("NOT_REGULAR_FILE")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise InstallError("FILE_TOO_LARGE")
        return data
    finally:
        os.close(fd)


class Installer:
    def __init__(self, source, root=ROOT, owner_uid=0, owner_gid=0, anchor=Path("/")):
        # Alternate roots and owners are local-test dependencies only. CLI is fixed.
        self.source, self.root = Path(source), Path(root)
        self.uid, self.gid, self.anchor = owner_uid, owner_gid, Path(anchor)

    def payloads(self):
        try:
            manifest = json.loads(read_file(self.source / "manifest.json", 131072).decode("utf-8"))
            entries = manifest["files"]
            if manifest["version"] != 1 or not isinstance(entries, list) or not 4 <= len(entries) <= 256:
                raise ValueError()
            result, names, total = [], set(), 0
            for item in entries:
                name, mode = item["target"], item["mode"]
                if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_./-]+", name)
                        or name.startswith("/") or any(part in ("", ".", "..") for part in name.split("/"))
                        or name in names):
                    raise ValueError()
                if name in HANDLERS:
                    if mode != HANDLERS[name]:
                        raise ValueError()
                elif not name.startswith(ASSETS) or mode != 0o644:
                    raise ValueError()
                data = read_file(self.source / "payload" / name)
                digest = hashlib.sha256(data).hexdigest()
                if digest != item["sha256"] or len(data) != item["size"]:
                    raise InstallError("PAYLOAD_HASH_MISMATCH")
                names.add(name)
                total += len(data)
                result.append((name, mode, data))
            required = set(HANDLERS) | {ASSETS + name for name in (
                "app.js", "app.css", "frame.html", "editor.worker.js", "MONACO-LICENSE.txt", "ThirdPartyNotices.txt")}
            if not required.issubset(names) or total > 50 * 1024 * 1024:
                raise ValueError()
            compile(next(data for name, _, data in result if name.endswith("ismonaco_preview.py")),
                    "ismonaco_preview.py", "exec")
            return sorted(result, key=lambda entry: (entry[0] == XML, entry[0]))
        except (ValueError, KeyError, TypeError, SyntaxError, UnicodeError):
            raise InstallError("INVALID_MANIFEST_OR_RUNTIME") from None

    def trusted_parents(self, destination, allow_missing=False):
        current = Path(destination).parent
        while True:
            try:
                info = os.lstat(str(current))
            except FileNotFoundError:
                if not allow_missing:
                    raise InstallError("MISSING_DIRECTORY") from None
            else:
                if (not stat.S_ISDIR(info.st_mode) or info.st_uid != self.uid
                        or info.st_mode & 0o022):
                    raise InstallError("UNTRUSTED_DIRECTORY")
            if current == self.anchor:
                break
            if current.parent == current:
                raise InstallError("INVALID_ANCHOR")
            current = current.parent

    def preflight(self):
        payloads = self.payloads()
        # Native panel directories must already exist; no inferred installation root.
        for name in ("addon", "etc/xml", "skins"):
            self.trusted_parents(self.root / name / ".probe")
        if os.path.lexists(str(self.root / ASSETS.rstrip("/"))):
            raise InstallError("ASSET_DIRECTORY_EXISTS")
        for name, _, _ in payloads:
            target = self.root / name
            self.trusted_parents(target, allow_missing=True)
            if os.path.lexists(str(target)):
                raise InstallError("TARGET_EXISTS")
        if os.path.lexists(str(self.root / (XML + ".disabled"))):
            raise InstallError("DISABLED_INSTALL_EXISTS")
        return payloads

    def create_file(self, target, mode, data):
        self.trusted_parents(target)
        fd, temporary = tempfile.mkstemp(prefix=".ismonaco-preview-", dir=str(target.parent))
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                os.fchown(stream.fileno(), self.uid, self.gid)
                os.fchmod(stream.fileno(), mode)
                stream.flush()
                os.fsync(stream.fileno())
            # Existing destinations, including dangling symlinks, cannot be replaced.
            os.link(temporary, str(target), follow_symlinks=False)
        finally:
            os.unlink(temporary)

    def install(self):
        payloads = self.preflight()
        for name, mode, data in payloads:
            target = self.root / name
            if name.startswith(ASSETS):
                self.trusted_parents(target, allow_missing=True)
                target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                self.trusted_parents(target)
            self.create_file(target, mode, data)
        self.verify()

    def verify(self):
        for name, mode, data in self.payloads():
            target = self.root / name
            self.trusted_parents(target)
            info = os.lstat(str(target))
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != self.uid
                    or info.st_gid != self.gid or stat.S_IMODE(info.st_mode) != mode
                    or read_file(target) != data):
                raise InstallError("INSTALLED_FILE_MISMATCH")

    def disable(self):
        # Keep assets and handlers for inspection; never touch project/site files.
        self.verify()
        source, destination = self.root / XML, self.root / (XML + ".disabled")
        if os.path.lexists(str(destination)):
            raise InstallError("DISABLED_TARGET_EXISTS")
        os.link(str(source), str(destination), follow_symlinks=False)
        os.unlink(str(source))


def runtime_probe(source, executable="/usr/bin/python3"):
    # CLI uses the fixed Rocky system path. Tests inject their actual interpreter.
    environment = {"AUTH_USER": "preview-test", "AUTH_LEVEL": "16", "PARAM_func": "file.edit"}
    sample = (b'<doc func="file.edit"><metadata name="file.edit" type="form"><form>'
              b'<field name="fdata"><textarea name="fdata"/></field></form></metadata>'
              b'<fdata>&lt;?php echo 1;</fdata></doc>')
    result = subprocess.run(
        [executable, "-I", "-B", str(source / "payload/addon/ismonaco_preview.py")],
        input=sample, env=environment, cwd="/", stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5,
    )
    if result.returncode or result.stderr or b"<ismonaco_preview>" not in result.stdout:
        raise InstallError("RUNTIME_PROBE_FAILED")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for option in ("check", "install", "verify", "disable"):
        group.add_argument("--" + option, action="store_true")
    options = parser.parse_args()
    if platform.system() != "Linux" or os.geteuid() != 0:
        print("LINUX_ROOT_REQUIRED", file=sys.stderr)
        return 1
    source = Path(__file__).resolve().parent
    installer = Installer(source)
    try:
        if options.check or options.install:
            installer.preflight()
            runtime_probe(source)
            if options.install:
                installer.install()
            action = "INSTALL" if options.install else "CHECK"
        elif options.verify:
            installer.verify()
            action = "VERIFY"
        else:
            installer.disable()
            action = "DISABLE"
    except (InstallError, OSError, subprocess.SubprocessError) as error:
        print(str(error) if isinstance(error, InstallError) else "INSTALL_IO_ERROR", file=sys.stderr)
        return 1
    print("MONACO_PREVIEW_" + action + "_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
