"""Check the exact copyable metadata filter without calling a panel or SSH."""

import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import unittest


DOC = Path(__file__).resolve().parents[1] / "docs" / "FAZ_0.md"
COMMAND = re.search(
    r"<!-- phase0-panel-metadata-command -->\s*```sh\n([^\n]+)\n```",
    DOC.read_text(encoding="utf-8"),
).group(1)
PARTS = shlex.split(COMMAND)
FILTER = PARTS[PARTS.index("-c") + 1]


class MetadataCommandTests(unittest.TestCase):
    def run_filter(self, data):
        return subprocess.run(
            [sys.executable, "-I", "-B", "-c", FILTER], input=data,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3,
        )

    def test_filter_does_not_share_rows_secrets_or_metadata_text(self):
        # Synthetic structure, not a captured ISPmanager compatibility fixture.
        xml = b'''<doc><metadata name="file" type="list" key="dname" mgr="ispmgr">
          <toolbar><toolgrp name="edit"><toolbtn name="edit" func="file.edit"
            default="yes" hint="private-hint"/></toolgrp></toolbar>
          <description>private-description</description></metadata>
          <auth>private-token</auth><elem><dname>private-file.php</dname></elem>
          <fdata>private-content</fdata></doc>'''
        result = self.run_filter(xml)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(b"private-", result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["metadata"]["key"], "dname")
        self.assertEqual(summary["buttons"], [
            {"name": "edit", "func": "file.edit", "default": "yes"},
        ])

    def test_missing_metadata_is_not_reported_as_success(self):
        result = self.run_filter(b"<doc><error>private-message</error></doc>")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"METADATA_NOT_FOUND", result.stderr)
        self.assertNotIn(b"private-message", result.stderr)

    def test_dtd_and_entities_are_rejected_before_parsing(self):
        xml = b'<!DOCTYPE doc [<!ENTITY secret "private-content">]><doc><metadata/></doc>'
        result = self.run_filter(xml)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"XML_REJECTED", result.stderr)
        self.assertEqual(result.stdout, b"")

    def test_utf16_cannot_bypass_declaration_rejection(self):
        xml = '<!DOCTYPE doc [<!ENTITY secret "private-content">]><doc><metadata/></doc>'
        result = self.run_filter(xml.encode("utf-16"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"XML_REJECTED", result.stderr)
        self.assertEqual(result.stdout, b"")

    def test_oversized_input_is_rejected(self):
        result = self.run_filter(b"x" * 1048577)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"XML_REJECTED", result.stderr)
        self.assertEqual(result.stdout, b"")

    def test_malformed_xml_does_not_echo_input(self):
        result = self.run_filter(b"<doc><metadata>private-content")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")
        self.assertNotIn(b"private-content", result.stderr)


if __name__ == "__main__":
    unittest.main()
