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
SPEC = importlib.util.spec_from_file_location('preview', str(ROOT / 'integration/preview/ismonaco_preview.py'))
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)
SOURCE = "<?php\r\n// İstanbul — yalnızca yerel test verisi\r\n$message = '</script><script>parent.PWNED = true</script>';\r\necho $message;\r\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return
        if path in ('/', '/normal', '/denied', '/ambiguous', '/slow'):
            context = {'AUTH_USER': 'root' if path == '/' else 'test-user',
                       'AUTH_LEVEL': '30' if path == '/' else '16', 'PARAM_func': 'file.edit'}
            document = ET.fromstring('<doc func="file.edit"><metadata name="file.edit" type="form"><form><field name="fdata"><textarea name="fdata" editor="yes"/></field></form></metadata><fdata/></doc>')
            document.find('fdata').text = SOURCE
            if path == '/denied':
                ET.SubElement(document, 'error', {'type': 'access'})
            output = ET.fromstring(preview.transform(ET.tostring(document), context))
            # Model only the supported native Phoenix frame branch, not htmldata.
            frame = output.find('metadata/form/field/frame')
            if frame is not None:
                url = output.find(frame.get('name')).text
                content = ('<isp-form-view-element data-dynamic-form-element-id="ismonaco_preview-frame">'
                           '<isp-form-view-frame-auxiliary><iframe id="preview-frame" title="Monaco pilot" '
                           'style="width:100%;height:620px;border:1px solid #dce5df" src="'
                           + html.escape(url, quote=True) + '"></iframe></isp-form-view-frame-auxiliary>'
                           '</isp-form-view-element>')
            else:
                content = '<p id="denied">Native erişim reddedildi; Monaco eklenmedi.</p>'
            duplicate = ('<isp-form-view-element data-dynamic-form-element-id="fdata-code-element">'
                         '<ace-editor></ace-editor></isp-form-view-element>') if path == '/ambiguous' else ''
            boot = json.dumps({'content': SOURCE, 'delay': 400 if path == '/slow' else 0}).replace('<', chr(92) + 'u003c')
            data = ('''<!doctype html><html lang="tr"><meta charset="utf-8"><title>Monaco yerel entegrasyon testi</title>
            <style>body{margin:16px;font:14px system-ui}isp-new-dynamic-form,isp-form-view-element,isp-form-view-frame-auxiliary,ace-editor{display:block}ace-editor{height:120px;width:100%}#decoy-form{display:none}</style>
            <body><p>Yerel sentetik panel testi · ''' + ('root' if path == '/' else 'normal kullanıcı') + '''</p>
            <isp-new-dynamic-form id="decoy-form"><isp-form-view-element data-dynamic-form-element-id="fdata-code-element"><ace-editor id="decoy"></ace-editor></isp-form-view-element></isp-new-dynamic-form>
            <isp-new-dynamic-form id="selected-form">''' + content + '''
            <p>Mevcut panel editörü (gerçek Ace ile yerel test örneği)</p>
            <isp-form-view-element data-dynamic-form-element-id="fdata-code-element"><ace-editor id="native"></ace-editor></isp-form-view-element>''' + duplicate + '''</isp-new-dynamic-form>
            <script type="application/json" id="harness-data">''' + boot + '''</script>
            <script src="/__harness/ace.js"></script><script>
            const boot=JSON.parse(document.getElementById('harness-data').textContent);
            ace.config.set('basePath','/__harness');
            const decoy=ace.edit(document.getElementById('decoy'));decoy.session.setUseWorker(false);decoy.setValue('OTHER_FORM_PRIVATE_DATA',-1);
            setTimeout(()=>{const editor=ace.edit(document.getElementById('native'));editor.session.setUseWorker(false);editor.setValue(boot.content,-1);window.nativeWrites=0;editor.on('change',()=>window.nativeWrites++);},boot.delay);
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
