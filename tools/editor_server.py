"""Local-only synthetic panel harness. Never connect to real files or a panel."""

import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import importlib.util
from pathlib import Path
import mimetypes
import sys
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('preview', str(ROOT / 'integration/editor/ismonaco_editor.py'))
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)
SOURCE = "\ufeff<?php\r\n// İstanbul — yalnızca yerel test verisi\r\n$message = '</script><script>parent.PWNED = true</script>';\r\necho $message;\r\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return
        if path in ('/', '/normal', '/denied', '/ambiguous', '/slow', '/readonly', '/custom', '/markup', '/save-close-error'):
            context = {'AUTH_USER': 'root' if path == '/' else 'test-user',
                       'AUTH_LEVEL': '30' if path == '/' else '16', 'PARAM_func': 'file.edit'}
            document = ET.fromstring('<doc func="file.edit"><metadata name="file.edit" type="form"><form><field name="filename"><textdata name="filename"/></field><field name="encoding"><select name="encoding"/></field><field name="fdata"><textarea name="fdata" editor="yes"/></field></form><buttons><button name="apply" type="setvalues"/><button name="ok" type="ok"/><button name="cancel" type="cancel"/></buttons></metadata><fdata/></doc>')
            source = '''<?php
// <head>comment</head>
$x = '<head>string</head>';
if ($x) { echo $x; }
?>
<html>
<head>
<meta charset="utf-8">
<title>Example</title>
</head>
<body><header>Content</header></body>
</html>''' if path == '/markup' else SOURCE
            document.find('fdata').text = source
            if path == '/denied':
                ET.SubElement(document, 'error', {'type': 'access'})
            original_appearance = preview.appearance
            if path == '/custom':
                preview.appearance = lambda: dict(preview.DEFAULTS, theme='light', fontSize=16, wrap=False, minimap=False, height=900, fullscreen=False)
            try:
                output = ET.fromstring(preview.transform(ET.tostring(document), context))
            finally:
                preview.appearance = original_appearance
            # Model only the supported native Phoenix frame branch, not htmldata.
            frame = output.find('metadata/form/field/frame')
            if frame is not None:
                url = output.find(frame.get('name')).text
                content = ('<isp-form-view-element data-dynamic-form-element-id="ismonaco_preview-frame">'
                           '<isp-form-view-frame-auxiliary style="height:'
                           + html.escape(frame.get('height')) + '"><iframe id="preview-frame" title="Monaco Editor" '
                           'style="width:100%;height:100%;border:1px solid #dce5df" src="'
                           + html.escape(url, quote=True) + '"></iframe></isp-form-view-frame-auxiliary>'
                           '</isp-form-view-element>')
            else:
                content = '<p id="denied">Native erişim reddedildi; Monaco eklenmedi.</p>'
            class Defaults:
                def load(self): return dict(preview.DEFAULTS)
            settings = preview.settings_response({'AUTH_USER': 'root', 'AUTH_LEVEL': '30', 'PARAM_lang': 'tr'}, Defaults())
            settings_html = '<section id="settings-form" hidden><h2>' + html.escape(settings.find("messages/msg[@name='title']").text) + '</h2>'
            for select in settings.findall('metadata/form/field/select'):
                name = select.get('name')
                label = settings.find("messages/msg[@name='%s']" % name).text
                settings_html += '<label>' + html.escape(label) + '<select aria-label="' + html.escape(label) + '">'
                for option in settings.findall("slist[@name='%s']/val" % name):
                    settings_html += '<option value="' + html.escape(option.get('key')) + '">' + html.escape(option.text) + '</option>'
                settings_html += '</select></label>'
            settings_html += '</section>'
            duplicate = ('<isp-form-view-element data-dynamic-form-element-id="fdata-code-element">'
                         '<ace-editor></ace-editor></isp-form-view-element>') if path == '/ambiguous' else ''
            boot = json.dumps({'content': source, 'delay': 400 if path == '/slow' else 0, 'readonly': path == '/readonly', 'closeError': path == '/save-close-error'}).replace('<', chr(92) + 'u003c')
            data = ('''<!doctype html><html lang="tr"><meta charset="utf-8"><title>Monaco yerel entegrasyon testi</title>
            <style>body{margin:16px;font:14px system-ui}isp-new-dynamic-form,isp-form-view-element,isp-form-view-frame-auxiliary,ace-editor{display:block}ace-editor{height:120px;width:100%}#decoy-form{display:none}</style>
            <body><p>Yerel sentetik panel testi · ''' + ('root' if path == '/' else 'normal kullanıcı') + '''</p>
            <isp-new-dynamic-form id="decoy-form"><isp-form-view-element data-dynamic-form-element-id="fdata-code-element"><ace-editor id="decoy"></ace-editor></isp-form-view-element></isp-new-dynamic-form>
            <isp-new-dynamic-form id="selected-form"><div id="native-filename">File name · <isp-form-view-element data-dynamic-form-element-id="full_filepath-textdata"><isp-form-view-text-auxiliary><span class="text-block">/test/example.php</span></isp-form-view-text-auxiliary></isp-form-view-element></div><label id="native-encoding">Encoding <select aria-label="Encoding"><option>UTF-8</option></select></label>''' + content + '''
            <isp-form-view-element data-dynamic-form-element-id="fdata-code-element"><p>Mevcut panel editörü (gerçek Ace ile yerel test örneği)</p><isp-form-view-code-field id="native-code"><ace-editor id="native"></ace-editor></isp-form-view-code-field></isp-form-view-element>''' + duplicate + '''<isp-form-view-buttons-container><isp-form-view-element data-dynamic-form-element-id="apply"><isp-form-view-button><button id="native-save" type="button">Save</button></isp-form-view-button></isp-form-view-element><isp-form-view-element data-dynamic-form-element-id="ok"><isp-form-view-button><button id="native-save-close" type="button">Save and close</button></isp-form-view-button></isp-form-view-element><isp-form-view-element data-dynamic-form-element-id="cancel"><isp-form-view-button><button id="native-cancel" type="button">Close</button></isp-form-view-button></isp-form-view-element></isp-form-view-buttons-container></isp-new-dynamic-form>
            ''' + settings_html + '''<script type="application/json" id="harness-data">''' + boot + '''</script>
            <script src="/__harness/ace.js"></script><script>
            const boot=JSON.parse(document.getElementById('harness-data').textContent);
            ace.config.set('basePath','/__harness');
            const decoy=ace.edit(document.getElementById('decoy'));decoy.session.setUseWorker(false);decoy.setValue('OTHER_FORM_PRIVATE_DATA',-1);
            setTimeout(()=>{const editor=ace.edit(document.getElementById('native'));editor.session.setUseWorker(false);editor.setValue(boot.content,-1);editor.setReadOnly(boot.readonly);window.nativeModel=editor.getValue();window.nativeWrites=0;editor.on('change',()=>{window.nativeWrites++;window.nativeModel=editor.getValue()});},boot.delay);
            window.addEventListener('hashchange',()=>{document.getElementById('settings-form').hidden=location.hash!=='#/form?func=ismonaco.settings'});
            document.getElementById('native-save').onclick=()=>{window.nativeSubmittedContent=window.nativeModel;window.nativeSaveCount=(window.nativeSaveCount||0)+1};
            document.getElementById('native-save-close').onclick=()=>{window.nativeSaveCloseCount=(window.nativeSaveCloseCount||0)+1;window.nativeSubmittedContent=window.nativeModel;if(!boot.closeError)window.nativeClosed=true;else{const error=document.createElement('p');error.setAttribute('role','alert');error.textContent='Native save rejected';document.getElementById('selected-form').append(error)}};
            document.getElementById('native-code').addEventListener('keydown',e=>{if(e.code==='KeyS'&&(e.ctrlKey||e.metaKey)){e.preventDefault();document.getElementById('native-save').click()}});
            </script></body></html>''').encode()
            mime = 'text/html; charset=utf-8'
        elif path == '/__harness/ace.js':
            data = (ROOT / 'node_modules/ace-builds/src-min-noconflict/ace.js').read_bytes()
            mime = 'text/javascript'
        elif path.startswith(preview.ASSETS + '/'):
            try:
                relative = Path(path[len(preview.ASSETS) + 1:])
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError('Invalid asset path')
                base = (ROOT / 'dist/frontend').resolve()
                target = base / relative
                resolved = target.resolve()
                resolved.relative_to(base)
                if not resolved.is_file():
                    raise ValueError('Not an asset file')
                data = resolved.read_bytes()
            except (OSError, RuntimeError, ValueError):
                self.send_error(404)
                return
            mime = mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
            if target.suffix == '.js':
                mime = 'text/javascript'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        pass


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print('Synthetic local harness at http://127.0.0.1:' + str(port), flush=True)
    HTTPServer(('127.0.0.1', port), Handler).serve_forever()
