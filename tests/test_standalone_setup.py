"""Narrow setup detection, preservation and refusal tests; no native server."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('standalone_setup', str(PROJECT / 'integration/standalone/launcher.py'))
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class StandaloneSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.anchor = Path(self.temp.name)
        self.source, self.root = self.anchor / 'stage', self.anchor / 'mgr5'
        self.source.mkdir(mode=0o700)
        self.data = (PROJECT / 'dist/ismonaco-plugin-0.3.0.zip').read_bytes()
        launcher.unpack_bundle(self.data, self.source)
        for name in ('addon','etc/xml','skins','var','sbin'): (self.root / name).mkdir(parents=True, exist_ok=True)
        manager = self.root / 'sbin/mgrctl'; manager.write_text('#!/bin/sh\nexit 0\n'); manager.chmod(0o750)
        self.setup = launcher.Setup(self.source, self.root, os.getuid(), os.getgid(), self.anchor)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns)
                for p in self.root.rglob('*') if p.is_file()}

    def test_clean_check_is_readonly_install_then_current_keeps_changed_preferences(self):
        before = self.snapshot(); calls = []
        self.assertEqual(self.setup.check(probe=calls.append), 'NEW_INSTALL')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.setup.apply(probe=calls.append), 'NEW_INSTALL')
        self.assertEqual(len(calls), 2)
        config = self.root / self.setup.install_module.CONFIG
        value = json.loads(config.read_text()); value['theme'] = 'light'; value['fontSize'] = 18
        config.write_text(json.dumps(value))
        note = self.root / self.setup.install_module.NOTICE_CONFIG
        note.write_text(json.dumps(dict(version=1, style='warning', text='IP A\nIP B')))
        before = self.snapshot()
        self.assertEqual(self.setup.apply(probe=calls.append), 'ALREADY_CURRENT')
        self.assertEqual(self.snapshot(), before); self.assertEqual(len(calls), 2)

    def install_previous(self):
        old = self.anchor / 'old'
        with zipfile.ZipFile(str(PROJECT / 'dist/ismonaco-editor-0.2.5.zip')) as z: z.extractall(str(old))
        module = launcher.load_module('previous_editor_install', old / 'install.py')
        module.Installer(old, self.root, os.getuid(), os.getgid(), self.anchor).install()

    def test_old_editor_detected_upgrade_and_rollback_preserve_preferences(self):
        self.install_previous()
        config = self.root / self.setup.install_module.CONFIG
        value = json.loads(config.read_text()); value['height'] = 1080
        config.write_text(json.dumps(value)); identity = config.read_bytes(), config.stat().st_ino, config.stat().st_mtime_ns
        before = self.snapshot()
        self.assertEqual(self.setup.check(probe=lambda _: None), 'UPDATE_0_2_5')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.setup.apply(probe=lambda _: None), 'UPDATE_0_2_5')
        self.assertEqual((config.read_bytes(), config.stat().st_ino, config.stat().st_mtime_ns), identity)
        note = self.root / self.setup.install_module.NOTICE_CONFIG
        note.write_text(json.dumps(dict(version=1,style='info',text='KEEP_NOTE')))
        self.setup.rollback()
        self.assertEqual((config.read_bytes(), config.stat().st_ino, config.stat().st_mtime_ns), identity)
        self.assertIn('KEEP_NOTE', note.read_text())

    def test_modified_unknown_partial_and_disabled_installations_never_overwritten(self):
        self.setup.apply(probe=lambda _: None)
        registration = self.root / self.setup.install_module.XML
        registration.write_bytes(b'foreign XML')
        before = self.snapshot()
        with self.assertRaisesRegex(launcher.SetupError, 'UNSUPPORTED_OR_MODIFIED'): self.setup.apply()
        self.assertEqual(self.snapshot(), before)
        registration.unlink()
        before = self.snapshot()
        with self.assertRaises(self.setup.expected_errors): self.setup.apply()
        self.assertEqual(self.snapshot(), before)
        disabled = self.root / (self.setup.install_module.XML + '.disabled'); disabled.write_bytes(b'disabled')
        with self.assertRaisesRegex(launcher.SetupError, 'DISABLED_INSTALLATION'): self.setup.apply()

    def test_probe_and_io_failure_do_not_publish_registration(self):
        def fail(_): raise launcher.SetupError('PROBE_FAILED')
        before = self.snapshot()
        with self.assertRaisesRegex(launcher.SetupError, 'PROBE_FAILED'): self.setup.apply(probe=fail)
        self.assertEqual(self.snapshot(), before)
        original = self.setup.installer.create_file
        def fail_file(path, mode, data):
            if str(path).startswith(str(self.root / 'skins')): raise OSError('test IO failure')
            return original(path,mode,data)
        with patch.object(self.setup.installer, 'create_file', side_effect=fail_file):
            with self.assertRaises(OSError): self.setup.apply(probe=lambda _: None)
        self.assertFalse((self.root / self.setup.install_module.XML).exists())

    def test_single_writer_lock_and_untrusted_symlink_lock_are_refused(self):
        with self.setup.lock():
            with self.assertRaisesRegex(launcher.SetupError, 'ANOTHER_SETUP_RUNNING'):
                with self.setup.lock(): pass
        path = self.root / 'var/ismonaco-setup.lock'
        path.unlink(); external = self.anchor / 'external'; external.write_text('keep')
        path.symlink_to(external)
        with self.assertRaises(OSError):
            with self.setup.lock(): pass
        self.assertEqual(external.read_text(), 'keep')

    def test_bundle_digest_and_traversal_or_symlink_entry_refused(self):
        with self.assertRaisesRegex(launcher.SetupError, 'BUNDLE_INTEGRITY_FAILED'):
            launcher.unpack_bundle(self.data + b'x', self.anchor / 'other')
        for name, mode in [('../escape', 0o100644), ('link', 0o120777)]:
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w') as z:
                info = zipfile.ZipInfo(name); info.external_attr = mode << 16; z.writestr(info, b'bad')
            data = stream.getvalue()
            with patch.object(launcher, 'BUNDLE_SHA256', hashlib.sha256(data).hexdigest()):
                with self.assertRaisesRegex(launcher.SetupError, 'INVALID_BUNDLE_PATH'):
                    launcher.unpack_bundle(data, self.anchor / 'unsafe')
        self.assertFalse((self.anchor / 'escape').exists())

    def test_manager_permissions_restart_fixed_args_and_error_separation(self):
        calls = []
        def runner(args, **kwargs):
            calls.append((args, kwargs)); return subprocess.CompletedProcess(args, 0)
        self.setup.restart_panel(runner)
        self.assertEqual(calls[0][0], [str(self.root / 'sbin/mgrctl'), '-m', 'ispmgr', 'exit'])
        self.assertEqual(calls[0][1]['env'], {})
        with self.assertRaisesRegex(launcher.SetupError, 'RESTART_REQUIRED'):
            self.setup.restart_panel(lambda *a, **k: subprocess.CompletedProcess(a, 1, b'PRIVATE', b'PRIVATE'))
        (self.root / 'sbin/mgrctl').chmod(0o777)
        with self.assertRaisesRegex(launcher.SetupError, 'PANEL_MANAGER_UNTRUSTED'): self.setup.plan()
        (self.root / 'sbin/mgrctl').unlink()
        with self.assertRaisesRegex(launcher.SetupError, 'ISP_MANAGER_NOT_FOUND'): self.setup.plan()

    def test_no_backup_rollback_and_nonroot_cli_refuse_without_changes(self):
        before = self.snapshot()
        with self.assertRaisesRegex(launcher.SetupError, 'NO_UPGRADE_BACKUP'): self.setup.rollback()
        self.assertEqual(self.snapshot(), before)
        with patch.object(launcher.platform, 'system', return_value='Linux'), patch.object(launcher.os, 'geteuid', return_value=999), patch.object(launcher.sys, 'argv', ['setup.pyz']):
            self.assertEqual(launcher.main(), 1)
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__': unittest.main()
