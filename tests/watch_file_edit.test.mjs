import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../tools/watch_file_edit.js', import.meta.url), 'utf8');
function harness() {
  const logs = [], sends = [], timers = [];
  class XHR extends EventTarget {
    send(...args) { sends.push({ receiver: this, args }); return 'NATIVE_RETURN'; }
  }
  const original = XHR.prototype.send;
  const context = vm.createContext({ XMLHttpRequest: XHR, URL,
    location: { origin: 'https://panel.test', href: 'https://panel.test/ispmgr' },
    console: { log: (message) => logs.push(message) },
    setTimeout: (callback) => { timers.push(callback); return timers.length; }, clearTimeout() {} });
  vm.runInContext(source, context);
  function request(url, data, responseType = 'json') {
    const xhr = new XHR();
    xhr.responseURL = url; xhr.status = 200; xhr.responseType = responseType;
    if (responseType === 'json') xhr.response = data;
    else xhr.responseText = data;
    const result = xhr.send('UNCHANGED_BODY');
    xhr.dispatchEvent(new Event('load'));
    return { xhr, result };
  }
  return { logs, sends, timers, context, XHR, original, request };
}
const target = 'https://panel.test/ispmgr?func=file.edit&auth=PRIVATE_TOKEN';

test('observes existing native request, preserves send and never logs private values', () => {
  const h = harness();
  assert.equal(h.sends.length, 0);
  const { xhr, result } = h.request(target, { doc: {
    metadata: { form: { field: [{ $name: 'ismonaco_preview', htmldata: { $name: 'ismonaco_preview' } }] } },
    ismonaco_preview: [{ $: 'PRIVATE_HTML' }], fdata: [{ $: 'PRIVATE_FILE' }], auth: 'PRIVATE_AUTH',
  } });
  assert.equal(result, 'NATIVE_RETURN');
  assert.equal(h.sends[0].receiver, xhr);
  assert.deepEqual(h.sends[0].args, ['UNCHANGED_BODY']);
  const output = h.logs.find((line) => line.startsWith('MONACO_NATIVE_CHECK\n'));
  const report = JSON.parse(output.split('\n').slice(1).join('\n'));
  assert.equal(report.metadataKeyPresent, true);
  assert.equal(report.previewDataKeyPresent, true);
  assert.equal(report.previewNamedElementPresent, true);
  assert.equal(report.htmlDataKeyPresent, true);
  assert.equal(h.logs.join().includes('PRIVATE_'), false);
  assert.equal(h.XHR.prototype.send, h.original);
});

test('ignores unrelated functions and origins without changing the request', () => {
  const h = harness();
  h.request('https://panel.test/ispmgr?func=desktop', { secret: 'PRIVATE' });
  h.request('https://other.test/ispmgr?func=file.edit', { secret: 'PRIVATE' });
  assert.equal(h.sends.length, 2);
  assert.equal(h.logs.length, 1);
  assert.notEqual(h.XHR.prototype.send, h.original);
  h.timers[0]();
  assert.equal(h.XHR.prototype.send, h.original);
});

test('does not mistake file text for metadata or preview keys', () => {
  const h = harness();
  h.request(target, { doc: { fdata: [{ $: 'metadata ismonaco_preview htmldata error' }] } });
  const report = JSON.parse(h.logs[1].split('\n').slice(1).join('\n'));
  assert.equal(report.previewDataKeyPresent, false);
  assert.equal(report.metadataKeyPresent, false);
  assert.equal(report.errorKeyPresent, false);
});

test('handles malformed and excessive responses without echoing data or blocking native send', () => {
  for (const data of ['PRIVATE_INVALID_JSON', 'PRIVATE_' + 'x'.repeat(4194304)]) {
    const h = harness();
    assert.equal(h.request(target, data, '').result, 'NATIVE_RETURN');
    assert.match(h.logs[1], /UNSUPPORTED_RESPONSE/);
    assert.equal(h.logs.join().includes('PRIVATE_'), false);
    assert.equal(h.XHR.prototype.send, h.original);
  }
});

test('repeat installation and timeouts restore exactly the active observer', () => {
  const h = harness();
  vm.runInContext(source, h.context);
  h.timers[0]();
  assert.notEqual(h.XHR.prototype.send, h.original);
  h.context.__ismonacoPreviewDiagnosticStop();
  assert.equal(h.XHR.prototype.send, h.original);
  assert.equal(h.context.__ismonacoPreviewDiagnosticStop, undefined);
});
