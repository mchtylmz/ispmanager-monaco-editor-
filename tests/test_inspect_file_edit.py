"""Privacy/shape tests for the standalone stdin filter; no panel is called."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


TOOL = Path(__file__).resolve().parents[1] / 'tools/inspect_file_edit.py'
SPEC = importlib.util.spec_from_file_location('inspect_file_edit', str(TOOL))
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


class InspectorTests(unittest.TestCase):
    def test_metadata_kept_but_content_paths_sessions_messages_and_defaults_omitted(self):
        data = b'''<doc func="file.edit" auth="PRIVATE_TOKEN"><tparams><elid>PRIVATE_PATH</elid></tparams>
        <metadata name="file.edit" type="form"><form><field name="fdata"><textarea name="fdata" editor="yes" value="PRIVATE_DEFAULT"/></field></form></metadata>
        <fdata>PRIVATE_CONTENT</fdata><messages><msg name="title">PRIVATE_TITLE</msg></messages>
        <encoding>PRIVATE_ENCODING</encoding><auth>PRIVATE_AUTH</auth></doc>'''
        result = tool.summarize(data)
        self.assertEqual(result['status'], 'OK')
        self.assertNotIn('PRIVATE_', json.dumps(result))
        self.assertEqual(result['controls'][1], {'tag': 'textarea', 'name': 'fdata', 'editor': 'yes'})
        self.assertTrue(result['fdata_within_preview_limit'])
        self.assertFalse(result['monaco_data_present'])

    def test_empty_sok_and_missing_metadata_names_are_visible_without_values(self):
        result = tool.summarize(b'<doc><tparams><sok/></tparams><metadata type="form"><form/></metadata><fdata/></doc>')
        self.assertEqual(result['metadata'], [{'type': 'form'}])
        self.assertIsNone(result['function'])
        self.assertTrue(result['sok_present'])
        self.assertFalse(result['sok_nonempty'])

    def test_preview_marker_and_nontextarea_control_are_distinguished(self):
        result = tool.summarize(b'<doc func="file.edit"><metadata name="file.edit" type="form"><form><field name="ismonaco_preview"><htmldata name="ismonaco_preview"/></field><field name="fdata"><input name="fdata" type="editor"/></field></form></metadata><ismonaco_preview>PRIVATE_HTML</ismonaco_preview><fdata>x</fdata></doc>')
        self.assertTrue(result['monaco_data_present'])
        self.assertTrue(result['monaco_field_present'])
        self.assertEqual(result['controls'][-1]['type'], 'editor')
        self.assertNotIn('PRIVATE_HTML', json.dumps(result))

    def test_errors_bad_xml_dtd_and_utf16_never_echo_private_payload(self):
        for data in (b'<doc><error>PRIVATE_ERROR</error></doc>', b'<bad PRIVATE_PAYLOAD',
                     b'<!DOCTYPE doc [<!ENTITY secret "PRIVATE_VALUE">]><doc>&secret;</doc>',
                     '<doc>PRIVATE_TEXT</doc>'.encode('utf-16')):
            result = tool.summarize(data)
            self.assertNotEqual(result['status'], 'OK')
            self.assertNotIn('PRIVATE_', json.dumps(result))

    def test_input_content_and_schema_limits(self):
        self.assertEqual(tool.summarize(b'x' * (tool.MAX_BYTES + 1))['status'], 'XML_TOO_LARGE')
        value = tool.summarize(b'<doc><metadata/><fdata>' + b'x' * 524289 + b'</fdata></doc>')
        self.assertFalse(value['fdata_within_preview_limit'])
        self.assertEqual(tool.summarize(b'<doc><metadata>' + b'<field/>' * 129 + b'</metadata></doc>')['status'], 'METADATA_TOO_LARGE')

    def test_entry_point_reports_only_sanitized_json(self):
        result = subprocess.run([sys.executable, '-I', '-B', str(TOOL)],
                                input=b'<doc><error>PRIVATE_ERROR</error></doc>',
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['status'], 'NATIVE_ERROR')
        self.assertEqual(result.stderr, b'')
        self.assertNotIn(b'PRIVATE_', result.stdout)


if __name__ == '__main__':
    unittest.main()
