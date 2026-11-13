"""Local contract tests for a lab probe, not evidence of a working panel install."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


LAB = Path(__file__).resolve().parents[1] / "lab" / "phase0"
SPEC = importlib.util.spec_from_file_location("phase0_probe", str(LAB / "ismonaco_phase0.py"))
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
CONTEXT = {"PARAM_func": "ismonaco.phase0", "AUTH_USER": "root", "AUTH_LEVEL": "30"}


class ProbeTests(unittest.TestCase):
    def test_captured_native_form_matches_the_read_only_handler_contract(self):
        # Captured from a real native mgrctl devel call, with framework/session
        # attributes removed. This is not proof of browser or normal-user access.
        captured = ET.parse(str(
            LAB.parents[1] / "tests/fixtures/ispmanager-6.155.0/phase0-root-form.xml"
        )).getroot()
        generated = probe.response(CONTEXT)
        self.assertIsNone(captured.find("error"))
        self.assertEqual(captured.find("metadata").get("name"), probe.FUNCTION)
        self.assertEqual(captured.find("metadata/form").attrib, generated.find("metadata/form").attrib)
        for document in (captured, generated):
            self.assertEqual(len(document.findall("metadata/form/field")), 7)
            self.assertEqual(document.findall("metadata/form/field/input"), [])
        actual = {item.get("name"): item.text for item in captured.findall("messages/msg")}
        expected = {item.get("name"): item.text for item in generated.findall("messages/msg")}
        self.assertEqual(actual, expected)

    def test_root_context_returns_read_only_status_not_security_approval(self):
        document = probe.response(CONTEXT)
        self.assertIsNone(document.find("error"))
        form = document.find("metadata/form")
        self.assertEqual(form.get("nosubmit"), "yes")
        messages = {element.get("name"): element.text for element in document.findall("messages/msg")}
        for name in ("file_read_value", "file_write_value", "lsp_value"):
            self.assertEqual(messages[name], "Disabled")
        self.assertEqual(messages["session_value"], "Not verified")
        self.assertEqual(messages["sandbox_value"], "Not verified")

    def test_missing_context_and_other_roles_are_denied(self):
        contexts = [
            {}, {"PARAM_func": probe.FUNCTION},
            dict(CONTEXT, AUTH_LEVEL="16"), dict(CONTEXT, AUTH_LEVEL="29"),
            dict(CONTEXT, AUTH_LEVEL="24"), dict(CONTEXT, AUTH_USER="ordinary-user"),
            dict(CONTEXT, PARAM_func="file.edit"), dict(CONTEXT, AUTH_LEVEL="30 "),
        ]
        for context in contexts:
            with self.subTest(context=context):
                document = probe.response(context)
                self.assertIsNotNone(document.find("error"))
                self.assertIsNone(document.find("metadata"))

    def test_request_fields_and_headers_cannot_impersonate_root(self):
        environment = {
            "PARAM_func": probe.FUNCTION,
            "AUTH_USER": "ordinary-user", "AUTH_LEVEL": "16",
            "PARAM_AUTH_USER": "root", "PARAM_AUTH_LEVEL": "30",
            "HTTP_AUTH_USER": "root", "HTTP_AUTH_LEVEL": "30",
            "PARAM_user": "root", "PARAM_su": "root",
        }
        self.assertIsNotNone(probe.response(environment).find("error"))

    def test_values_not_used_by_probe_are_not_reflected(self):
        environment = dict(CONTEXT, PARAM_fdata="private-content", HTTP_AUTHORIZATION="private-token")
        environment["PARAM_path"] = "/private-file.php"
        output = ET.tostring(probe.response(environment), encoding="unicode")
        self.assertNotIn("private-", output)

    def test_entry_point_ignores_untrusted_stdin_and_user_site_python(self):
        with tempfile.TemporaryDirectory() as directory:
            # An inherited PYTHONPATH must not execute an attacker's sitecustomize.
            Path(directory, "sitecustomize.py").write_text(
                "raise RuntimeError('PRIVATE_STARTUP_EXECUTED')\n", encoding="utf-8"
            )
            environment = dict(os.environ, **CONTEXT)
            environment["PYTHONPATH"] = directory
            result = subprocess.run(
                [sys.executable, "-I", "-B", str(LAB / "ismonaco_phase0.py")],
                input=b'<!DOCTYPE doc [<!ENTITY x "private-content">]><doc>&x;</doc>',
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
                cwd=directory, timeout=3,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(ET.fromstring(result.stdout).find("error"))
        self.assertNotIn(b"private-content", result.stdout)
        self.assertEqual(result.stderr, b"")

    def test_plugin_does_not_hook_or_replace_existing_file_functions(self):
        module = ET.parse(str(LAB / "ispmgr_mod_ismonaco_phase0.xml")).getroot()
        self.assertEqual(module.find("mainmenu").get("level"), "30")
        functions = [element.get("name") for element in module.findall("handler/func")]
        self.assertEqual(functions, [probe.FUNCTION])
        self.assertEqual(module.findall("handler/event"), [])
        self.assertEqual(module.findall("metadata"), [])

    def test_wrapper_has_fixed_target_and_only_forwards_native_context(self):
        wrapper = (LAB / "ismonaco_phase0.sh").read_text()
        syntax = subprocess.run(
            ["/bin/sh", "-n"], input=wrapper.encode(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        # Replace just the exec invocation for the test. POSIX special builtins
        # may take precedence over shell functions named "exec".
        self.assertEqual(wrapper.count("\nexec "), 1)
        script = "capture_arguments() { printf '%s\\n' \"$@\"; }\n" + wrapper.replace(
            "\nexec ", "\ncapture_arguments ", 1,
        )
        environment = dict(CONTEXT, PARAM_path="private-path", HTTP_AUTH_USER="fake-root")
        environment["AUTH_USER"] = "$(must-not-execute)"
        capture = subprocess.run(
            ["/bin/sh", "-c", script], env=environment,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3,
        )
        arguments = capture.stdout.decode().splitlines()
        self.assertEqual(capture.returncode, 0, capture.stderr)
        self.assertEqual(arguments[:2], ["/usr/bin/env", "-i"])
        self.assertIn("AUTH_USER=$(must-not-execute)", arguments)
        self.assertEqual(arguments[-4:], [
            "/usr/bin/python3", "-I", "-B", "/usr/local/mgr5/addon/ismonaco_phase0.py",
        ])
        self.assertFalse(any("private-path" in value or "fake-root" in value for value in arguments))


if __name__ == "__main__":
    unittest.main()
