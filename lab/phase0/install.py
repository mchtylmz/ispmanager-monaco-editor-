"""Install the three approved lab files. Never restart or overwrite targets."""

import argparse
import hashlib
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


TARGET_ROOT = Path("/usr/local/mgr5")
PAYLOADS = (
    ("ismonaco_phase0.py", "addon/ismonaco_phase0.py", 0o640,
     "4c544045467254a91776220551d8790807ac6a0fbd97858b60ce4fc337d173a7"),
    ("ismonaco_phase0.sh", "addon/ismonaco_phase0.sh", 0o750,
     "8a084ce1034ddd422e5e03dc251282033ece41287178488fc416b0fc1a540cd7"),
    ("ispmgr_mod_ismonaco_phase0.xml", "etc/xml/ispmgr_mod_ismonaco_phase0.xml", 0o644,
     "f3b82413e8a1876bfa71711f1a676ce5142091b5bc8636957ec4486ee7c7298a"),
)


class InstallError(Exception):
    pass


def read_payload(path):
    try:
        descriptor = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise InstallError("PAYLOAD_UNREADABLE") from None
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise InstallError("PAYLOAD_NOT_REGULAR")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(32769)
        if len(data) > 32768:
            raise InstallError("PAYLOAD_TOO_LARGE")
        return data
    finally:
        os.close(descriptor)


def probe_runtime(arguments):
    environment = {
        "PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C",
        "AUTH_USER": "root", "AUTH_LEVEL": "30", "PARAM_func": "ismonaco.phase0",
    }
    try:
        result = subprocess.run(
            arguments, env=environment, cwd="/", stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5,
        )
        if result.returncode != 0 or result.stderr:
            raise InstallError("RUNTIME_TEST_FAILED")
        document = ET.fromstring(result.stdout)
        if (document.tag != "doc" or document.find("error") is not None
                or document.find("metadata/form") is None):
            raise InstallError("RUNTIME_TEST_FAILED")
    except (OSError, subprocess.TimeoutExpired, ET.ParseError):
        raise InstallError("RUNTIME_TEST_FAILED") from None


class Installer:
    def __init__(self, source, root=TARGET_ROOT, owner_uid=0, owner_gid=0,
                 trust_anchor=Path("/"), runner=probe_runtime):
        # Alternate roots/owners/runner are used only by local tests. The CLI
        # below always uses the fixed production paths and root ownership.
        self.source = Path(source)
        self.root = Path(root)
        self.owner_uid = owner_uid
        self.owner_gid = owner_gid
        self.trust_anchor = Path(trust_anchor)
        self.runner = runner

    def payloads(self):
        result = []
        for name, relative, mode, digest in PAYLOADS:
            data = read_payload(self.source / name)
            if hashlib.sha256(data).hexdigest() != digest:
                raise InstallError("PAYLOAD_HASH_MISMATCH")
            result.append((self.root / relative, mode, digest, data))
        return result

    def check_directories(self):
        parents = {self.root, self.root / "addon", self.root / "etc", self.root / "etc/xml"}
        current = self.root
        while current != self.trust_anchor:
            if current.parent == current:
                raise InstallError("INVALID_TRUST_ANCHOR")
            current = current.parent
            parents.add(current)
        for path in parents:
            try:
                metadata = os.lstat(str(path))
            except OSError:
                raise InstallError("INVALID_TARGET_DIRECTORY") from None
            if (not stat.S_ISDIR(metadata.st_mode)
                    or metadata.st_uid not in (0, self.owner_uid)
                    or metadata.st_mode & 0o022):
                raise InstallError("UNTRUSTED_TARGET_DIRECTORY")

    def atomic_create(self, destination, data, mode):
        descriptor, temporary = tempfile.mkstemp(prefix=".ismonaco-phase0-", dir=str(destination.parent))
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                os.fchown(stream.fileno(), self.owner_uid, self.owner_gid)
                os.fchmod(stream.fileno(), mode)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                # Same-directory hard link is atomic and refuses any existing
                # destination, including a dangling symlink or directory.
                os.link(temporary, str(destination), follow_symlinks=False)
            except FileExistsError:
                raise InstallError("TARGET_EXISTS") from None
        finally:
            os.unlink(temporary)  # Only this invocation's private staging file.

    def install(self):
        payloads = self.payloads()
        self.check_directories()
        if any(os.path.lexists(str(destination)) for destination, _, _, _ in payloads):
            raise InstallError("TARGET_EXISTS")
        # Verify the observed server Python before publishing any target.
        self.runner(["/usr/bin/python3", "-I", "-B", str(self.source / PAYLOADS[0][0])])
        for index, (destination, mode, _, data) in enumerate(payloads):
            if index == 2:
                # XML registration is last, after installed wrapper validation.
                self.runner([str(self.root / "addon/ismonaco_phase0.sh")])
            self.atomic_create(destination, data, mode)
        self.verify()

    def verify(self):
        payloads = self.payloads()
        self.check_directories()
        for destination, mode, digest, _ in payloads:
            try:
                metadata = os.lstat(str(destination))
            except OSError:
                raise InstallError("TARGET_MISSING") from None
            if (not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_uid != self.owner_uid or metadata.st_gid != self.owner_gid
                    or stat.S_IMODE(metadata.st_mode) != mode):
                raise InstallError("TARGET_METADATA_MISMATCH")
            if hashlib.sha256(read_payload(destination)).hexdigest() != digest:
                raise InstallError("TARGET_HASH_MISMATCH")
        self.runner([str(self.root / "addon/ismonaco_phase0.sh")])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Verify only; do not install or restart")
    options = parser.parse_args(argv)
    if platform.system() != "Linux" or os.geteuid() != 0:
        print("LINUX_ROOT_REQUIRED", file=sys.stderr)
        return 1
    installer = Installer(Path(__file__).resolve().parent)
    try:
        if options.verify:
            installer.verify()
        else:
            installer.install()
    except InstallError as error:
        print(str(error), file=sys.stderr)
        return 1
    except OSError:
        print("INSTALL_OS_ERROR", file=sys.stderr)
        return 1
    print("PHASE0_VERIFY_OK" if options.verify else "PHASE0_INSTALL_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
