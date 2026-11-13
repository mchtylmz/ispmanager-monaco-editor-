"""Guarded 0.1.1 -> 0.1.2 update. Never restart or modify site/core files."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import tempfile


SOURCE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('ismonaco_local_installer', str(SOURCE / 'install.py'))
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)
InstallError = installer.InstallError
PREVIOUS_HASH = '5b4331b28cea86702ecb40b4c83562704368153dac698b2f7953e2ddd9355ac1'
MAIN = 'addon/ismonaco_preview.py'
BACKUP = MAIN + '.pre-0.1.2'


class Updater(installer.Installer):
    def previous(self):
        data = installer.read_file(self.source / 'previous-manifest.json', 131072)
        if hashlib.sha256(data).hexdigest() != PREVIOUS_HASH:
            raise InstallError('PREVIOUS_MANIFEST_MISMATCH')
        return json.loads(data.decode('utf-8'))['files']

    def checked_file(self, name, mode, digest):
        path = self.root / name
        self.trusted_parents(path)
        info = os.lstat(str(path))
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != self.uid or info.st_gid != self.gid
                or stat.S_IMODE(info.st_mode) != mode):
            raise InstallError('PREVIOUS_FILE_METADATA_MISMATCH')
        data = installer.read_file(path)
        if hashlib.sha256(data).hexdigest() != digest:
            raise InstallError('PREVIOUS_FILE_HASH_MISMATCH')
        return data

    def verify_previous(self):
        return {item['target']: self.checked_file(item['target'], item['mode'], item['sha256'])
                for item in self.previous()}

    def check(self):
        payloads = self.payloads()
        old = self.verify_previous()
        if os.path.lexists(str(self.root / BACKUP)):
            raise InstallError('BACKUP_EXISTS')
        if os.path.lexists(str(self.root / installer.ASSETS.rstrip('/'))):
            raise InstallError('NEW_ASSET_DIRECTORY_EXISTS')
        for name, mode, data in payloads:
            if name.startswith(installer.ASSETS):
                self.trusted_parents(self.root / name, allow_missing=True)
                if os.path.lexists(str(self.root / name)):
                    raise InstallError('NEW_ASSET_EXISTS')
            elif name != MAIN and (name not in old or data != old[name]):
                raise InstallError('REGISTRATION_CHANGE_NOT_SUPPORTED')
        return payloads, old

    def replace_main(self, data, expected):
        destination = self.root / MAIN
        digest = hashlib.sha256(expected).hexdigest()
        self.checked_file(MAIN, 0o640, digest)
        fd, temporary = tempfile.mkstemp(prefix='.ismonaco-update-', dir=str(destination.parent))
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                os.fchown(stream.fileno(), self.uid, self.gid)
                os.fchmod(stream.fileno(), 0o640)
                stream.flush()
                os.fsync(stream.fileno())
            self.checked_file(MAIN, 0o640, digest)
            os.replace(temporary, str(destination))
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)  # Only this invocation's private staging file.

    def apply(self, runner=None):
        payloads, old = self.check()
        if runner:
            runner(self.source)
        for name, mode, data in payloads:
            if name.startswith(installer.ASSETS):
                path = self.root / name
                path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                self.create_file(path, mode, data)
                self.checked_file(name, mode, hashlib.sha256(data).hexdigest())
        # All new assets exist before the one live handler is atomically replaced.
        self.checked_file(MAIN, 0o640, hashlib.sha256(old[MAIN]).hexdigest())
        self.create_file(self.root / BACKUP, 0o640, old[MAIN])
        new = next(data for name, _, data in payloads if name == MAIN)
        self.replace_main(new, old[MAIN])
        self.verify()

    def rollback(self):
        self.verify()
        original = next(item for item in self.previous() if item['target'] == MAIN)
        backup = self.checked_file(BACKUP, 0o640, original['sha256'])
        new = next(data for name, _, data in self.payloads() if name == MAIN)
        self.replace_main(backup, new)
        self.verify_previous()
        # Both asset directories and the independent backup are preserved.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for name in ('check', 'apply', 'rollback'):
        group.add_argument('--' + name, action='store_true')
    options = parser.parse_args()
    if platform.system() != 'Linux' or os.geteuid() != 0:
        print('LINUX_ROOT_REQUIRED', file=sys.stderr)
        return 1
    updater = Updater(SOURCE)
    try:
        if options.check:
            updater.check()
            installer.runtime_probe(SOURCE)
            action = 'CHECK'
        elif options.apply:
            updater.apply(runner=installer.runtime_probe)
            action = 'APPLY'
        else:
            updater.rollback()
            action = 'ROLLBACK'
    except (InstallError, OSError, subprocess.SubprocessError) as error:
        print(str(error) if isinstance(error, InstallError) else 'UPDATE_IO_ERROR', file=sys.stderr)
        return 1
    print('MONACO_PREVIEW_UPDATE_' + action + '_OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
