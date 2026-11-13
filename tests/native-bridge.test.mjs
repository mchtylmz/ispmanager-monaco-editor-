import test from 'node:test';
import assert from 'node:assert/strict';
import { readFilePath, readSnapshot, waitForSnapshot } from '../frontend/native-bridge.mjs';

function host(content = '<?php echo 1;') {
  const element = {};
  const editor = { container: element, getValue: () => content };
  element.env = { editor };
  const field = { querySelectorAll: () => [element] };
  const form = { isConnected: true, contains: (node) => node === element,
    querySelectorAll: (selector) => {
      assert.equal(selector, '[data-dynamic-form-element-id="fdata-code-element"]');
      return [field];
    } };
  const wrapper = { getAttribute: () => 'ismonaco_preview-frame' };
  const frame = { closest: (selector) => selector === 'isp-new-dynamic-form' ? form : wrapper };
  const view = { frameElement: frame, parent: {} };
  Object.defineProperties(view, {
    document: { get() { throw new Error('GLOBAL_DOM_FORBIDDEN'); } },
    localStorage: { get() { throw new Error('STORAGE_FORBIDDEN'); } },
    fetch: { get() { throw new Error('REQUEST_FORBIDDEN'); } },
  });
  return { view, form, field, element, editor, wrapper };
}

test('reads exactly the bound native Ace value without global DOM, storage or network', () => {
  const h = host('İstanbul\r\n</script><script>PRIVATE_DATA</script>');
  Object.freeze(h.element); Object.freeze(h.editor); Object.freeze(h.form);
  const snapshot = readSnapshot(h.view);
  assert.equal(snapshot.content, 'İstanbul\r\n</script><script>PRIVATE_DATA</script>');
  assert.equal(snapshot.readOnly, true);
});

test('does not fall back outside the containing form when fdata is missing', () => {
  const h = host();
  h.form.querySelectorAll = () => [];
  assert.equal(readSnapshot(h.view), null);
});

test('rejects standalone pages, incorrect frame wrappers and detached forms', () => {
  assert.throws(() => readSnapshot({ frameElement: null }), /NOT_EMBEDDED/);
  const h = host();
  h.wrapper.getAttribute = () => 'other-frame';
  assert.throws(() => readSnapshot(h.view), /WRONG_FRAME_BINDING/);
  h.wrapper.getAttribute = () => 'ismonaco_preview-frame';
  h.form.isConnected = false;
  assert.throws(() => readSnapshot(h.view), /NO_NATIVE_FORM/);
});

test('rejects ambiguous fields and editors rather than picking another value', () => {
  const h = host();
  h.form.querySelectorAll = () => [h.field, h.field];
  assert.throws(() => readSnapshot(h.view), /AMBIGUOUS_NATIVE_FIELD/);
  h.form.querySelectorAll = () => [h.field];
  h.field.querySelectorAll = () => [h.element, h.element];
  assert.throws(() => readSnapshot(h.view), /AMBIGUOUS_NATIVE_EDITOR/);
});

test('requires Ace container identity and rejects a form change during the read', () => {
  const h = host();
  h.editor.container = {};
  assert.equal(readSnapshot(h.view), null);
  h.editor.container = h.element;
  h.editor.getValue = () => { h.form.isConnected = false; return 'PRIVATE'; };
  assert.throws(() => readSnapshot(h.view), /FORM_CHANGED/);
});

test('enforces byte limit and accepts an empty authorized document', () => {
  assert.equal(readSnapshot(host('').view).content, '');
  assert.throws(() => readSnapshot(host('ğ'.repeat(262145)).view), /NATIVE_CONTENT_REJECTED/);
});

test('readiness waits are bounded and abortable', async () => {
  const h = host();
  h.form.querySelectorAll = () => [];
  await assert.rejects(waitForSnapshot(h.view, new AbortController().signal, 0), /TIMEOUT/);
  const controller = new AbortController();
  const promise = waitForSnapshot(h.view, controller.signal);
  controller.abort();
  await assert.rejects(promise, /ABORTED/);
});

test('file path reads only the unique native text block in the bound form', () => {
  const h = host(); const native = h.form.querySelectorAll;
  let value = '/var/www/test/index.php';
  const path = { querySelectorAll: () => [{ get textContent() { return value; } }] };
  let paths = [path];
  h.form.querySelectorAll = selector => selector.includes('full_filepath-textdata') ? paths : native(selector);
  assert.equal(readFilePath(h.view), value);
  paths = [path, path]; assert.equal(readFilePath(h.view), '');
  paths = []; assert.equal(readFilePath(h.view), '');
  paths = [path];
  for (value of ['relative.php', '/bad\npath', '/' + 'x'.repeat(4096)]) assert.equal(readFilePath(h.view), '');
});
