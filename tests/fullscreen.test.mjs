import test from 'node:test';
import assert from 'node:assert/strict';
import { createFullscreen } from '../frontend/fullscreen.mjs';

function fixture() {
  const changes = [], observers = [], attrs = new Map();
  function style(initial = {}) {
    const values = new Map(Object.entries(initial).map(([k, v]) => [k, [v, '']]));
    return { getPropertyValue: (key) => values.get(key)?.[0] || '',
      getPropertyPriority: (key) => values.get(key)?.[1] || '',
      setProperty: (key, value, priority) => values.set(key, [value, priority]),
      removeProperty: (key) => values.delete(key) };
  }
  const target = { isConnected: true, style: style({ padding: '3px', color: 'red' }),
    getAttribute: (key) => key === 'data-dynamic-form-element-id' ? 'ismonaco_preview-frame' : attrs.get(key),
    hasAttribute: (key) => attrs.has(key), setAttribute: (k, v) => attrs.set(k, v),
    removeAttribute: (key) => attrs.delete(key), showPopover() { this.open = true; }, hidePopover() { this.open = false; } };
  const host = { style: style({ height: '760px' }) };
  const element = {};
  element.env = { editor: { container: element, getValue: () => 'authorized text' } };
  const field = { querySelectorAll: () => [element] };
  const document = { hidden: false, addEventListener() {}, removeEventListener() {} };
  const form = { isConnected: true, ownerDocument: document, parentElement: null,
    getClientRects: () => [{}], querySelectorAll: () => [field] };
  const frame = { style: style(), closest: (selector) => selector === 'isp-new-dynamic-form' ? form
    : selector === 'isp-form-view-frame-auxiliary' ? host : target };
  const view = { parent: {}, frameElement: frame, MutationObserver: class {
    constructor(callback) { this.callback = callback; observers.push(this); }
    observe() {} disconnect() { this.disconnected = true; }
  } };
  const fullscreen = createFullscreen(view, (active) => changes.push(active));
  return { fullscreen, form, target, host, frame, element, document, changes, observers };
}

test('fullscreen promotes only its existing wrapper and restores exact inline styles', () => {
  const h = fixture();
  assert.equal(h.fullscreen.enter(), true);
  assert.equal(h.target.open, true);
  assert.equal(h.target.style.getPropertyValue('inset'), '0');
  assert.equal(h.host.style.getPropertyValue('height'), '100%');
  h.fullscreen.exit();
  assert.equal(h.target.hasAttribute('popover'), false);
  assert.equal(h.target.style.getPropertyValue('padding'), '3px');
  assert.equal(h.target.style.getPropertyValue('color'), 'red');
  assert.equal(h.target.style.getPropertyValue('position'), '');
  assert.equal(h.host.style.getPropertyValue('height'), '760px');
  assert.deepEqual(h.changes, [true, false]);
  h.fullscreen.dispose();
  assert.deepEqual(h.changes, [true, false]);
});
test('unsupported, foreign and failed popovers leave inline/native layout intact', () => {
  for (const type of ['unsupported', 'foreign', 'failed', 'changed']) {
    const h = fixture();
    if (type === 'unsupported') h.target.showPopover = undefined;
    if (type === 'foreign') h.target.setAttribute('popover', 'auto');
    if (type === 'failed') h.target.showPopover = () => { throw new Error('unsupported'); };
    if (type === 'changed') h.element.env.editor = { ...h.element.env.editor };
    assert.equal(h.fullscreen.enter(), false);
    assert.equal(h.fullscreen.active, false);
    assert.equal(h.host.style.getPropertyValue('height'), '760px');
    assert.equal(h.target.style.getPropertyValue('padding'), '3px');
    if (type === 'foreign') assert.equal(h.target.getAttribute('popover'), 'auto');
  }
});
test('hidden or removed native form exits fullscreen without retaining a panel overlay', () => {
  for (const reason of ['hidden', 'removed', 'tab', 'hidden-attribute']) {
    const h = fixture(); h.fullscreen.enter();
    if (reason === 'hidden') h.document.hidden = true;
    if (reason === 'removed') h.target.isConnected = false;
    if (reason === 'hidden-attribute') h.form.closest = () => ({});
    if (reason === 'tab') h.form.getClientRects = () => [];
    h.observers[0].callback();
    assert.equal(h.fullscreen.active, false);
    assert.equal(h.observers[0].disconnected, true);
    assert.equal(h.target.hasAttribute('popover'), false);
  }
});
