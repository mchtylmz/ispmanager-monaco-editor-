"""Exercise the narrow update against the exact released 0.2.4 archive."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('preview_update', str(PROJECT / 'integration/editor/update.py'))
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class EditorUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.anchor = Path(self.temp.name)
        self.root, self.source = self.anchor / 'mgr5', self.anchor / 'stage'
        old = self.anchor / 'old'
        with zipfile.ZipFile(str(PROJECT / 'dist/ismonaco-editor-0.2.4.zip')) as archive:
            archive.extractall(str(old))
        for name in ('addon', 'etc/xml', 'skins'):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        spec = importlib.util.spec_from_file_location('previous_release', str(old / 'install.py'))
        previous = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(previous)
        previous.Installer(old, self.root, os.getuid(), os.getgid(), self.anchor).install()
        self.old_registration = (self.root / module.REGISTRATION).read_bytes()
        payloads = {name: (PROJECT / 'integration/editor' / {module.installer.PYTHON: 'ismonaco_editor.py', module.installer.WRAPPER: 'ismonaco_editor.sh', module.installer.XML: 'ispmgr_mod_ismonaco_preview.xml', module.installer.CONFIG: 'defaults.json'}[name]).read_bytes()
                    for name in module.installer.HANDLERS}
        for name in ('app.js', 'app.css', 'frame.html', 'editor.worker.js', 'MONACO-LICENSE.txt', 'ThirdPartyNotices.txt'):
            payloads[module.installer.ASSETS + name] = b'new-static-fixture'
        entries = []
        for name, data in payloads.items():
            path = self.source / 'payload' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            entries.append({'target': name, 'mode': module.installer.HANDLERS.get(name, 0o644),
                            'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        (self.source / 'manifest.json').write_text(json.dumps({'version': 1, 'files': entries}))
        (self.source / 'previous-manifest.json').write_bytes((old / 'manifest.json').read_bytes())
        self.updater = module.Updater(self.source, self.root, os.getuid(), os.getgid(), self.anchor)

    def test_check_is_readonly_update_keeps_old_assets_and_rollback_restores_old_handler(self):
        before = set(self.root.rglob('*'))
        self.updater.check()
        self.assertEqual(set(self.root.rglob('*')), before)
        old_inode = (self.root / module.REGISTRATION).stat().st_ino
        self.updater.apply()
        self.updater.verify()
        self.assertEqual((self.root / module.BACKUP).read_bytes(), self.old_registration)
        self.assertNotEqual((self.root / module.BACKUP).stat().st_ino, old_inode)
        self.assertTrue((self.root / 'skins/ismonaco-editor-0.2.4/app.js').exists())
        self.updater.rollback()
        self.assertEqual((self.root / module.REGISTRATION).read_bytes(), self.old_registration)
        self.assertTrue((self.root / module.BACKUP).exists())
        self.assertTrue((self.root / module.installer.ASSETS / 'frame.html').exists())

    def test_update_and_rollback_preserve_existing_server_preferences(self):
        config = self.root / module.OLD_CONFIG
        value = json.loads(config.read_text()); value['theme'] = 'light'; value['height'] = 1080
        config.write_text(json.dumps(value)); config.chmod(0o600)
        before = (config.read_bytes(), config.stat().st_mtime_ns, config.stat().st_ino)
        self.updater.check(); self.updater.apply(); self.updater.verify()
        new_config = self.root / module.installer.CONFIG
        new_values = json.loads(new_config.read_text())
        self.assertEqual(new_values, value)
        self.updater.rollback()
        self.assertEqual(json.loads(new_config.read_text()), new_values)
        self.assertEqual((config.read_bytes(), config.stat().st_mtime_ns, config.stat().st_ino), before)

    def test_foreign_modified_handler_stops_before_writes(self):
        (self.root / module.REGISTRATION).write_bytes(b'foreign-change')
        with self.assertRaisesRegex(module.InstallError, 'PREVIOUS_FILE_HASH_MISMATCH'):
            self.updater.apply()
        self.assertFalse((self.root / module.BACKUP).exists())
        self.assertFalse((self.root / module.installer.ASSETS).exists())

    def test_symlinked_handler_and_existing_backup_are_not_overwritten(self):
        path = self.root / module.REGISTRATION
        path.unlink()
        path.symlink_to(self.anchor / 'not-present')
        with self.assertRaisesRegex(module.InstallError, 'PREVIOUS_FILE_METADATA_MISMATCH'):
            self.updater.apply()

    def test_existing_backup_stops_update(self):
        (self.root / module.BACKUP).write_bytes(b'keep-this')
        with self.assertRaisesRegex(module.InstallError, 'BACKUP_EXISTS'):
            self.updater.apply()
        self.assertEqual((self.root / module.BACKUP).read_bytes(), b'keep-this')

    def test_asset_failure_keeps_live_handler_and_registration_intact(self):
        registration = (self.root / module.installer.XML).read_bytes()
        original = self.updater.create_file
        def fail(target, mode, data):
            if str(target).startswith(str(self.root / module.installer.ASSETS)):
                raise OSError('test failure')
            return original(target, mode, data)
        with patch.object(self.updater, 'create_file', side_effect=fail):
            with self.assertRaises(OSError):
                self.updater.apply()
        self.assertEqual((self.root / module.REGISTRATION).read_bytes(), self.old_registration)
        self.assertEqual((self.root / module.installer.XML).read_bytes(), registration)
        self.assertFalse((self.root / module.BACKUP).exists())

    def test_runtime_failure_stops_before_assets_or_backup_are_written(self):
        def fail(_):
            raise module.InstallError('RUNTIME_PROBE_FAILED')
        with self.assertRaisesRegex(module.InstallError, 'RUNTIME_PROBE_FAILED'):
            self.updater.apply(runner=fail)
        self.assertFalse((self.root / module.installer.ASSETS).exists())
        self.assertFalse((self.root / module.BACKUP).exists())

    def test_rollback_refuses_drift_and_previous_manifest_cannot_be_replaced(self):
        self.updater.apply()
        (self.root / module.REGISTRATION).write_bytes(b'changed-after-update')
        with self.assertRaisesRegex(module.InstallError, 'INSTALLED_FILE_MISMATCH'):
            self.updater.rollback()
        (self.source / 'previous-manifest.json').write_text('{}')
        with self.assertRaisesRegex(module.InstallError, 'PREVIOUS_MANIFEST_MISMATCH'):
            self.updater.previous()


if __name__ == '__main__':
    unittest.main()
