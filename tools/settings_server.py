"""Local settings regression harness using the actual Phoenix submit method.

No live panel auth or API access. Writes only a TemporaryDirectory config.
Closed-source panel code is read from an explicitly provided public bundle,
validated by hash, and is never included in the distributed plugin archive.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import zipfile
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit, parse_qs

PROJECT = Path(__file__).resolve().parents[1]
SOURCE_HASH = '894c4de0e503c1723ae6b68a2c3856ebe125a7d8598780c466a48ac9ef44b6f0'
METHOD_HASH = '5964e989a39bb0d532fd1ceffff64c48386b1cb929f2fcad545fcc622219e207'
SPEC = importlib.util.spec_from_file_location('settings_backend', str(PROJECT / 'integration/editor/ismonaco_editor.py'))
backend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backend)


def native_method(path):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_HASH:
        raise ValueError('NATIVE_PUBLIC_SOURCE_MISMATCH')
    source = data.decode()
    start = source.index('applyFormSubmitResponse(e,t,i=!1){')
    method = source[start:source.index('download(e,t=', start)]
    if hashlib.sha256(method.encode()).hexdigest() != METHOD_HASH:
        raise ValueError('NATIVE_SUBMIT_METHOD_MISMATCH')
    return ('const q=(...v)=>Object.assign({},...v), x=q;\nexport const native={'+method+'};').encode()


def document_json(node):
    if node.tag == 'messages':
        return {'msg': {e.get('name'): e.text or '' for e in node.findall('msg')}}
    result = {'$' + key: value for key, value in node.attrib.items()}
    if node.text and node.text.strip(): result['$'] = node.text
    for child in node:
        value = document_json(child)
        if child.tag in ('field', 'button', 'slist', 'val'):
            result.setdefault(child.tag, []).append(value)
        elif child.tag in result:
            result[child.tag] = [result[child.tag], value]
        else:
            result[child.tag] = value
    return result


PAGE = b'''<!doctype html><html lang="tr"><meta charset="utf-8"><title>Native settings submit regression</title>
<style>body{font:16px system-ui;margin:24px;max-width:720px}label{display:flex;justify-content:space-between;gap:16px;margin:16px 0}select,button{font:inherit;padding:7px}button{margin:12px 12px 0 0}[role=alert]{color:#a11}#saved{color:#176a2b}[hidden]{display:none}</style>
<h1 id="title"></h1><p id="saved" role="status"></p><p id="error" role="alert"></p><form id="settings"></form><p id="closed" hidden>Closed</p>
<script type="module">
import {native} from '/native-submit.js';
const parameters = new URLSearchParams(location.search), form=document.getElementById('settings');
const state={standalone:parameters.get('standalone')!=='false',doc:null};
window.submissions=0;
const api='/api/settings?'+parameters;
function render(doc){
 document.getElementById('title').textContent=doc.messages?.msg?.title||'';
 document.getElementById('saved').textContent=doc.messages?.msg?.ismonaco_saved||'';
 document.getElementById('error').textContent=doc.error?.msg?.$||'';
 form.replaceChildren();
 for(const field of doc.metadata?.form?.field||[]){
  if(!field.select)continue;
  const name=field.select.$name, label=document.createElement('label'), select=document.createElement('select');
  label.append(doc.messages.msg[name]); select.name=name;select.setAttribute('aria-label',doc.messages.msg[name]);
  const listing=doc.slist.find(s=>s.$name===name);
  for(const item of listing.val){const option=document.createElement('option');option.value=item.$key;option.textContent=item.$;select.append(option)}
  select.value=doc[name].$;label.append(select);form.append(label);
 }
 if(doc.metadata){const save=document.createElement('button');save.type='submit';save.textContent=doc.messages.msg.msg_ok;form.append(save)}
}
native.tabService={resetSuccess(){},update(tab,doc){tab.doc=doc;render(doc)},close(){form.replaceChildren();document.getElementById('closed').hidden=false}};
// Empty ok follows the native redirect service's verified no-tab-action path.
// A full page response must not invoke redirect at all.
native.redirectService={redirect$(){return{subscribe(callback){callback({type:'no-tab-action'})}}}};
form.addEventListener('submit',async event=>{
 event.preventDefault();const body=new URLSearchParams(new FormData(form));body.set('sok','ok');
 const response=await fetch(api,{method:'POST',body});const doc=await response.json();
 native.applyFormSubmitResponse(doc,state);window.submissions++;
});
state.doc=await fetch(api).then(r=>r.json());render(state.doc);document.documentElement.dataset.ready='true';
</script></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-source', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8767)
    args = parser.parse_args()
    method = native_method(args.native_source)
    archive_path = PROJECT / 'dist/ismonaco-editor-0.2.2.zip'
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != '8db8347cb584267d8c78278738adbbd59b0dbbe00d3cc159c53aa9219559b6cf':
        raise ValueError('BASELINE_RELEASE_MISMATCH')
    with zipfile.ZipFile(str(archive_path)) as archive:
        baseline = types.ModuleType('baseline_settings')
        exec(compile(archive.read('payload/addon/ismonaco_0_2_2.py'), 'baseline_settings.py', 'exec'), baseline.__dict__)
    with tempfile.TemporaryDirectory(prefix='ismonaco-settings-test-') as directory:
        anchor = Path(directory)
        config = anchor / 'defaults.json'
        config.write_text(json.dumps(backend.DEFAULTS)); config.chmod(0o600)
        store = backend.ConfigStore(config, os.getuid(), os.getgid(), anchor)
        class BrokenStore:
            def load(self): return store.load()
            def save(self, value): raise OSError('synthetic IO failure')
        class Handler(BaseHTTPRequestHandler):
            def handle_request(self, post=False):
                route = urlsplit(self.path)
                parameters = parse_qs(route.query)
                if route.path == '/favicon.ico': self.send_response(204); self.end_headers(); return
                if route.path == '/': data, mime = PAGE, 'text/html; charset=utf-8'
                elif route.path == '/native-submit.js': data, mime = method, 'text/javascript'
                elif route.path == '/api/settings':
                    context = {'AUTH_USER': 'root', 'AUTH_LEVEL': '30', 'PARAM_func': 'ismonaco.settings', 'PARAM_lang': 'tr'}
                    if parameters.get('role') == ['normal']: context.update(AUTH_USER='test-user', AUTH_LEVEL='16')
                    if post:
                        size = int(self.headers.get('Content-Length', 0))
                        if not 0 <= size <= 4096: self.send_error(413); return
                        values = parse_qs(self.rfile.read(size).decode(), keep_blank_values=True)
                        context.update({'PARAM_' + k: v[0] for k, v in values.items()})
                    handler = baseline if parameters.get('legacy') == ['true'] else backend
                    response = handler.settings_response(context, BrokenStore() if post and parameters.get('io') == ['true'] else store)
                    data, mime = json.dumps(document_json(response)).encode(), 'application/json'
                else: self.send_error(404); return
                self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)))
                self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
            def do_GET(self): self.handle_request()
            def do_POST(self): self.handle_request(True)
            def log_message(self, *_): pass
        print('Native-method settings regression at http://127.0.0.1:'+str(args.port), flush=True)
        HTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__': main()
