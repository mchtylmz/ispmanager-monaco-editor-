import test from 'node:test';
import assert from 'node:assert/strict';
import { createEditorBridge } from '../frontend/editor-bridge.mjs';

function style(initial = '') {
  let value = initial, priority = '';
  return { getPropertyValue: () => value, getPropertyPriority: () => priority,
    setProperty: (_, v, p = '') => { value = v; priority = p; },
    get display() { return value; }, set display(v) { value = v; } };
}
function host(initial = '<?php echo 1;') {
  let value = initial, native = initial, readonly = false;
  const change = new Set(), events = new Map(), calls = { writes: 0, faults: 0, saves: 0, closes: 0 };
  const element = {};
  const editor = { container: element, getValue: () => native, getReadOnly: () => readonly,
    setValue(next) { native = next; calls.writes++; for (const handler of change) handler(); },
    on: (_, fn) => change.add(fn), off: (_, fn) => change.delete(fn) };
  element.env = { editor };
  const code = { dispatchEvent(event) { calls.saves++; assert.equal(event.code, 'KeyS'); } };
  const field = { style: style('block'), querySelectorAll: () => [element], querySelector: () => code };
  const wrapper = { style: style(), getAttribute: () => 'ismonaco_preview-frame' };
  const frameHost = { style: {} };
  const closeButton = { disabled: false, getAttribute: () => null, click: () => calls.closes++ };
  const closeWrapper = { querySelectorAll: () => [closeButton] };
  const form = { isConnected: true, contains: (node) => node === element || node === closeButton,
    querySelectorAll: (selector) => selector.includes('fdata-code-element') ? [field] : selector.includes('="ok"') ? [closeWrapper] : [{}],
    addEventListener(type, fn) { if (!events.has(type)) events.set(type, new Set()); events.get(type).add(fn); },
    removeEventListener: (type, fn) => events.get(type)?.delete(fn) };
  const frame = { closest: (selector) => selector === 'isp-new-dynamic-form' ? form
    : selector === 'isp-form-view-frame-auxiliary' ? frameHost : wrapper };
  const view = { frameElement: frame, parent: { location: { hash: '' } }, confirm: () => false,
    KeyboardEvent: class { constructor(type, data) { this.type = type; Object.assign(this, data); } } };
  const options = { saveButtons: ['apply', 'ok'], saveAndCloseButton: 'ok', cancelButtons: ['cancel'],
    getValue: () => value, replaceValue: (next) => { value = next; },
    onFault: () => calls.faults++, onReadOnly() {} };
  const bridge = createEditorBridge(view, options);
  function click(id = 'apply') {
    const event = { type: 'click', target: { closest: () => ({ getAttribute: () => id }) },
      preventDefault() { this.prevented = true; }, stopImmediatePropagation() {} };
    for (const fn of events.get('click') || []) fn(event);
    return event;
  }
  return { view, field, form, frameHost, editor, element, bridge, calls, options, click, closeButton, closeWrapper,
    setModel: (next) => { value = next; }, getModel: () => value, setReadonly: (next) => { readonly = next; } };
}

test('one visible editor; updates native buffer and allows its original save controls', () => {
  const h = host(); h.bridge.activate();
  assert.equal(h.field.style.display, 'none');
  h.setModel('<?php echo 2;');
  assert.equal(h.bridge.commit(h.getModel()), true);
  assert.equal(h.editor.getValue(), '<?php echo 2;');
  assert.equal(h.calls.writes, 1);
  assert.equal(h.click().prevented, undefined);
  assert.equal(h.bridge.requestSave(), true);
  assert.equal(h.calls.saves, 1);
  h.bridge.dispose();
  assert.equal(h.field.style.display, 'block');
});
test('native readonly cannot be overridden by a Monaco edit or save', () => {
  const h = host(); h.setReadonly(true); h.bridge.activate();
  assert.equal(h.bridge.readOnly, true);
  h.setModel('ATTEMPT');
  assert.equal(h.bridge.commit(h.getModel()), false);
  assert.equal(h.calls.writes, 0);
  assert.equal(h.field.style.display, 'block');
  assert.equal(h.click().prevented, true);
});
test('setter failure retains pending text and blocks save until explicit fallback', () => {
  const h = host(); h.bridge.activate();
  h.editor.setValue = () => { throw new Error('PRIVATE_ERROR'); };
  h.setModel('PENDING_CONTENT');
  assert.equal(h.bridge.commit(h.getModel()), false);
  assert.equal(h.getModel(), 'PENDING_CONTENT');
  assert.equal(h.calls.faults, 1);
  assert.equal(h.click().prevented, true);
  assert.equal(h.bridge.useNative(), false);
  h.view.confirm = () => true;
  assert.equal(h.bridge.useNative(), true);
  assert.equal(h.field.style.display, 'block');
  assert.equal(h.click().prevented, undefined);
});
test('external native change is reflected without a write-back loop', () => {
  const h = host(); h.bridge.activate();
  h.editor.setValue('RELOADED_CONTENT');
  assert.equal(h.getModel(), 'RELOADED_CONTENT');
  assert.equal(h.calls.writes, 1);
  assert.equal(h.calls.faults, 0);
});
test('revocation, swapped editor and oversized data never overwrite native data', () => {
  for (const failure of ['readonly', 'replaced', 'oversized']) {
    const h = host(); h.bridge.activate(); h.setModel('NEW');
    if (failure === 'readonly') h.setReadonly(true);
    if (failure === 'replaced') h.element.env.editor = { ...h.editor };
    if (failure === 'oversized') h.setModel('ğ'.repeat(262145));
    assert.equal(h.bridge.commit(h.getModel()), false);
    assert.equal(h.editor.getValue(), '<?php echo 1;');
    assert.equal(h.field.style.display, 'block');
  }
});
test('height is bounded; clean fallback restores native UI', () => {
  const h = host(); h.bridge.activate();
  h.bridge.resize(900); assert.equal(h.frameHost.style.height, '900px');
  h.bridge.resize(999999); assert.equal(h.frameHost.style.height, '900px');
  assert.equal(h.bridge.useNative(), true);
  assert.equal(h.field.style.display, 'block');
});
test('old instance cleanup cannot unhide an editor owned by the next instance', () => {
  const h = host(); h.bridge.activate();
  const next = createEditorBridge(h.view, h.options); next.activate();
  h.bridge.dispose();
  assert.equal(h.field.style.display, 'none');
  next.dispose(); assert.equal(h.field.style.display, 'block');
});

test('native to Monaco round trip preserves the latest native buffer and readonly state', () => {
  const h = host(); h.bridge.activate(); h.bridge.resize(900);
  assert.equal(h.bridge.useNative(), true);
  assert.equal(h.frameHost.style.height, '88px');
  assert.equal(h.field.style.display, 'block');
  h.editor.setValue('NATIVE_UNSAVED_CONTENT');
  const writes = h.calls.writes;
  h.setReadonly(true);
  assert.equal(h.bridge.useMonaco(), true);
  assert.equal(h.getModel(), 'NATIVE_UNSAVED_CONTENT');
  assert.equal(h.calls.writes, writes);
  assert.equal(h.bridge.readOnly, true);
  assert.equal(h.field.style.display, 'none');
  assert.equal(h.frameHost.style.height, '900px');
  h.bridge.useNative();
  h.element.env.editor = { ...h.editor };
  assert.equal(h.bridge.useMonaco(), false);
  assert.equal(h.field.style.display, 'block');
});

test('save-and-close clicks only the declared native ok button; Ctrl-S remains save-only', () => {
  const h=host();h.bridge.activate();h.setModel('NEW_TEXT');h.bridge.commit(h.getModel());
  assert.equal(h.bridge.canSaveAndClose,true);
  assert.equal(h.bridge.requestSaveAndClose(),true);assert.equal(h.calls.closes,1);assert.equal(h.calls.saves,0);
  assert.equal(h.bridge.requestSave(),true);assert.equal(h.calls.closes,1);assert.equal(h.calls.saves,1);
});
test('save-and-close refuses readonly, disabled, missing, ambiguous and changed targets', () => {
  for(const type of ['readonly','disabled','missing','ambiguous','changed']){
    const h=host();h.bridge.activate();
    if(type==='readonly')h.setReadonly(true);
    if(type==='disabled')h.closeButton.disabled=true;
    if(type==='missing')delete h.options.saveAndCloseButton;
    if(type==='ambiguous')h.closeWrapper.querySelectorAll=()=>[h.closeButton,h.closeButton];
    if(type==='changed')h.options.beforeSave=()=>{h.element.env.editor={...h.editor}};
    assert.equal(h.bridge.requestSaveAndClose(),false,type);assert.equal(h.calls.closes,0,type);
  }
});
