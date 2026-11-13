import importlib.util
import json
import os
from pathlib import Path
import tempfile
import shlex
import subprocess
import sys
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('editor_backend', str(ROOT / 'integration/editor/ismonaco_editor.py'))
backend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backend)
CONTEXT = {'PARAM_func': 'file.edit', 'AUTH_USER': 'root', 'AUTH_LEVEL': '30'}


def native():
    return b'''<doc func="file.edit"><metadata name="file.edit" type="form" mgr="core"><form>
      <field name="fdata"><textarea name="fdata" editor="yes"/></field></form>
      <buttons><button name="apply" type="ok"/><button name="ok" type="ok"/><button name="cancel" type="cancel"/></buttons></metadata>
      <fdata>&lt;?php echo 'PRIVATE_CONTENT';</fdata></doc>'''


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.anchor = Path(self.temp.name)
        self.config = self.anchor / 'defaults.json'
        self.config.write_text(json.dumps(backend.DEFAULTS)); self.config.chmod(0o600)
        self.store = backend.ConfigStore(self.config, os.getuid(), os.getgid(), self.anchor)

    def test_default_payload_matches_source_and_root_form_get_does_not_write(self):
        self.assertEqual(json.loads((ROOT / 'integration/editor/defaults.json').read_text()), backend.DEFAULTS)
        before = self.config.read_bytes()
        response = backend.settings_response(CONTEXT, self.store)
        self.assertIsNone(response.find('error'))
        self.assertEqual(response.find('theme').text, 'dark')
        self.assertEqual(response.find('wrap').text, 'on')
        self.assertEqual(response.find('height').text, '760')
        self.assertEqual(self.config.read_bytes(), before)

    def test_shell_wrapper_preserves_each_allowed_parameter_and_drops_other_environment(self):
        probe = self.anchor / 'probe.py'
        probe.write_text('import json, os; print(json.dumps(dict(os.environ)))')
        script = (ROOT / 'integration/editor/ismonaco_editor.sh').read_text()
        script = script.replace('/usr/bin/python3', shlex.quote(sys.executable)).replace(
            '/usr/local/mgr5/addon/ismonaco_0_2_5.py', shlex.quote(str(probe)))
        env = dict(CONTEXT, PARAM_lang='tr', PARAM_sok='ok', PARAM_theme='dark; echo DO_NOT_EXECUTE',
                   PARAM_fdata='PRIVATE_CONTENT', PRIVATE_TOKEN='PRIVATE_TOKEN')
        result = subprocess.run(['/bin/sh'], input=script.encode(), env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        values = json.loads(result.stdout.decode())
        for name in ('AUTH_USER', 'AUTH_LEVEL', 'PARAM_func', 'PARAM_lang', 'PARAM_sok', 'PARAM_theme'):
            self.assertEqual(values[name], env[name])
        self.assertNotIn('PARAM_fdata', values)
        self.assertNotIn('PRIVATE_TOKEN', values)
        self.assertEqual(result.stderr, b'')

    def test_settings_response_contains_the_complete_form_and_messages(self):
        response = backend.settings_response(dict(CONTEXT, PARAM_lang='tr'), self.store)
        metadata = response.find('metadata')
        self.assertEqual(metadata.attrib, {'name': 'ismonaco.settings', 'type': 'form'})
        self.assertEqual([e.get('name') for e in metadata.findall('form/field/select')],
                         ['theme', 'font_size', 'wrap', 'minimap', 'height', 'fullscreen'])
        self.assertEqual([e.get('type') for e in metadata.findall('buttons/button')], ['ok', 'cancel'])
        self.assertEqual(response.find("messages/msg[@name='title']").text, 'Monaco — Sunucu varsayılanları')
        for select in metadata.findall('form/field/select'):
            self.assertIsNotNone(response.find("slist[@name='%s']" % select.get('name')))
            self.assertIsNotNone(response.find(select.get('name')))

    def test_editor_follows_filename_and_encoding_at_the_native_code_position(self):
        doc = ET.fromstring(native())
        form = doc.find('metadata/form')
        for index, name in enumerate(('filename', 'encoding')):
            field = ET.Element('field', {'name': name})
            ET.SubElement(field, 'textdata' if name == 'filename' else 'select', {'name': name})
            form.insert(index, field)
        before = [ET.tostring(child) for child in form]
        result = ET.fromstring(backend.transform(ET.tostring(doc), CONTEXT))
        actual = result.find('metadata/form')
        self.assertEqual([child.get('name') for child in actual], ['filename', 'encoding', backend.FIELD, 'fdata'])
        self.assertEqual([ET.tostring(child) for child in actual if child.get('name') != backend.FIELD], before)
        # A nested code field must keep the containing page and native order.
        page = ET.Element('page', {'name': 'code'})
        field = form.find("field[@name='fdata']")
        form.remove(field); page.append(field); form.append(page)
        result = ET.fromstring(backend.transform(ET.tostring(doc), CONTEXT))
        self.assertEqual([e.get('name') for e in result.find('metadata/form/page')], [backend.FIELD, 'fdata'])
        page.append(ET.fromstring(ET.tostring(field)))
        duplicate = ET.tostring(doc)
        self.assertEqual(backend.transform(duplicate, CONTEXT), duplicate)

    def test_save_updates_only_allowlisted_global_preferences_atomically(self):
        context = dict(CONTEXT, PARAM_sok='ok', PARAM_theme='light', PARAM_font_size='18',
                       PARAM_wrap='off', PARAM_minimap='on', PARAM_height='900', PARAM_fullscreen='off', PARAM_path='/etc/passwd')
        result = backend.settings_response(context, self.store)
        self.assertIsNone(result.find('ok'))
        self.assertIsNotNone(result.find('metadata/form'))
        self.assertEqual(result.findtext('fullscreen'), 'off')
        self.assertEqual(result.find("messages/msg[@name='ismonaco_saved']").text, 'Settings saved.')
        self.assertEqual(self.store.load(), {'version': 2, 'fullscreen': False, 'theme': 'light', 'fontSize': 18, 'wrap': False, 'minimap': True, 'height': 900})
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.anchor.glob('.ismonaco-defaults-*')), [])

    def test_save_returns_renderable_form_for_standalone_and_normal_tabs(self):
        for theme, fullscreen in (('light', 'off'), ('dark', 'on')):
            context = dict(CONTEXT, PARAM_lang='tr', PARAM_sok='ok', PARAM_theme=theme,
                           PARAM_font_size='16', PARAM_wrap='on', PARAM_minimap='off',
                           PARAM_height='900', PARAM_fullscreen=fullscreen)
            response = backend.settings_response(context, self.store)
            self.assertIsNone(response.find('error'))
            self.assertIsNone(response.find('ok'))
            self.assertEqual(response.find('metadata').get('type'), 'form')
            self.assertEqual(len(response.findall('metadata/form/field/select')), 6)
            self.assertIsNotNone(response.find("metadata/form/field/textdata[@name='ismonaco_saved']"))
            self.assertEqual(response.findtext('theme'), theme)
            self.assertEqual(response.findtext('fullscreen'), fullscreen)
            self.assertEqual(response.find("messages/msg[@name='ismonaco_saved']").text, 'Ayarlar kaydedildi.')
            loaded = backend.settings_response(CONTEXT, self.store)
            self.assertEqual(loaded.findtext('theme'), theme)
            self.assertEqual(loaded.findtext('fullscreen'), fullscreen)
            self.assertIsNone(loaded.find("messages/msg[@name='ismonaco_saved']"))

    def test_save_io_error_has_visible_message_and_does_not_report_success(self):
        context = dict(CONTEXT, PARAM_lang='tr', PARAM_sok='ok', PARAM_theme='dark',
                       PARAM_font_size='14', PARAM_wrap='on', PARAM_minimap='on',
                       PARAM_height='760', PARAM_fullscreen='off')
        before = self.config.read_bytes()
        with patch.object(self.store, 'save', side_effect=OSError('PRIVATE_IO_DETAILS')):
            response = backend.settings_response(context, self.store)
        self.assertIn('Ayarlar kaydedilemedi', response.findtext('error/msg'))
        self.assertIsNone(response.find('ok'))
        self.assertIsNone(response.find("messages/msg[@name='ismonaco_saved']"))
        self.assertNotIn('PRIVATE_', ET.tostring(response, encoding='unicode'))
        self.assertEqual(self.config.read_bytes(), before)

    def test_error_after_success_clears_saved_status_and_keeps_a_complete_form(self):
        context = dict(CONTEXT, PARAM_lang='tr', PARAM_sok='ok', PARAM_theme='light',
                       PARAM_font_size='16', PARAM_wrap='on', PARAM_minimap='on',
                       PARAM_height='900', PARAM_fullscreen='off')
        success = backend.settings_response(context, self.store)
        self.assertIsNotNone(success.find("messages/msg[@name='ismonaco_saved']"))
        before = self.config.read_bytes()
        error = backend.settings_response(dict(context, PARAM_theme='PRIVATE_INVALID'), self.store)
        self.assertEqual(len(error.findall('metadata/form/field/select')), 6)
        self.assertTrue(error.findtext('error/msg'))
        self.assertIsNone(error.find("messages/msg[@name='ismonaco_saved']"))
        self.assertIsNone(error.find("metadata/form/field/textdata[@name='ismonaco_saved']"))
        self.assertEqual(error.findtext('theme'), 'light')
        self.assertEqual(self.config.read_bytes(), before)

    def test_normal_admin_and_spoofed_root_context_cannot_read_or_write_settings(self):
        before = self.config.read_bytes()
        for context in ({}, dict(CONTEXT, AUTH_LEVEL='16'), dict(CONTEXT, AUTH_USER='other'),
                        dict(CONTEXT, AUTH_LEVEL='29'), {'PARAM_AUTH_USER': 'root', 'PARAM_AUTH_LEVEL': '30'}):
            result = backend.settings_response(dict(context, PARAM_sok='ok'), self.store)
            self.assertEqual(result.find('error').get('type'), 'access')
            self.assertEqual(result.findall('slist'), [])
        self.assertEqual(self.config.read_bytes(), before)

    def test_invalid_settings_never_mutate_or_echo_input(self):
        good = dict(CONTEXT, PARAM_sok='ok', PARAM_theme='dark', PARAM_font_size='14',
                    PARAM_wrap='on', PARAM_minimap='on', PARAM_height='760', PARAM_fullscreen='on')
        before = self.config.read_bytes()
        for change in ({'PARAM_theme': 'PRIVATE_SECRET'}, {'PARAM_height': '999999'},
                       {'PARAM_font_size': '14;PRIVATE_CODE'}, {'PARAM_wrap': 'true'}, {'PARAM_minimap': ''}, {'PARAM_fullscreen': 'PRIVATE_SECRET'}):
            result = backend.settings_response(dict(good, **change), self.store)
            self.assertIsNotNone(result.find('error'))
            self.assertTrue(result.findtext('error/msg'))
            self.assertNotIn('PRIVATE_', ET.tostring(result, encoding='unicode'))
        self.assertEqual(self.config.read_bytes(), before)

    def test_unsafe_file_directory_symlink_fifo_and_oversize_are_rejected(self):
        self.config.chmod(0o666)
        with self.assertRaises(backend.ConfigError): self.store.load()
        self.config.chmod(0o600)
        self.config.unlink(); self.config.symlink_to(self.anchor / 'missing')
        with self.assertRaises(OSError): self.store.load()
        self.config.unlink(); os.mkfifo(str(self.config), 0o600)
        with self.assertRaises(backend.ConfigError): self.store.load()
        self.config.unlink(); self.config.write_bytes(b'x' * 2049); self.config.chmod(0o600)
        with self.assertRaises(backend.ConfigError): self.store.load()
        self.anchor.chmod(0o777)
        try:
            with self.assertRaises(backend.ConfigError): self.store.load()
        finally: self.anchor.chmod(0o700)

    def test_frame_inherits_server_defaults_for_every_role_without_credentials_or_file_text(self):
        changed = dict(backend.DEFAULTS, theme='light', height=900, minimap=False)
        self.store.save(changed)
        for level in ('30', '29', '24', '16'):
            user = 'root' if level == '30' else 'test-user'
            with patch.object(backend, 'appearance', return_value=self.store.load()):
                doc = ET.fromstring(backend.transform(native(), dict(CONTEXT, AUTH_USER=user, AUTH_LEVEL=level)))
            url = doc.find(backend.FIELD).text
            boot = json.loads(parse_qs(urlsplit(url).fragment)['boot'][0])
            self.assertEqual(boot['preferences'], changed)
            self.assertEqual(boot['saveButtons'], ['apply', 'ok'])
            self.assertEqual(boot['cancelButtons'], ['cancel'])
            self.assertEqual(boot['canConfigure'], level == '30')
            self.assertNotIn('PRIVATE_', url); self.assertNotIn('test-user', url)
            self.assertEqual(doc.find('metadata/form/field/frame').get('height'), '900px')
            self.assertEqual(doc.find('fdata').text, "<?php echo 'PRIVATE_CONTENT';")

    def test_native_apply_setvalues_is_guarded_and_only_unique_ok_can_close(self):
        doc = ET.fromstring(native())
        doc.find("metadata/buttons/button[@name='apply']").set('type', 'setvalues')
        def boot():
            out = ET.fromstring(backend.transform(ET.tostring(doc), CONTEXT))
            return json.loads(parse_qs(urlsplit(out.findtext(backend.FIELD)).fragment)['boot'][0])
        value = boot()
        self.assertIn('apply', value['saveButtons'])
        self.assertEqual(value['saveAndCloseButton'], 'ok')
        duplicate = ET.SubElement(doc.find('metadata/buttons'), 'button', {'name':'ok','type':'ok'})
        self.assertIsNone(boot()['saveAndCloseButton'])
        doc.find('metadata/buttons').remove(duplicate)
        doc.find("metadata/buttons/button[@name='ok']").set('type', 'cancel')
        self.assertIsNone(boot()['saveAndCloseButton'])

    def test_corrupt_display_config_falls_back_without_widening_file_access(self):
        self.config.write_text('{"PRIVATE":"invalid"}')
        self.assertEqual(backend.appearance(self.store), backend.DEFAULTS)
        data = b'<doc func="file.edit"><error type="access"/></doc>'
        self.assertEqual(backend.transform(data, CONTEXT), data)

    def test_registration_declares_only_root_settings_and_existing_native_after_event(self):
        xml = ET.parse(str(ROOT / 'integration/editor/ispmgr_mod_ismonaco_preview.xml')).getroot()
        self.assertEqual(xml.find('mainmenu').get('level'), '30')
        self.assertEqual([e.get('name') for e in xml.findall('handler/func')], ['ismonaco.settings'])
        self.assertEqual([e.attrib for e in xml.findall('handler/event')], [{'name': 'file.edit', 'after': 'yes'}])
        names = [e.get('name') for e in xml.findall("metadata/form/field/select")]
        self.assertEqual(set(names), {'theme', 'font_size', 'wrap', 'minimap', 'height', 'fullscreen'})


if __name__ == '__main__': unittest.main()
