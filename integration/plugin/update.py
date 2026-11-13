"""Guarded 0.2.5 -> 0.3.0 registration switch. Never restart or modify site/core files."""

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
PREVIOUS_HASH = 'd9cfc0dd40a93c977994299c9f0abcf0605c6adc66bb079918fb0358fc5b60fe'
OLD_CONFIG = installer.CONFIG
REGISTRATION = installer.XML
BACKUP = REGISTRATION + '.pre-0.3.0'


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
        if digest is not None and hashlib.sha256(data).hexdigest() != digest:
            raise InstallError('PREVIOUS_FILE_HASH_MISMATCH')
        return data

    def verify_previous(self):
        result = {}
        for item in self.previous():
            name = item['target']
            data = self.checked_file(name, item['mode'], None if name == OLD_CONFIG else item['sha256'])
            if name == OLD_CONFIG:
                installer.validate_config(data)
            result[name] = data
        return result

    def check(self):
        payloads = self.payloads()
        old = self.verify_previous()
        if os.path.lexists(str(self.root / BACKUP)):
            raise InstallError('BACKUP_EXISTS')
        for name, mode, data in payloads:
            if name not in (REGISTRATION, installer.CONFIG):
                self.trusted_parents(self.root / name, allow_missing=True)
                if name in old:
                    if data != old[name]:
                        raise InstallError('REUSED_PAYLOAD_MISMATCH')
                elif os.path.lexists(str(self.root / name)):
                    raise InstallError('NEW_TARGET_EXISTS')
        return payloads, old

    def replace_registration(self, data, expected):
        destination = self.root / REGISTRATION
        digest = hashlib.sha256(expected).hexdigest()
        self.checked_file(REGISTRATION, 0o644, digest)
        fd, temporary = tempfile.mkstemp(prefix='.ismonaco-update-', dir=str(destination.parent))
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                os.fchown(stream.fileno(), self.uid, self.gid)
                os.fchmod(stream.fileno(), 0o644)
                stream.flush()
                os.fsync(stream.fileno())
            self.checked_file(REGISTRATION, 0o644, digest)
            os.replace(temporary, str(destination))
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)  # Only this invocation's private staging file.

    def apply(self, runner=None):
        payloads, old = self.check()
        if runner:
            runner(self.source)
        for name, mode, data in payloads:
            if name not in old:
                path = self.root / name
                path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                self.create_file(path, mode, data)
                self.checked_file(name, mode, hashlib.sha256(data).hexdigest())
        # New handlers/assets exist before switching XML; mutable settings are untouched.
        self.checked_file(REGISTRATION, 0o644, hashlib.sha256(old[REGISTRATION]).hexdigest())
        self.create_file(self.root / BACKUP, 0o644, old[REGISTRATION])
        new = next(data for name, _, data in payloads if name == REGISTRATION)
        self.replace_registration(new, old[REGISTRATION])
        self.verify()

    def rollback(self):
        self.verify()
        original = next(item for item in self.previous() if item['target'] == REGISTRATION)
        backup = self.checked_file(BACKUP, 0o644, original['sha256'])
        new = next(data for name, _, data in self.payloads() if name == REGISTRATION)
        self.replace_registration(backup, new)
        self.verify_previous()
        # Both versions, global preferences and independent XML backup are preserved.


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
    print('MONACO_EDITOR_UPDATE_' + action + '_OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
