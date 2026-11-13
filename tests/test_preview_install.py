"""Installation boundary and recovery tests in disposable local directories."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('preview_install', str(PROJECT / 'integration/preview/install.py'))
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.anchor = Path(self.temp.name)
        self.root, self.source = self.anchor / 'mgr5', self.anchor / 'stage'
        for name in ('addon', 'etc/xml', 'skins'):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        payloads = {}
        for name in module.HANDLERS:
            payloads[name] = (PROJECT / 'integration/preview' / Path(name).name).read_bytes()
        for name in ('app.js', 'app.css', 'frame.html', 'editor.worker.js', 'MONACO-LICENSE.txt', 'ThirdPartyNotices.txt'):
            payloads[module.ASSETS + name] = b'fixture'
        entries = []
        for name, data in payloads.items():
            path = self.source / 'payload' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            entries.append({'target': name, 'mode': module.HANDLERS.get(name, 0o644),
                            'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data)})
        self.manifest = self.source / 'manifest.json'
        self.manifest.write_text(json.dumps({'version': 1, 'files': entries}))
        self.installer = module.Installer(self.source, self.root, os.getuid(), os.getgid(), self.anchor)

    def test_check_has_no_writes_and_install_then_verify_and_disable_preserves_handlers(self):
        before = set(self.root.rglob('*'))
        self.installer.preflight()
        self.assertEqual(set(self.root.rglob('*')), before)
        self.installer.install()
        self.installer.verify()
        self.installer.disable()
        self.assertFalse((self.root / module.XML).exists())
        self.assertTrue((self.root / (module.XML + '.disabled')).is_file())
        self.assertTrue((self.root / 'addon/ismonaco_preview.py').is_file())
        with self.assertRaisesRegex(module.InstallError, 'ASSET_DIRECTORY_EXISTS'):
            self.installer.install()

    def test_real_runtime_probe_accepts_packaged_handler_without_writing_targets(self):
        before = set(self.root.rglob('*'))
        module.runtime_probe(self.source, executable=sys.executable)
        self.assertEqual(set(self.root.rglob('*')), before)

    def test_existing_handler_stops_before_any_other_file_is_installed(self):
        existing = self.root / 'addon/ismonaco_preview.py'
        existing.write_bytes(b'user-owned-existing')
        with self.assertRaisesRegex(module.InstallError, 'TARGET_EXISTS'):
            self.installer.install()
        self.assertEqual(existing.read_bytes(), b'user-owned-existing')
        self.assertFalse((self.root / module.XML).exists())
        self.assertFalse((self.root / module.ASSETS).exists())

    def test_dangling_target_symlink_cannot_be_overwritten(self):
        (self.root / module.XML).symlink_to(self.anchor / 'not-present')
        with self.assertRaisesRegex(module.InstallError, 'TARGET_EXISTS'):
            self.installer.install()
        self.assertFalse((self.root / 'addon/ismonaco_preview.py').exists())

    def test_writable_or_symlinked_directory_rejected(self):
        (self.root / 'addon').chmod(0o777)
        with self.assertRaisesRegex(module.InstallError, 'UNTRUSTED_DIRECTORY'):
            self.installer.install()
        (self.root / 'addon').chmod(0o755)
        (self.root / 'skins').rmdir()
        target = self.anchor / 'elsewhere'
        target.mkdir()
        (self.root / 'skins').symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(module.InstallError, 'UNTRUSTED_DIRECTORY'):
            self.installer.install()

    def test_manifest_traversal_and_changed_payload_rejected_without_install(self):
        original = self.manifest.read_text()
        value = json.loads(original)
        value['files'][0]['target'] = '../outside'
        self.manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(module.InstallError, 'INVALID_MANIFEST'):
            self.installer.install()
        self.manifest.write_text(original)
        (self.source / 'payload/addon/ismonaco_preview.py').write_bytes(b'modified')
        with self.assertRaisesRegex(module.InstallError, 'PAYLOAD_HASH_MISMATCH'):
            self.installer.install()
        self.assertFalse((self.root / module.XML).exists())

    def test_verify_detects_drift_and_disable_does_not_delete_changed_registration(self):
        self.installer.install()
        target = self.root / module.XML
        target.write_bytes(b'modified-by-admin')
        with self.assertRaisesRegex(module.InstallError, 'INSTALLED_FILE_MISMATCH'):
            self.installer.disable()
        self.assertEqual(target.read_bytes(), b'modified-by-admin')

    def test_atomic_create_does_not_overwrite_existing_destination(self):
        target = self.root / 'addon/occupied'
        target.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):
            self.installer.create_file(target, 0o640, b'replacement')
        self.assertEqual(target.read_bytes(), b'keep')
        self.assertEqual(list(target.parent.glob('.ismonaco-preview-*')), [])

    def test_asset_failure_does_not_publish_native_event_registration(self):
        original = self.installer.create_file
        def fail_on_asset(target, mode, data):
            if str(target).startswith(str(self.root / module.ASSETS)):
                raise OSError('simulated failure')
            return original(target, mode, data)
        with patch.object(self.installer, 'create_file', side_effect=fail_on_asset):
            with self.assertRaises(OSError):
                self.installer.install()
        self.assertFalse((self.root / module.XML).exists())


if __name__ == '__main__':
    unittest.main()
