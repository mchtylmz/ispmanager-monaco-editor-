"""Offline, single-file installer. Production root/commands are never configurable.

Setup 0.3.1 installs the unchanged plugin 0.3.0 payload. Python >= 3.6.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import tempfile
import zipfile


SETUP_VERSION = '0.3.1'
PLUGIN_VERSION = '0.3.0'
BUNDLE_SHA256 = 'fe3c2fafcc986c64b2dde6d8cb1149a443fc8ad2ae48120888b3554b7a1762b3'
ROOT = Path('/usr/local/mgr5')
MAX_BUNDLE_BYTES = 16 * 1024 * 1024
MAX_UNPACKED_BYTES = 64 * 1024 * 1024


class SetupError(Exception):
    pass


def unpack_bundle(data, destination):
    if len(data) > MAX_BUNDLE_BYTES or hashlib.sha256(data).hexdigest() != BUNDLE_SHA256:
        raise SetupError('BUNDLE_INTEGRITY_FAILED')
    with zipfile.ZipFile(io.BytesIO(data)) as bundle:
        members = bundle.infolist()
        names = [i.filename for i in members]
        if (len(members) > 300 or len(set(names)) != len(names)
                or sum(i.file_size for i in members) > MAX_UNPACKED_BYTES):
            raise SetupError('INVALID_BUNDLE')
        for item in members:
            name = item.filename
            if (not re.fullmatch(r'[A-Za-z0-9_./-]+', name) or name.startswith('/')
                    or any(p in ('', '.', '..') for p in name.split('/'))
                    or not stat.S_ISREG(item.external_attr >> 16)):
                raise SetupError('INVALID_BUNDLE_PATH')
            path = destination / name
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(bundle.read(item))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Setup:
    def __init__(self, source, root=ROOT, uid=0, gid=0, anchor=Path('/')):
        # Alternate roots/owners are unit-test dependencies, not CLI or environment options.
        self.source, self.root = Path(source), Path(root)
        self.uid, self.gid = uid, gid
        self.install_module = load_module('ismonaco_setup_install', self.source / 'install.py')
        self.update_module = load_module('ismonaco_setup_update', self.source / 'update.py')
        self.installer = self.install_module.Installer(self.source, self.root, uid, gid, anchor)
        self.updater = self.update_module.Updater(self.source, self.root, uid, gid, anchor)
        self.expected_errors = (self.install_module.InstallError, self.update_module.InstallError, OSError)

    def panel_preflight(self):
        manager = self.root / 'sbin/mgrctl'
        try:
            self.installer.trusted_parents(manager)
            self.installer.trusted_parents(self.root / 'var/.ismonaco-probe')
            info = os.lstat(str(manager))
        except FileNotFoundError:
            raise SetupError('ISP_MANAGER_NOT_FOUND') from None
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != self.uid or info.st_gid != self.gid
                or info.st_mode & 0o022 or not info.st_mode & 0o100):
            raise SetupError('PANEL_MANAGER_UNTRUSTED')

    @contextmanager
    def lock(self):
        self.panel_preflight()
        path = self.root / 'var/ismonaco-setup.lock'
        fd = os.open(str(path), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != self.uid or info.st_gid != self.gid
                    or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
                raise SetupError('SETUP_LOCK_UNTRUSTED')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise SetupError('ANOTHER_SETUP_RUNNING') from None
            yield
        finally:
            os.close(fd)

    def plan(self):
        self.panel_preflight()
        registration = self.root / self.install_module.XML
        if os.path.lexists(str(self.root / (self.install_module.XML + '.disabled'))):
            raise SetupError('DISABLED_INSTALLATION_REQUIRES_REVIEW')
        if not os.path.lexists(str(registration)):
            # Reject orphaned/partial files; do not mistake them for a clean install.
            self.installer.preflight()
            return 'NEW_INSTALL'
        try:
            self.installer.verify()
            return 'ALREADY_CURRENT'
        except self.expected_errors:
            pass
        try:
            self.updater.verify_previous()
        except self.expected_errors:
            raise SetupError('UNSUPPORTED_OR_MODIFIED_INSTALLATION') from None
        self.updater.check()
        return 'UPDATE_0_2_5'

    def check(self, probe=None):
        mode = self.plan()
        (probe or self.install_module.runtime_probe)(self.source)
        return mode

    def apply(self, probe=None):
        mode = self.plan()
        if mode == 'ALREADY_CURRENT':
            return mode
        probe = probe or self.install_module.runtime_probe
        if mode == 'NEW_INSTALL':
            probe(self.source)
            self.installer.install()  # Registration is published last; verifies all files.
        else:
            self.updater.apply(runner=probe)  # Preserves appearance settings byte-for-byte.
        return mode

    def rollback(self):
        self.panel_preflight()
        if not os.path.lexists(str(self.root / self.update_module.BACKUP)):
            raise SetupError('NO_UPGRADE_BACKUP')
        self.updater.rollback()  # Existing verified XML backup only; no file deletion.

    def restart_panel(self, runner=subprocess.run):
        self.panel_preflight()
        try:
            result = runner([str(self.root / 'sbin/mgrctl'), '-m', 'ispmgr', 'exit'],
                            env={}, cwd='/', stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        except (OSError, subprocess.SubprocessError):
            raise SetupError('RESTART_REQUIRED') from None
        if result.returncode != 0:
            raise SetupError('RESTART_REQUIRED')


def main():
    parser = argparse.ArgumentParser(description='Monaco offline setup 0.3.1: auto-install/update; keeps settings.')
    parser.add_argument('action', nargs='?', default='install', choices=('install', 'check', 'verify', 'rollback', 'restart'))
    parser.add_argument('--no-restart', action='store_true', help='Keep panel running; restart later with the restart action.')
    args = parser.parse_args()
    if platform.system() != 'Linux' or os.geteuid() != 0:
        print('LINUX_ROOT_REQUIRED', file=sys.stderr)
        return 1
    if sys.version_info < (3, 6):
        print('PYTHON_3_6_OR_NEWER_REQUIRED', file=sys.stderr)
        return 1
    if not os.access('/usr/bin/python3', os.X_OK):
        print('SYSTEM_PYTHON_REQUIRED', file=sys.stderr)
        return 1
    try:
        with zipfile.ZipFile(sys.argv[0]) as app:
            item = app.getinfo('bundle.zip')
            if item.file_size > MAX_BUNDLE_BYTES:
                raise SetupError('BUNDLE_TOO_LARGE')
            data = app.read(item)
        # New private staging files only; no uploaded archives or panel data are removed.
        with tempfile.TemporaryDirectory(prefix='ismonaco-setup-') as temporary:
            source = Path(temporary)
            unpack_bundle(data, source)
            setup = Setup(source)
            print('MONACO_SETUP_VERSION=' + SETUP_VERSION + ' PLUGIN_VERSION=' + PLUGIN_VERSION, flush=True)
            if args.action == 'check':
                print('MONACO_SETUP_CHECK_OK MODE=' + setup.check())
            elif args.action == 'verify':
                setup.panel_preflight()
                setup.installer.verify()
                print('MONACO_SETUP_VERIFY_OK')
            else:
                with setup.lock():
                    if args.action == 'install':
                        mode = setup.apply()
                        print('MONACO_SETUP_APPLY_OK MODE=' + mode, flush=True)
                        changed = mode != 'ALREADY_CURRENT'
                    elif args.action == 'rollback':
                        setup.rollback()
                        print('MONACO_SETUP_ROLLBACK_OK', flush=True)
                        changed = True
                    else:
                        setup.installer.verify()
                        changed = True
                    if changed:
                        if args.no_restart:
                            print('MONACO_SETUP_RESTART_PENDING')
                        else:
                            setup.restart_panel()
                            print('MONACO_SETUP_RESTART_REQUESTED')
    except Exception as error:
        # Do not print native output, file contents or uncontrolled exception strings.
        code = str(error)
        if not isinstance(error, SetupError) and error.__class__.__name__ != 'InstallError':
            code = 'SETUP_IO_OR_BUNDLE_ERROR'
        if not re.fullmatch(r'[A-Z][A-Z0-9_]{1,100}', code):
            code = 'SETUP_FAILED'
        print('MONACO_SETUP_ERROR=' + code, file=sys.stderr)
        return 2 if code == 'RESTART_REQUIRED' else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
