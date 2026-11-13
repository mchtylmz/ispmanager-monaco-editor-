import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import unittest
from unittest import mock


TOOL = Path(__file__).resolve().parents[1] / "tools" / "collect_environment.py"
SPEC = importlib.util.spec_from_file_location("collect_environment", str(TOOL))
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


class FakeHost:
    def __init__(self):
        self.data = {
            "os_release": 'ID="rocky"\nVERSION_ID="8.10"\nHOSTNAME=secret-host\n',
            "memory": "MemTotal:       2097152 kB\n",
            "panel_config": "Password secret-value\nFileMaxEditSize 1024\n",
            "selinux": "1\n",
            "cgroup_controllers": "cpu memory pids\n",
            "cgroup_mounts": "none /sys/fs/cgroup cgroup2 rw,nosuid,nodev,noexec 0 0\n",
            "cgroup_v1_controllers": "#subsys_name hierarchy num_cgroups enabled\n",
        }
        self.package_data = {
            "manager": "rpm",
            "items": inventory.parse_packages(
                "coremanager\t5.450-1\tx86_64\n"
                "ispmanager-lite-common\t6.155-1\tx86_64\n"
            ),
        }
        self.root = False

    def system(self):
        return "Linux"

    def machine(self):
        return "x86_64"

    def effective_uid(self):
        return 0 if self.root else 1000

    def cpu_count(self):
        return 2

    def read(self, key):
        value = self.data[key]
        if isinstance(value, Exception):
            raise value
        return value

    def panel_path_present(self, key):
        return True

    def packages(self):
        if isinstance(self.package_data, Exception):
            raise self.package_data
        return self.package_data


class ParserTests(unittest.TestCase):
    def test_os_release_parses_data_without_copying_unrelated_fields(self):
        result = inventory.parse_os_release(FakeHost().data["os_release"])
        self.assertEqual(result, {"id": "rocky", "version_id": "8.10"})

    def test_os_release_rejects_shell_substitution_and_duplicates(self):
        for text in (
            'ID="$(touch /tmp/should-not-run)"\nVERSION_ID="8.10"',
            "ID=rocky\nID=debian\nVERSION_ID=8.10",
            "ID=rocky",
        ):
            with self.subTest(text=text), self.assertRaises(inventory.ProbeError):
                inventory.parse_os_release(text)

    def test_package_versions_are_not_panel_release_assertions(self):
        result = inventory.parse_packages(
            "coremanager\t5.450-1\tx86_64\n"
            "private-company-package\tsecret-value\tx86_64\n"
            "php8.2-cli\t8.2.0-1\tamd64\n"
        )
        self.assertEqual([item["name"] for item in result], ["coremanager", "php8.2-cli"])
        self.assertEqual(result[0]["package_version"], "5.450-1")
        self.assertNotIn("secret-value", json.dumps(result))

    def test_malformed_allowlisted_package_is_not_reported_as_valid(self):
        for text in ("coremanager\t6.1\n", "coremanager\thttps://secret\tx86_64\n"):
            with self.subTest(text=text), self.assertRaises(inventory.ProbeError):
                inventory.parse_packages(text)

    def test_config_only_extracts_limit_not_credentials(self):
        result = inventory.parse_file_limit(FakeHost().data["panel_config"])
        self.assertEqual(result, {"configured_kib": 1024, "effective_value_verified": False})
        self.assertNotIn("secret-value", json.dumps(result))

    def test_config_does_not_guess_default_or_included_value(self):
        result = inventory.parse_file_limit("Include custom.conf\nPassword secret-value\n")
        self.assertIsNone(result["configured_kib"])
        self.assertFalse(result["effective_value_verified"])

    def test_config_rejects_invalid_or_ambiguous_limits(self):
        for text in (
            "FileMaxEditSize 0", "FileMaxEditSize -1", "FileMaxEditSize lots",
            "FileMaxEditSize 1024 extra", "FileMaxEditSize 1024\nFileMaxEditSize 2048",
        ):
            with self.subTest(text=text), self.assertRaises(inventory.ProbeError):
                inventory.parse_file_limit(text)

    def test_cgroup_metadata_does_not_claim_isolation(self):
        result = inventory.parse_controllers("memory cpu pids")
        self.assertFalse(result["isolation_verified"])
        with self.assertRaises(inventory.ProbeError):
            inventory.parse_controllers("memory unrecognized-controller")


class CgroupInventoryTests(unittest.TestCase):
    def test_v2_observation_does_not_verify_isolation(self):
        report = inventory.collect_inventory(FakeHost())
        result = report["facts"]["cgroups"]
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["value"]["mode"], "v2")
        self.assertEqual(result["value"]["mounted_v1_controllers"], [])
        self.assertFalse(result["value"]["isolation_verified"])
        self.assertFalse(report["features"]["lsp"])

    def test_tmpfs_root_with_v1_mounts_is_not_misclassified_as_missing(self):
        host = FakeHost()
        host.data["cgroup_mounts"] = (
            "tmpfs /sys/fs/cgroup tmpfs rw 0 0\n"
            "cgroup /sys/fs/cgroup/memory cgroup rw,memory 0 0\n"
            "cgroup /sys/fs/cgroup/cpu cgroup rw,cpu,cpuacct 0 0\n"
            "cgroup /sys/fs/cgroup/devices cgroup rw,devices 0 0\n"
            "secret-device /private/secret-path ext4 rw,secret-option 0 0\n"
        )
        host.data["cgroup_v1_controllers"] = (
            "#subsys_name hierarchy num_cgroups enabled\n"
            "memory 4 3 1\ncpu 2 3 1\ncpuacct 2 3 1\n"
            "devices 5 1 0\npids 6 2 1\nfreezer 0 1 1\n"
        )
        host.data["cgroup_controllers"] = inventory.ProbeError("not_found")
        result = inventory.collect_inventory(host)["facts"]["cgroups"]
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["value"]["mode"], "v1")
        self.assertEqual(result["value"]["mounted_v1_controllers"], ["cpu", "cpuacct", "memory"])
        self.assertEqual(result["value"]["visible_v2_controllers"], [])
        self.assertFalse(result["value"]["isolation_verified"])
        self.assertNotIn("secret-", json.dumps(result))

    def test_hybrid_mounts_keep_v1_and_v2_evidence_separate(self):
        host = FakeHost()
        host.data["cgroup_mounts"] += "cgroup /sys/fs/cgroup/memory cgroup rw,memory 0 0\n"
        host.data["cgroup_v1_controllers"] += "memory 4 3 1\n"
        result = inventory.collect_cgroups(host)
        self.assertEqual(result["mode"], "hybrid")
        self.assertEqual(result["mounted_v1_controllers"], ["memory"])
        self.assertIn("cpu", result["visible_v2_controllers"])
        self.assertFalse(result["isolation_verified"])

    def test_tmpfs_alone_does_not_prove_v1(self):
        host = FakeHost()
        host.data["cgroup_mounts"] = "tmpfs /sys/fs/cgroup tmpfs rw 0 0\n"
        result = inventory.collect_inventory(host)["facts"]["cgroups"]
        self.assertEqual(result, {"status": "unknown", "reason": "cgroup_mount_not_observed"})

    def test_missing_controller_metadata_is_unknown(self):
        host = FakeHost()
        host.data["cgroup_controllers"] = PermissionError("secret detail")
        result = inventory.collect_inventory(host)["facts"]["cgroups"]
        self.assertEqual(result["status"], "unknown")
        self.assertNotIn("secret detail", json.dumps(result))

    def test_malformed_or_ambiguous_controller_tables_are_rejected(self):
        for text in ("memory 4 3 1\nmemory 5 3 1\n", "memory x 3 1\n", "memory 4 3 2\n"):
            with self.subTest(text=text), self.assertRaises(inventory.ProbeError):
                inventory.parse_active_v1_controllers(text)
        with self.assertRaisesRegex(inventory.ProbeError, "invalid_cgroup_mount_metadata"):
            inventory.parse_cgroup_mounts("none /sys/fs/cgroup cgroup2 rw\n")


class InventoryTests(unittest.TestCase):
    def test_complete_inventory_does_not_enable_features_or_complete_phase(self):
        report = inventory.collect_inventory(FakeHost())
        self.assertEqual(report["collection_status"], "collected")
        self.assertFalse(report["phase0_complete"])
        self.assertFalse(any(report["features"].values()))
        self.assertEqual(set(report["integration_checks"].values()), {"not_verified"})
        serialized = json.dumps(report)
        self.assertNotIn("secret-value", serialized)
        self.assertNotIn("secret-host", serialized)

    def test_permission_failure_is_unknown_and_no_escalation_occurs(self):
        host = FakeHost()
        host.data["panel_config"] = PermissionError("secret exception detail")
        report = inventory.collect_inventory(host)
        self.assertFalse(report["facts"]["running_as_root"])
        self.assertEqual(report["facts"]["file_edit_limit"]["status"], "unknown")
        self.assertNotIn("secret exception detail", json.dumps(report))

    def test_missing_required_metadata_produces_partial_inventory(self):
        host = FakeHost()
        host.package_data = inventory.ProbeError("timeout")
        report = inventory.collect_inventory(host)
        self.assertEqual(report["collection_status"], "partial")
        self.assertFalse(report["phase0_complete"])

    def test_non_linux_host_does_not_probe_host_files_or_commands(self):
        host = FakeHost()
        host.system = lambda: "Darwin"
        host.read = mock.Mock(side_effect=AssertionError("must not read"))
        host.packages = mock.Mock(side_effect=AssertionError("must not run"))
        report = inventory.collect_inventory(host)
        self.assertEqual(report["collection_status"], "unsupported_platform")
        self.assertEqual(report["facts"], {})

    def test_unknown_cli_arguments_are_not_treated_as_commands(self):
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit) as error:
            inventory.main(["--command", "anything"])
        self.assertEqual(error.exception.code, 2)

    def test_cli_returns_partial_status_and_valid_json(self):
        host = FakeHost()
        host.data["os_release"] = inventory.ProbeError("unreadable")
        with mock.patch.object(inventory, "LinuxHost", return_value=host), \
                mock.patch("sys.stdout") as output:
            result = inventory.main([])
        self.assertEqual(result, 2)
        report = json.loads(output.write.call_args_list[0].args[0])
        self.assertEqual(report["collection_status"], "partial")


class FileReadTests(unittest.TestCase):
    def test_file_read_is_bounded_and_symlinks_are_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata"
            path.write_text("12345", encoding="utf-8")
            self.assertEqual(inventory.read_regular_file(str(path), limit=5), "12345")
            with self.assertRaisesRegex(inventory.ProbeError, "output_limit"):
                inventory.read_regular_file(str(path), limit=4)
            link = Path(directory) / "link"
            link.symlink_to(path)
            with self.assertRaises(inventory.ProbeError):
                inventory.read_regular_file(str(link))

    def test_fifo_and_directory_are_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            fifo = Path(directory) / "fifo"
            os.mkfifo(str(fifo))
            started = time.monotonic()
            for path in (str(fifo), directory):
                with self.subTest(path=path), self.assertRaises(inventory.ProbeError):
                    inventory.read_regular_file(path)
            self.assertLess(time.monotonic() - started, 1)

    def test_unreadable_data_does_not_leak_content_in_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid"
            path.write_bytes(b"secret-value\xff")
            with self.assertRaisesRegex(inventory.ProbeError, "^invalid_utf8$"):
                inventory.read_regular_file(str(path))

    def test_os_release_symlink_uses_known_fallback_only(self):
        with mock.patch.object(inventory, "read_regular_file") as reader:
            reader.side_effect = [inventory.ProbeError("unreadable_or_symlink"), "ID=rocky"]
            self.assertEqual(inventory.LinuxHost().read("os_release"), "ID=rocky")
        self.assertEqual(
            reader.call_args_list,
            [mock.call("/etc/os-release"), mock.call("/usr/lib/os-release")],
        )


class CommandTests(unittest.TestCase):
    def command(self, code):
        return [sys.executable, "-I", "-B", "-c", code]

    def test_child_does_not_inherit_secret_environment_or_stdin(self):
        code = "import os,sys; print(os.getenv('INVENTORY_TEST_SECRET')); print(len(sys.stdin.read()))"
        with mock.patch.dict(os.environ, {"INVENTORY_TEST_SECRET": "secret-value"}):
            result = inventory.run_bounded(self.command(code))
        self.assertEqual(result, "None\n0\n")

    def test_command_output_limit(self):
        with self.assertRaisesRegex(inventory.ProbeError, "^output_limit$"):
            inventory.run_bounded(self.command("print('x'*4096)"), limit=128)

    def test_command_timeout(self):
        with self.assertRaisesRegex(inventory.ProbeError, "^timeout$"):
            inventory.run_bounded(self.command("import time; time.sleep(5)"), timeout=0.15)

    def test_failure_discards_stderr_and_stdout(self):
        code = "import sys; print('secret-value'); print('secret-value',file=sys.stderr); sys.exit(1)"
        with self.assertRaisesRegex(inventory.ProbeError, "^command_failed$"):
            inventory.run_bounded(self.command(code))

    def test_package_query_uses_fixed_argv_and_rejects_writable_binary(self):
        metadata = mock.Mock(st_mode=stat.S_IFREG | 0o755, st_uid=0)
        with mock.patch.object(inventory.os, "stat", return_value=metadata), \
                mock.patch.object(inventory, "run_bounded", return_value=(
                    "ispmanager-lite-common\t6.155-1\tx86_64\n"
                )) as runner:
            inventory.LinuxHost().packages()
        runner.assert_called_once_with(inventory.PACKAGE_COMMANDS["rpm"])
        metadata.st_mode |= 0o020
        with mock.patch.object(inventory.os, "stat", return_value=metadata), \
                mock.patch.object(inventory, "run_bounded") as runner:
            with self.assertRaisesRegex(inventory.ProbeError, "^untrusted_package_manager$"):
                inventory.LinuxHost().packages()
        runner.assert_not_called()

    def test_empty_rpm_database_does_not_hide_deb_panel_installation(self):
        metadata = mock.Mock(st_mode=stat.S_IFREG | 0o755, st_uid=0)
        with mock.patch.object(inventory.os, "stat", return_value=metadata), \
                mock.patch.object(inventory, "run_bounded", side_effect=[
                    "systemd\t239-1\tx86_64\n",
                    "ispmanager-lite-common\t6.155-1\tamd64\n",
                ]):
            result = inventory.LinuxHost().packages()
        self.assertEqual(result["manager"], "dpkg")

if __name__ == "__main__":
    unittest.main()
