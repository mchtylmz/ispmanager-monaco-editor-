"""Native file.edit UI adapter and root-only, fixed-path appearance settings.

No site filesystem access, subprocesses or independent site save endpoint.
Python 3.6 compatible for Rocky Linux 8.
"""

import os
import json
from pathlib import Path
import re
import stat
import sys
import tempfile
from urllib.parse import urlencode
import xml.etree.ElementTree as ET


MAX_XML_BYTES = 4 * 1024 * 1024
MAX_CONTENT_BYTES = 512 * 1024
FIELD = "ismonaco_preview"
ASSETS = "/manimg/ismonaco-editor-0.2.5"
SETTINGS_FUNCTION = 'ismonaco.settings'
DEFAULTS_PATH = Path('/usr/local/mgr5/etc/ismonaco-editor/defaults-v2.json')
DEFAULTS = {'version': 2, 'fullscreen': True, 'theme': 'dark', 'fontSize': 14, 'wrap': True, 'minimap': True, 'height': 760}


class ConfigError(Exception):
    pass


def validate_defaults(value):
    if (not isinstance(value, dict) or set(value) != set(DEFAULTS)
            or type(value['version']) is not int or value['version'] != 2
            or value['theme'] not in ('dark', 'light')
            or type(value['fontSize']) is not int or value['fontSize'] not in (12, 14, 16, 18, 20)
            or type(value['fullscreen']) is not bool or type(value['wrap']) is not bool or type(value['minimap']) is not bool
            or type(value['height']) is not int or value['height'] not in (620, 760, 900, 1080)):
        raise ConfigError('INVALID_DEFAULTS')
    return dict(value)


class ConfigStore:
    def __init__(self, path=DEFAULTS_PATH, uid=0, gid=0, anchor=Path('/')):
        # Test injection only. Handler always uses this fixed production path.
        self.path, self.uid, self.gid, self.anchor = Path(path), uid, gid, Path(anchor)

    def check_parents(self):
        current = self.path.parent
        while True:
            info = os.lstat(str(current))
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != self.uid or info.st_mode & 0o022:
                raise ConfigError('UNTRUSTED_CONFIG_DIRECTORY')
            if current == self.anchor:
                break
            if current.parent == current:
                raise ConfigError('INVALID_CONFIG_ANCHOR')
            current = current.parent

    def load(self):
        self.check_parents()
        fd = os.open(str(self.path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != self.uid or info.st_gid != self.gid
                    or stat.S_IMODE(info.st_mode) != 0o600):
                raise ConfigError('UNTRUSTED_CONFIG_FILE')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                data = stream.read(2049)
            if len(data) > 2048:
                raise ConfigError('CONFIG_TOO_LARGE')
            return validate_defaults(json.loads(data.decode('utf-8')))
        finally:
            os.close(fd)

    def save(self, value):
        value = validate_defaults(value)
        self.load()  # Refuse symlinks, foreign files, unsafe modes or corrupt state.
        fd, temporary = tempfile.mkstemp(prefix='.ismonaco-defaults-', dir=str(self.path.parent))
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write((json.dumps(value, sort_keys=True) + '\n').encode('utf-8'))
                os.fchown(stream.fileno(), self.uid, self.gid)
                os.fchmod(stream.fileno(), 0o600)
                stream.flush()
                os.fsync(stream.fileno())
            self.load()
            os.replace(temporary, str(self.path))
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)


def appearance(store=None):
    try:
        return (store or ConfigStore()).load()
    except (ConfigError, OSError, ValueError, UnicodeError):
        return dict(DEFAULTS)


def settings_form(value, language, saved=False):
    root = ET.Element('doc', {'func': SETTINGS_FUNCTION, 'lang': language})
    # External XML handlers return the complete page, including metadata.
    # Static registration alone did not populate the Phoenix form response.
    metadata = ET.SubElement(root, 'metadata', {'name': SETTINGS_FUNCTION, 'type': 'form'})
    form = ET.SubElement(metadata, 'form')
    for name in ('theme', 'font_size', 'wrap', 'minimap', 'height', 'fullscreen'):
        field = ET.SubElement(form, 'field', {'name': name})
        ET.SubElement(field, 'select', {'name': name, 'required': 'yes'})
    if saved:
        status = ET.SubElement(form, 'field', {'name': 'ismonaco_saved', 'noname': 'yes', 'fullwidth': 'yes'})
        ET.SubElement(status, 'textdata', {'name': 'ismonaco_saved', 'type': 'msg'})
    buttons = ET.SubElement(metadata, 'buttons')
    for name in ('ok', 'cancel'):
        ET.SubElement(buttons, 'button', {'name': name, 'type': name})
    messages = ET.SubElement(root, 'messages')
    labels = {'title': 'Monaco — Server defaults', 'theme': 'Theme',
              'font_size': 'Font size', 'wrap': 'Word wrap', 'minimap': 'Minimap',
              'height': 'Editor height', 'fullscreen': 'Open in full screen by default', 'msg_ok': 'Save', 'msg_cancel': 'Close'}
    if language == 'tr':
        labels.update(title='Monaco — Sunucu varsayılanları', theme='Tema',
                      font_size='Yazı boyutu', wrap='Satır kaydır', minimap='Kod haritası',
                      height='Editör yüksekliği', fullscreen='Varsayılan tam ekran', msg_ok='Kaydet', msg_cancel='Kapat')
    if saved:
        labels['ismonaco_saved'] = 'Ayarlar kaydedildi.' if language == 'tr' else 'Settings saved.'
    for name, label in labels.items():
        ET.SubElement(messages, 'msg', {'name': name}).text = label
    choices = {'theme': [('dark', 'Koyu / Dark'), ('light', 'Açık / Light')],
               'font_size': [(str(v), str(v)) for v in (12, 14, 16, 18, 20)],
               'height': [(str(v), str(v) + ' px') for v in (620, 760, 900, 1080)],
               'wrap': [('on', 'Açık / On'), ('off', 'Kapalı / Off')],
               'minimap': [('on', 'Açık / On'), ('off', 'Kapalı / Off')],
               'fullscreen': [('on', 'Evet / Yes'), ('off', 'Hayır / No')]}
    for name, options in choices.items():
        listing = ET.SubElement(root, 'slist', {'name': name})
        for key, label in options:
            ET.SubElement(listing, 'val', {'key': key}).text = label
        current = value['fontSize' if name == 'font_size' else name]
        ET.SubElement(root, name).text = ('on' if current else 'off') if type(current) is bool else str(current)
    return root


def settings_response(context, store=None):
    language = 'tr' if context.get('PARAM_lang') == 'tr' else 'en'
    root = ET.Element('doc', {'func': SETTINGS_FUNCTION, 'lang': language})
    if context.get('AUTH_USER') != 'root' or context.get('AUTH_LEVEL') != '30':
        error = ET.SubElement(root, 'error', {'type': 'access', 'code': '1'})
        ET.SubElement(error, 'msg').text = 'Bu ayarlara yalnızca root erişebilir.' if language == 'tr' else 'Only root can access these settings.'
        return root
    store = store or ConfigStore()
    value = None
    try:
        if context.get('PARAM_sok'):
            value = {'version': 2, 'fullscreen': True, 'theme': context.get('PARAM_theme'),
                     'fontSize': int(context.get('PARAM_font_size', '')),
                     'height': int(context.get('PARAM_height', ''))}
            for name in ('wrap', 'minimap', 'fullscreen'):
                raw = context.get('PARAM_' + name)
                if raw not in ('on', 'off'):
                    raise ConfigError('INVALID_BOOLEAN')
                value[name] = raw == 'on'
            store.save(value)
            saved = True
        else:
            value = store.load()
            saved = False
        return settings_form(value, language, saved)
    except (ConfigError, OSError, ValueError, TypeError, UnicodeError):
        # Keep a usable form and clear any stale success message on failed saves.
        try:
            safe_value = validate_defaults(value)
        except (ConfigError, ValueError, TypeError):
            safe_value = appearance(store)
        root = settings_form(safe_value, language)
        error = ET.SubElement(root, 'error', {'type': 'ismonaco_config', 'code': '1'})
        ET.SubElement(error, 'msg').text = ('Ayarlar kaydedilemedi veya okunamadı. Değerleri ve eklenti yapılandırma izinlerini kontrol edin.'
                                         if language == 'tr' else 'Settings could not be saved or loaded. Check values and plugin configuration permissions.')
    return root



def transform(data, context):
    # Only native identity is considered. Request parameters cannot grant access.
    if (context.get("PARAM_func") != "file.edit"
            or not context.get("AUTH_USER")
            or context.get("AUTH_LEVEL") not in ("16", "24", "29", "30")
            or len(data) > MAX_XML_BYTES):
        return data
    try:
        text = data.decode("utf-8")
        if "\x00" in text or "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            return data
        root = ET.fromstring(text)
        if (root.tag != "doc" or root.get("func") != "file.edit"
                or root.find(".//error") is not None
                or root.find("ok") is not None
                or root.find("tparams/sok") is not None):
            return data
        metadata = root.findall("metadata")
        contents = root.findall("fdata")
        if (len(metadata) != 1 or metadata[0].get("name") != "file.edit"
                or metadata[0].get("type") != "form" or len(contents) != 1
                or len(contents[0]) != 0 or root.find(FIELD) is not None):
            return data
        form = metadata[0].find("form")
        if form is None:
            return data
        native_fields = [child for child in form.iter('field')
                         if child.find("textarea[@name='fdata']") is not None]
        if len(native_fields) != 1:
            return data
        native_field = native_fields[0]
        parent = next((node for node in form.iter() if native_field in list(node)), None)
        if parent is None:
            return data
        content = contents[0].text or ""
        if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
            return data
        # Phoenix ignores htmldata; use its native frame control. The URL has
        # only a public render nonce, never content, identity or a session token.
        preferences = appearance()
        buttons = metadata[0].findall('buttons/button') + form.findall('buttons/button')
        ids = lambda kind: [button.get('name') for button in buttons
                            if button.get('type') in kind
                            and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,63}', button.get('name', ''))]
        boot = {'version': 1, 'preferences': preferences,
                'saveButtons': ids(('ok', 'next', 'submit', 'apply')) + [b.get('name') for b in buttons if b.get('name') == 'apply' and b.get('type') == 'setvalues'],
                'saveAndCloseButton': 'ok' if len([b for b in buttons if b.get('name') == 'ok' and b.get('type') == 'ok']) == 1 else None,
                'cancelButtons': ids(('cancel',)),
                'canConfigure': context.get('AUTH_USER') == 'root' and context.get('AUTH_LEVEL') == '30'}
        frame_url = ASSETS + "/frame.html?v=" + os.urandom(8).hex() + '#' + urlencode({'boot': json.dumps(boot, separators=(',', ':'))})
        field = ET.Element("field", {"name": FIELD, "noname": "yes", "fullwidth": "yes"})
        ET.SubElement(field, "frame", {"name": FIELD, "height": str(preferences['height']) + 'px'})
        # Native fields, submit buttons, function, hidden fields and fdata stay intact.
        # Keep filename/encoding and all native fields in their original order.
        # Monaco occupies the native code field's position, including nested forms.
        parent.insert(list(parent).index(native_field), field)
        ET.SubElement(root, FIELD).text = frame_url
        # tostring(xml_declaration=...) was added in Python 3.8. The server
        # baseline is 3.6; prepend the fixed declaration without that keyword.
        serialized = ET.tostring(root, encoding="utf-8").replace(b"\r", b"&#13;")
        return b'<?xml version="1.0" encoding="utf-8"?>\n' + serialized
    except Exception:
        # Fail open for presentation only; native access/save behavior is retained.
        return data


def main():
    if os.environ.get('PARAM_func') == SETTINGS_FUNCTION:
        root = settings_response(os.environ)
        sys.stdout.buffer.write(b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='utf-8'))
        return 0
    data = sys.stdin.buffer.read(MAX_XML_BYTES + 1)
    if len(data) > MAX_XML_BYTES:
        # Keep memory bounded and preserve large native responses without parsing.
        sys.stdout.buffer.write(data)
        while True:
            block = sys.stdin.buffer.read(65536)
            if not block:
                break
            sys.stdout.buffer.write(block)
    else:
        sys.stdout.buffer.write(transform(data, os.environ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
