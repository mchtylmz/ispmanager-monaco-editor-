"""Synthetic native contracts, not real ISPmanager browser evidence."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("preview", str(ROOT / "integration/preview/ismonaco_preview.py"))
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)
CONTEXT = {"PARAM_func": "file.edit", "AUTH_USER": "root", "AUTH_LEVEL": "30"}


def native(content="<?php echo 'İstanbul';\r\n", **attributes):
    root = ET.fromstring('''<doc func="file.edit"><tparams><elid>example.php</elid></tparams>
      <metadata name="file.edit" type="form"><form><field name="encoding"><select name="encoding"/></field>
      <field name="fdata"><textarea name="fdata" editor="yes"/></field></form>
      <buttons><button name="ok" type="ok"/></buttons></metadata><messages><msg name="title">Edit</msg></messages>
      <encoding>UTF-8</encoding><fdata/></doc>''')
    root.set("func", attributes.get("func", "file.edit"))
    root.find("fdata").text = content
    return ET.tostring(root, encoding="utf-8")


class PreviewTests(unittest.TestCase):
    def test_serialization_uses_python36_supported_tostring_arguments(self):
        original = ET.tostring
        def python36_tostring(element, encoding='us-ascii', method='xml', *, short_empty_elements=True):
            return original(element, encoding=encoding, method=method,
                            short_empty_elements=short_empty_elements)
        data = native()
        with patch.object(preview.ET, 'tostring', side_effect=python36_tostring):
            output = preview.transform(data, CONTEXT)
        self.assertTrue(output.startswith(b'<?xml version="1.0" encoding="utf-8"?>'))
        self.assertIsNotNone(ET.fromstring(output).find(preview.FIELD))

    def test_root_admin_and_normal_users_get_same_preview_without_identity_reflection(self):
        for level in ("30", "29", "24", "16"):
            context = dict(CONTEXT, AUTH_USER="native-user", AUTH_LEVEL=level, PARAM_su="root")
            data = native()
            output = preview.transform(data, context)
            document = ET.fromstring(output)
            self.assertIsNotNone(document.find(preview.FIELD))
            self.assertNotIn(b"native-user", output)
            self.assertEqual(document.find("fdata").text, ET.fromstring(data).find("fdata").text)
            # Removing only the two added elements recovers all native XML values/attributes.
            document.remove(document.find(preview.FIELD))
            form = document.find("metadata/form")
            form.remove(form.find("field[@name='ismonaco_preview']"))
            self.assertEqual(ET.tostring(document), ET.tostring(ET.fromstring(data)))

    def test_denied_missing_or_spoofed_context_does_not_transform(self):
        for context in ({}, dict(CONTEXT, AUTH_USER=""), dict(CONTEXT, AUTH_LEVEL="9"),
                        {"PARAM_func": "file.edit", "PARAM_AUTH_USER": "root", "PARAM_AUTH_LEVEL": "30"},
                        dict(CONTEXT, PARAM_func="file.download")):
            self.assertEqual(preview.transform(native(), context), native())

    def test_error_submission_unknown_contract_and_repeated_hook_passthrough(self):
        unknown = ET.fromstring(native())
        unknown.find("metadata/form/field/textarea").set("name", "unknown")
        cases = [b'<doc func="file.edit"><error type="access"/></doc>',
                 b'<doc func="file.edit"><ok/></doc>', b'<doc/>',
                 native().replace(b'<tparams>', b'<tparams><sok>ok</sok>'),
                 ET.tostring(unknown, encoding="utf-8"),
                 native(func="file"), preview.transform(native(), CONTEXT)]
        for data in cases:
            self.assertEqual(preview.transform(data, CONTEXT), data)

    def test_dtd_utf16_malformed_and_oversized_input_passthrough(self):
        cases = [b'<!DOCTYPE doc [<!ENTITY e SYSTEM "file:///etc/passwd">]><doc>&e;</doc>',
                 native().decode().encode("utf-16"), b'<doc><bad>', b'x' * (preview.MAX_XML_BYTES + 1),
                 native("x" * (preview.MAX_CONTENT_BYTES + 1))]
        for data in cases:
            self.assertEqual(preview.transform(data, CONTEXT), data)

    def test_native_frame_contains_only_fixed_static_url_and_nonsecret_nonce(self):
        content = "PRIVATE_CONTENT </script><script>parent.PWNED=1</script>"
        document = ET.fromstring(preview.transform(native(content), CONTEXT))
        frame = document.find("metadata/form/field/frame")
        self.assertEqual(frame.attrib, {"name": preview.FIELD, "height": "620px"})
        self.assertEqual(document.findall('.//htmldata'), [])
        self.assertEqual(document.find('fdata').text, content)
        self.assertRegex(document.find(preview.FIELD).text,
                         r'^/manimg/ismonaco-preview-0\.1\.2/frame\.html\?v=[0-9a-f]{16}$')
        self.assertNotIn('PRIVATE_', document.find(preview.FIELD).text)
        self.assertNotIn('srcdoc', document.find(preview.FIELD).text)

    def test_reopening_form_changes_frame_url_without_content_or_identity(self):
        with patch.object(preview.os, 'urandom', side_effect=[b'A' * 8, b'B' * 8]):
            first = ET.fromstring(preview.transform(native(), CONTEXT)).find(preview.FIELD).text
            second = ET.fromstring(preview.transform(native(), CONTEXT)).find(preview.FIELD).text
        self.assertNotEqual(first, second)
        self.assertTrue(first.endswith('4141414141414141'))
        self.assertNotIn('root', first)

    def test_unexpected_exception_returns_original_native_response(self):
        data = native()
        with patch.object(preview.os, "urandom", side_effect=RuntimeError("private-error")):
            self.assertEqual(preview.transform(data, CONTEXT), data)

    def test_character_reference_crlf_and_bom_are_preserved_in_native_field(self):
        data = native('\ufeff<?php echo 1;').replace(b'</fdata>', b'&#13;\n&#13;</fdata>')
        expected = ET.fromstring(data).find('fdata').text
        self.assertEqual(ET.fromstring(preview.transform(data, CONTEXT)).find('fdata').text, expected)

    def test_streaming_entry_point_preserves_large_data_and_stderr_is_empty(self):
        data = b'x' * (preview.MAX_XML_BYTES + 131072)
        result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / 'integration/preview/ismonaco_preview.py')],
                                input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=CONTEXT, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, data)
        self.assertEqual(result.stderr, b"")

    def test_only_native_after_event_registered_and_no_new_file_or_save_function(self):
        document = ET.parse(str(ROOT / 'integration/preview/ispmgr_mod_ismonaco_preview.xml')).getroot()
        self.assertEqual(document.findall('.//func'), [])
        self.assertEqual([event.attrib for event in document.findall('.//event')],
                         [{"name": "file.edit", "after": "yes"}])
        self.assertEqual(document.findall('mainmenu'), [])


if __name__ == "__main__":
    unittest.main()
