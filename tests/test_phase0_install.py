"""Exercise installation in private local temporary dirs, never /usr/local."""

import importlib.util
import os
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest import mock


LAB = Path(__file__).resolve().parents[1] / "lab/phase0"
SPEC = importlib.util.spec_from_file_location("phase0_install", str(LAB / "install.py"))
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.anchor = Path(self.directory.name)
        self.root = self.anchor / "mgr5"
        self.source = self.anchor / "source"
        self.source.mkdir(mode=0o700)
        for name, _, _, _ in module.PAYLOADS:
            shutil.copyfile(str(LAB / name), str(self.source / name))
        for path in (self.root, self.root / "addon", self.root / "etc", self.root / "etc/xml"):
            path.mkdir(mode=0o755)
        self.runner = mock.Mock()
        self.installer = module.Installer(
            self.source, self.root, os.getuid(), os.getgid(), self.anchor, self.runner,
        )

    def test_installs_exact_payloads_with_permissions_and_xml_last(self):
        original = self.installer.atomic_create
        destinations = []
        def capture(destination, data, mode):
            destinations.append(destination)
            return original(destination, data, mode)
        with mock.patch.object(self.installer, "atomic_create", side_effect=capture):
            self.installer.install()
        self.assertEqual(destinations[-1].name, "ispmgr_mod_ismonaco_phase0.xml")
        for name, relative, mode, _ in module.PAYLOADS:
            target = self.root / relative
            self.assertEqual(target.read_bytes(), (LAB / name).read_bytes())
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), mode)
        self.assertEqual(list(self.root.rglob(".ismonaco-phase0-*")), [])

    def test_existing_file_or_dangling_link_stops_before_any_install(self):
        target = self.root / module.PAYLOADS[-1][1]
        for symlink in (False, True):
            with self.subTest(symlink=symlink):
                if symlink:
                    target.symlink_to(self.anchor / "missing-private-target")
                else:
                    target.write_text("private-existing-file")
                with self.assertRaisesRegex(module.InstallError, "^TARGET_EXISTS$"):
                    self.installer.install()
                self.assertEqual(list((self.root / "addon").iterdir()), [])
                self.runner.assert_not_called()
                if not symlink:
                    self.assertEqual(target.read_text(), "private-existing-file")
                target.unlink()

    def test_corrupt_payload_is_rejected_before_writes(self):
        (self.source / module.PAYLOADS[0][0]).write_text("invalid payload")
        with self.assertRaisesRegex(module.InstallError, "^PAYLOAD_HASH_MISMATCH$"):
            self.installer.install()
        self.assertEqual(list((self.root / "addon").iterdir()), [])
        self.runner.assert_not_called()

    def test_source_symlink_is_not_followed(self):
        source = self.source / module.PAYLOADS[0][0]
        source.unlink()
        source.symlink_to(LAB / module.PAYLOADS[0][0])
        with self.assertRaisesRegex(module.InstallError, "^PAYLOAD_UNREADABLE$"):
            self.installer.install()
        self.runner.assert_not_called()

    def test_writable_parent_is_rejected(self):
        (self.root / "addon").chmod(0o777)
        with self.assertRaisesRegex(module.InstallError, "^UNTRUSTED_TARGET_DIRECTORY$"):
            self.installer.install()
        self.runner.assert_not_called()

    def test_runtime_failure_does_not_publish_xml(self):
        for failure_at in (0, 1):
            with self.subTest(failure_at=failure_at):
                self.runner.reset_mock(side_effect=True)
                self.runner.side_effect = ([None] * failure_at) + [module.InstallError("RUNTIME_TEST_FAILED")]
                with self.assertRaisesRegex(module.InstallError, "^RUNTIME_TEST_FAILED$"):
                    self.installer.install()
                self.assertFalse((self.root / module.PAYLOADS[-1][1]).exists())
                for path in (self.root / "addon").iterdir():
                    path.unlink()

    def test_creation_race_does_not_overwrite_existing_target(self):
        target = self.root / "addon/ismonaco_phase0.py"
        target.write_text("private-existing-file")
        with self.assertRaisesRegex(module.InstallError, "^TARGET_EXISTS$"):
            self.installer.atomic_create(target, b"replacement", 0o640)
        self.assertEqual(target.read_text(), "private-existing-file")
        self.assertEqual(list(target.parent.glob(".ismonaco-phase0-*")), [])

    def test_verification_rejects_tampered_file_and_permissions(self):
        self.installer.install()
        target = self.root / module.PAYLOADS[0][1]
        original = target.read_bytes()
        target.write_bytes(b"tampered")
        with self.assertRaisesRegex(module.InstallError, "^TARGET_HASH_MISMATCH$"):
            self.installer.verify()
        target.write_bytes(original)
        target.chmod(0o777)
        with self.assertRaisesRegex(module.InstallError, "^TARGET_METADATA_MISMATCH$"):
            self.installer.verify()


if __name__ == "__main__":
    unittest.main()
