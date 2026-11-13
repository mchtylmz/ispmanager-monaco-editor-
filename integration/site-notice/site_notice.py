"""Root-configured notice for native site.edit; no site writes or API calls.

The released editor remains byte-for-byte unchanged. Python 3.6 compatible.
"""

import html
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import xml.etree.ElementTree as ET


SETTINGS_FUNCTION = 'ismonaco.settings'
SITE_FUNCTION = 'site.edit'
FIELD = 'ismonaco_site_notice_field'
VALUE = 'ismonaco_site_notice'
MAX_XML_BYTES = 4 * 1024 * 1024
MAX_TEXT_BYTES = 4096
MAX_CONFIG_BYTES = 32768
NOTICE_PATH = Path('/usr/local/mgr5/etc/ismonaco-editor/site-notice-v1.json')
DEFAULTS = {'version': 1, 'style': 'info', 'text': ''}


class NoticeError(Exception):
    pass


def validate_notice(value):
    if (not isinstance(value, dict) or set(value) != set(DEFAULTS)
            or type(value['version']) is not int or value['version'] != 1
            or value['style'] not in ('info', 'warning') or not isinstance(value['text'], str)):
        raise NoticeError('INVALID_SITE_NOTICE')
    text = value['text'].replace('\r\n', '\n').replace('\r', '\n')
    if (len(text.encode('utf-8')) > MAX_TEXT_BYTES
            or any(ord(c) < 32 and c not in '\n\t' or ord(c) == 127 for c in text)):
        raise NoticeError('INVALID_SITE_NOTICE_TEXT')
    return dict(value, text=text)


class NoticeStore:
    def __init__(self, path=NOTICE_PATH, uid=0, gid=0, anchor=Path('/')):
        self.path, self.uid, self.gid, self.anchor = Path(path), uid, gid, Path(anchor)

    def check_parents(self):
        current = self.path.parent
        while True:
            info = os.lstat(str(current))
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != self.uid or info.st_mode & 0o022:
                raise NoticeError('UNTRUSTED_NOTICE_DIRECTORY')
            if current == self.anchor:
                return
            if current.parent == current:
                raise NoticeError('INVALID_NOTICE_ANCHOR')
            current = current.parent

    def load(self):
        self.check_parents()
        fd = os.open(str(self.path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != self.uid or info.st_gid != self.gid
                    or stat.S_IMODE(info.st_mode) != 0o600):
                raise NoticeError('UNTRUSTED_NOTICE_FILE')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                data = stream.read(MAX_CONFIG_BYTES + 1)
            if len(data) > MAX_CONFIG_BYTES:
                raise NoticeError('NOTICE_CONFIG_TOO_LARGE')
            return validate_notice(json.loads(data.decode('utf-8')))
        finally:
            os.close(fd)

    def save(self, value):
        value = validate_notice(value)
        self.load()
        fd, temporary = tempfile.mkstemp(prefix='.ismonaco-notice-', dir=str(self.path.parent))
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


def editor_module():
    # Fixed, versioned sibling verified by the package; never a request-supplied path.
    path = Path(__file__).with_name('ismonaco_0_2_5.py')
    spec = importlib.util.spec_from_file_location('ismonaco_released_editor', str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def add_settings(root, value, language):
    form = root.find('metadata/form')
    if form is None:
        return root
    field = ET.SubElement(form, 'field', {'name': 'site_notice_style'})
    ET.SubElement(field, 'select', {'name': 'site_notice_style', 'required': 'yes'})
    field = ET.SubElement(form, 'field', {'name': 'site_notice_text', 'fullwidth': 'yes'})
    ET.SubElement(field, 'textarea', {'name': 'site_notice_text', 'rows': '5'})
    labels = {
        'site_notice_style': 'Site notice type',
        'site_notice_text': 'Notice shown when creating or editing a site',
        'hint_site_notice_text': 'Server-wide plain text, up to 4096 UTF-8 bytes. Leave empty to hide. No HTML.',
    }
    if language == 'tr':
        labels.update(site_notice_style='Site uyarısı türü',
                      site_notice_text='Site oluştururken veya düzenlerken gösterilecek uyarı metni',
                      hint_site_notice_text='Sunucu genelinde düz metin; en fazla 4096 UTF-8 byte. Boş bırakılırsa gizlenir. HTML kullanılmaz.')
    messages = root.find('messages')
    for name, text in labels.items():
        ET.SubElement(messages, 'msg', {'name': name}).text = text
    listing = ET.SubElement(root, 'slist', {'name': 'site_notice_style'})
    for key, label in [('info', 'Bilgi / Information'), ('warning', 'Uyarı / Warning')]:
        ET.SubElement(listing, 'val', {'key': key}).text = label
    ET.SubElement(root, 'site_notice_style').text = value['style']
    ET.SubElement(root, 'site_notice_text').text = value['text']
    return root


def settings_response(context, appearance_store=None, notice_store=None):
    editor = editor_module()
    if context.get('AUTH_USER') != 'root' or context.get('AUTH_LEVEL') != '30':
        return editor.settings_response(context, appearance_store)
    language = 'tr' if context.get('PARAM_lang') == 'tr' else 'en'
    appearance_store = appearance_store or editor.ConfigStore()
    notice_store = notice_store or NoticeStore()
    try:
        appearance = appearance_store.load()
        notice = notice_store.load()
        saved = bool(context.get('PARAM_sok'))
        if saved:
            next_notice = validate_notice({'version': 1, 'style': context.get('PARAM_site_notice_style'),
                                           'text': context.get('PARAM_site_notice_text', '')})
            next_appearance = {'version': 2, 'theme': context.get('PARAM_theme'),
                               'fontSize': int(context.get('PARAM_font_size', '')),
                               'height': int(context.get('PARAM_height', ''))}
            for name in ('wrap', 'minimap', 'fullscreen'):
                raw = context.get('PARAM_' + name)
                if raw not in ('on', 'off'):
                    raise NoticeError('INVALID_BOOLEAN')
                next_appearance[name] = raw == 'on'
            next_appearance = editor.validate_defaults(next_appearance)
            # Validate both before writes; each store replaces its own file atomically.
            # Avoid rewriting unchanged editor defaults for a notice-only update.
            if next_appearance != appearance:
                appearance_store.save(next_appearance)
            if next_notice != notice:
                notice_store.save(next_notice)
            appearance, notice = next_appearance, next_notice
        return add_settings(editor.settings_form(appearance, language, saved), notice, language)
    except (NoticeError, editor.ConfigError, OSError, ValueError, TypeError, UnicodeError):
        # Re-read persisted values; never claim success or close a failed form.
        appearance = editor.appearance(appearance_store)
        try:
            notice = notice_store.load()
        except (NoticeError, OSError, ValueError, TypeError, UnicodeError):
            notice = dict(DEFAULTS)
        root = add_settings(editor.settings_form(appearance, language), notice, language)
        error = ET.SubElement(root, 'error', {'type': 'ismonaco_config', 'code': '1'})
        ET.SubElement(error, 'msg').text = (
            'Ayarlar tamamen kaydedilemedi veya okunamadı. Alanları ve eklenti izinlerini kontrol edin; kaydedilen değerler yeniden gösteriliyor.'
            if language == 'tr' else 'Settings could not be fully saved or loaded. Check values and plugin permissions; persisted values are shown.')
        return root


def transform(data, context, store=None):
    if (context.get('PARAM_func') != SITE_FUNCTION or not context.get('AUTH_USER')
            or context.get('AUTH_LEVEL') not in ('16', '24', '29', '30') or len(data) > MAX_XML_BYTES):
        return data
    try:
        text = data.decode('utf-8')
        if '\x00' in text or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
            return data
        root = ET.fromstring(text)
        metadata = root.findall('metadata')
        if (root.tag != 'doc' or root.get('func') != SITE_FUNCTION or root.find('.//error') is not None
                or root.find('ok') is not None or root.find('tparams/sok') is not None
                or len(metadata) != 1 or metadata[0].get('name') != SITE_FUNCTION
                or metadata[0].get('type') != 'form' or root.find(VALUE) is not None
                or metadata[0].find('.//field[@name="' + FIELD + '"]') is not None):
            return data
        forms = metadata[0].findall('form')
        if len(forms) != 1:
            return data
        form = forms[0]
        pages = form.findall('page')
        if pages:
            main = form.findall('page[@name="mainsettings"]')
            if len(main) != 1:
                return data
            form = main[0]
        notice = (store or NoticeStore()).load()
        if not notice['text'].strip():
            return data
        field = ET.Element('field', {'name': FIELD, 'noname': 'yes', 'fullwidth': 'yes', 'base': 'yes'})
        # Only generated <br> markup is enabled: every character of user text is escaped.
        ET.SubElement(field, 'textdata', {'name': VALUE, 'type': 'banner', 'status': notice['style'], 'html': 'yes'})
        form.insert(0, field)
        ET.SubElement(root, VALUE).text = html.escape(notice['text'], quote=True).replace('\n', '<br>')
        return b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='utf-8').replace(b'\r', b'&#13;')
    except Exception:
        # Presentation failure never blocks native create/edit, access checks or save.
        return data


def main():
    if os.environ.get('PARAM_func') == SETTINGS_FUNCTION:
        root = settings_response(os.environ)
        sys.stdout.buffer.write(b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='utf-8'))
        return 0
    data = sys.stdin.buffer.read(MAX_XML_BYTES + 1)
    if len(data) <= MAX_XML_BYTES:
        sys.stdout.buffer.write(transform(data, os.environ))
    else:
        sys.stdout.buffer.write(data)
        while True:
            block = sys.stdin.buffer.read(65536)
            if not block:
                break
            sys.stdout.buffer.write(block)
    return 0


if __name__ == '__main__':
    sys.exit(main())
