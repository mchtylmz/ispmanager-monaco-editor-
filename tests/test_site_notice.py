import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

PROJECT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(PROJECT / path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


notice = load('notice', 'integration/site-notice/site_notice.py')
editor = load('editor', 'integration/editor/ismonaco_editor.py')
CONTEXT = dict(PARAM_func='site.edit', AUTH_USER='root', AUTH_LEVEL='30', PARAM_lang='tr')


def native(edit=False):
    root = ET.fromstring(b'<doc func="site.edit"><metadata name="site.edit" type="form"><form><page name="mainsettings"><field name="site_ipaddrs"><select name="site_ipaddrs"/></field></page><page name="php"><field name="php_mode"><select name="php_mode"/></field></page><buttons><button name="ok" type="ok"/></buttons></form></metadata><site_ipaddrs>TEST_IP_UNCHANGED</site_ipaddrs></doc>')
    if edit:
        ET.SubElement(root, 'elid').text = 'example.test'
    return ET.tostring(root)


class SiteNoticeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.anchor = Path(self.temp.name)
        self.path = self.anchor / 'notice.json'
        self.path.write_text(json.dumps(notice.DEFAULTS)); self.path.chmod(0o600)
        self.store = notice.NoticeStore(self.path, os.getuid(), os.getgid(), self.anchor)
        self.appearance_path = self.anchor / 'appearance.json'
        self.appearance_path.write_text(json.dumps(editor.DEFAULTS)); self.appearance_path.chmod(0o600)
        self.appearance = editor.ConfigStore(self.appearance_path, os.getuid(), os.getgid(), self.anchor)
        self.patcher = patch.object(notice, 'editor_module', return_value=editor)
        self.patcher.start(); self.addCleanup(self.patcher.stop)

    def settings(self, extra=None, **identity):
        context = dict(CONTEXT, PARAM_func='ismonaco.settings', **identity)
        context.update(extra or {})
        return notice.settings_response(context, self.appearance, self.store)

    def values(self, **changes):
        value = dict(PARAM_sok='ok', PARAM_theme='dark', PARAM_font_size='14', PARAM_height='760',
                     PARAM_wrap='on', PARAM_minimap='on', PARAM_fullscreen='on',
                     PARAM_site_notice_style='warning', PARAM_site_notice_text='IP A: Web\r\nIP B: Mail\nIP C: Test')
        value.update(changes)
        return value

    def test_native_create_edit_and_roles_preserve_all_original_controls_and_values(self):
        self.store.save(dict(notice.DEFAULTS, text='IP A\nIP B', style='warning'))
        for edit in (False, True):
            for user, level in [('root','30'),('admin','29'),('reseller','24'),('test-user','16')]:
                before = ET.fromstring(native(edit))
                after = ET.fromstring(notice.transform(native(edit), dict(CONTEXT, AUTH_USER=user, AUTH_LEVEL=level), self.store))
                page = after.find("metadata/form/page[@name='mainsettings']")
                self.assertEqual(page[0].get('name'), notice.FIELD)
                self.assertEqual(page[0].find('textdata').attrib, {'name': notice.VALUE, 'type':'banner', 'status':'warning', 'html':'yes'})
                self.assertEqual(after.findtext(notice.VALUE), 'IP A<br>IP B')
                page.remove(page[0]); after.remove(after.find(notice.VALUE))
                self.assertEqual(ET.tostring(after), ET.tostring(before))

    def test_empty_disables_duplicate_and_corrupt_store_do_not_change_native_form(self):
        data = native()
        self.assertEqual(notice.transform(data, CONTEXT, self.store), data)
        self.store.save(dict(notice.DEFAULTS, text='  \n\t'))
        self.assertEqual(notice.transform(data, CONTEXT, self.store), data)
        self.store.save(dict(notice.DEFAULTS, text='IP note'))
        once = notice.transform(data, CONTEXT, self.store)
        self.assertEqual(notice.transform(once, CONTEXT, self.store), once)
        self.path.write_text('invalid JSON')
        self.assertEqual(notice.transform(data, CONTEXT, self.store), data)

    def test_html_and_template_text_is_escaped_newlines_are_only_generated_markup(self):
        text = '<script>parent.PWNED=true</script>\n<img src=x onerror="alert(1)"> & {{7*7}}'
        self.store.save(dict(notice.DEFAULTS, text=text))
        after = ET.fromstring(notice.transform(native(), CONTEXT, self.store))
        html = after.findtext(notice.VALUE)
        self.assertNotIn('<script', html); self.assertNotIn('<img', html)
        self.assertIn('&lt;script&gt;', html); self.assertEqual(html.count('<br>'), 1)

    def test_unknown_denied_submit_errors_success_and_malformed_responses_pass_through(self):
        self.store.save(dict(notice.DEFAULTS, text='note'))
        for extra in [dict(PARAM_func='webdomain.edit'), dict(AUTH_LEVEL='15'), dict(AUTH_USER='')]:
            data = native(); self.assertEqual(notice.transform(data, dict(CONTEXT, **extra), self.store), data)
        cases = [b'<doc', b'<!DOCTYPE doc><doc func="site.edit"/>', b'<doc func="site.edit"><ok/></doc>']
        for node in ('error', 'ok', 'tparams'):
            doc = ET.fromstring(native()); child = ET.SubElement(doc, node)
            if node == 'tparams': ET.SubElement(child, 'sok').text = 'ok'
            cases.append(ET.tostring(doc))
        for data in cases:
            self.assertEqual(notice.transform(data, CONTEXT, self.store), data)
        doc = ET.fromstring(native()); doc.find('metadata/form/page').set('name', 'unknown')
        data = ET.tostring(doc); self.assertEqual(notice.transform(data, CONTEXT, self.store), data)

    def test_settings_load_save_reload_clear_and_notice_only_does_not_rewrite_editor_defaults(self):
        before = (self.appearance_path.read_bytes(), self.appearance_path.stat().st_ino, self.appearance_path.stat().st_mtime_ns)
        form = self.settings()
        self.assertEqual(form.find("metadata/form/field/textarea").get('rows'), '5')
        self.assertEqual(len(form.findall('metadata/form/field/select')), 7)
        saved = self.settings(self.values())
        self.assertIsNone(saved.find('error')); self.assertIsNone(saved.find('ok'))
        self.assertEqual(saved.findtext('site_notice_text'), 'IP A: Web\nIP B: Mail\nIP C: Test')
        self.assertEqual(self.settings().findtext('site_notice_style'), 'warning')
        self.assertEqual((self.appearance_path.read_bytes(), self.appearance_path.stat().st_ino, self.appearance_path.stat().st_mtime_ns), before)
        self.settings(self.values(PARAM_site_notice_text=''))
        self.assertEqual(notice.transform(native(), CONTEXT, self.store), native())

    def test_invalid_text_or_editor_values_rejected_before_either_store_writes(self):
        before = self.path.read_bytes(), self.appearance_path.read_bytes()
        for change in [dict(PARAM_site_notice_style='danger'), dict(PARAM_site_notice_text='x'*4097),
                       dict(PARAM_site_notice_text='a\x00b'), dict(PARAM_site_notice_text='ş'*2049),
                       dict(PARAM_height='999999'), dict(PARAM_wrap='true')]:
            response = self.settings(self.values(**change))
            self.assertTrue(response.findtext('error/msg'))
            self.assertIsNotNone(response.find('metadata/form/field/textarea'))
            self.assertIsNone(response.find("messages/msg[@name='ismonaco_saved']"))
            self.assertEqual((self.path.read_bytes(), self.appearance_path.read_bytes()), before)

    def test_nonroot_cannot_read_or_change_notice_and_failed_io_does_not_claim_success(self):
        self.store.save(dict(notice.DEFAULTS, text='ADMIN_NOTE'))
        before = self.path.read_bytes()
        for identity in [dict(AUTH_USER='test-user', AUTH_LEVEL='16'), dict(AUTH_USER='root', AUTH_LEVEL='29')]:
            response = self.settings(self.values(), **identity)
            self.assertIsNotNone(response.find('error')); self.assertIsNone(response.find('metadata'))
            self.assertNotIn('ADMIN_NOTE', ET.tostring(response, encoding='unicode'))
            self.assertEqual(self.path.read_bytes(), before)
        with patch.object(self.store, 'save', side_effect=OSError('disk full')):
            response = self.settings(self.values(PARAM_theme='light'))
        self.assertTrue(response.findtext('error/msg'))
        self.assertEqual(response.findtext('theme'), 'light')  # Persisted state, never a false all-or-nothing claim.
        self.assertEqual(response.findtext('site_notice_text'), 'ADMIN_NOTE')
        self.assertIsNone(response.find("messages/msg[@name='ismonaco_saved']"))

    def test_storage_bounds_unsafe_modes_fifo_symlink_and_missing_file_fail_safely(self):
        self.store.save(dict(notice.DEFAULTS, text='ş'*2048))
        self.assertEqual(self.store.load()['text'], 'ş'*2048)
        self.path.chmod(0o666)
        with self.assertRaises(notice.NoticeError): self.store.load()
        self.path.unlink(); os.mkfifo(str(self.path), 0o600)
        with self.assertRaises(notice.NoticeError): self.store.load()
        self.path.unlink(); self.path.symlink_to(self.anchor / 'missing')
        with self.assertRaises(OSError): self.store.save(notice.DEFAULTS)
        self.assertEqual(notice.transform(native(), CONTEXT, self.store), native())
        self.path.unlink(); self.path.write_bytes(b'x'*32769); self.path.chmod(0o600)
        with self.assertRaises(notice.NoticeError): self.store.load()


if __name__ == '__main__':
    unittest.main()
