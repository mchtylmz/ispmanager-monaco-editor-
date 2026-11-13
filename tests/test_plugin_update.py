"""Only the new 0.3.0 installer/reused-payload and notice recovery boundaries."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('plugin_update', str(PROJECT / 'integration/plugin/update.py'))
update = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(update)


class PluginUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.anchor = Path(self.temp.name)
        self.root, self.old, self.source = self.anchor / 'mgr5', self.anchor / 'old', self.anchor / 'new'
        for file, destination in [('ismonaco-editor-0.2.5.zip', self.old), ('ismonaco-plugin-0.3.0.zip', self.source)]:
            with zipfile.ZipFile(str(PROJECT / 'dist' / file)) as z: z.extractall(str(destination))
        spec = importlib.util.spec_from_file_location('old_editor_install', str(self.old / 'install.py'))
        old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
        for name in ('addon', 'etc/xml', 'skins'): (self.root / name).mkdir(parents=True, exist_ok=True)
        old.Installer(self.old, self.root, os.getuid(), os.getgid(), self.anchor).install()
        self.installer = update.Updater(self.source, self.root, os.getuid(), os.getgid(), self.anchor)
        self.original = (self.root / update.REGISTRATION).read_bytes()

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns)
                for p in self.root.rglob('*') if p.is_file()}

    def test_check_is_readonly_apply_reuses_exact_editor_and_defaults_and_rollback_preserves_note(self):
        before = self.snapshot()
        self.installer.check(); self.assertEqual(self.snapshot(), before)
        self.installer.apply(); self.installer.verify()
        after = self.snapshot()
        for name, identity in before.items():
            if name != update.REGISTRATION: self.assertEqual(after[name], identity)
        note = self.root / update.installer.NOTICE_CONFIG
        note.write_text(json.dumps({'version':1,'style':'warning','text':'IP note'}))
        self.installer.verify(); self.installer.rollback()
        self.assertEqual((self.root / update.REGISTRATION).read_bytes(), self.original)
        self.assertIn('IP note', note.read_text())

    def test_modified_old_handler_and_reused_payload_refused_before_any_new_file(self):
        path = self.root / update.installer.PYTHON
        path.write_bytes(b'foreign')
        with self.assertRaisesRegex(update.InstallError, 'PREVIOUS_FILE_HASH_MISMATCH'): self.installer.apply()
        self.assertFalse((self.root / update.installer.NOTICE_PYTHON).exists())

    def test_existing_notice_target_or_backup_not_overwritten(self):
        target = self.root / update.installer.NOTICE_PYTHON
        target.write_bytes(b'keep')
        with self.assertRaisesRegex(update.InstallError, 'NEW_TARGET_EXISTS'): self.installer.apply()
        self.assertEqual(target.read_bytes(), b'keep')
        self.assertEqual((self.root / update.REGISTRATION).read_bytes(), self.original)

    def test_runtime_failure_before_new_files_or_registration(self):
        def fail(_): raise update.InstallError('TEST_PROBE_FAILED')
        with self.assertRaisesRegex(update.InstallError, 'TEST_PROBE_FAILED'): self.installer.apply(runner=fail)
        self.assertFalse((self.root / update.installer.NOTICE_PYTHON).exists())
        self.assertFalse((self.root / update.BACKUP).exists())

    def test_new_file_io_failure_keeps_old_registration_and_editor(self):
        original = self.installer.create_file
        def fail(path, mode, data):
            if path == self.root / update.installer.NOTICE_CONFIG: raise OSError('disk full')
            return original(path, mode, data)
        with patch.object(self.installer, 'create_file', side_effect=fail):
            with self.assertRaises(OSError): self.installer.apply()
        self.assertEqual((self.root / update.REGISTRATION).read_bytes(), self.original)
        self.assertFalse((self.root / update.BACKUP).exists())

    def test_tampered_payload_does_not_publish_new_registration(self):
        (self.source / 'payload' / update.installer.NOTICE_PYTHON).write_bytes(b'tampered')
        with self.assertRaisesRegex(update.InstallError, 'PAYLOAD_HASH_MISMATCH'): self.installer.apply()
        self.assertEqual((self.root / update.REGISTRATION).read_bytes(), self.original)

    def test_invalid_or_symlinked_notice_config_detected_without_rollback_overwrite(self):
        self.installer.apply()
        config = self.root / update.installer.NOTICE_CONFIG
        config.write_text('{"version":1,"style":"danger","text":"x"}')
        with self.assertRaisesRegex(update.InstallError, 'INVALID_NOTICE_CONFIG'): self.installer.rollback()
        config.unlink(); config.symlink_to(self.anchor / 'missing')
        with self.assertRaisesRegex(update.InstallError, 'INSTALLED_FILE_MISMATCH'): self.installer.verify()

    def test_fresh_install_and_verify_allow_only_valid_mutable_notice(self):
        fresh_root = self.anchor / 'fresh'
        for name in ('addon','etc/xml','skins'): (fresh_root / name).mkdir(parents=True, exist_ok=True)
        fresh = update.installer.Installer(self.source, fresh_root, os.getuid(), os.getgid(), self.anchor)
        fresh.install(); fresh.verify()
        config = fresh_root / update.installer.NOTICE_CONFIG
        value = json.loads(config.read_text()); value['text'] = 'ş'*2049
        config.write_text(json.dumps(value))
        with self.assertRaisesRegex(update.InstallError, 'INVALID_NOTICE_CONFIG'): fresh.verify()


if __name__ == '__main__': unittest.main()
