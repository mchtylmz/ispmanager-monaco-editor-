import { getNativeSource } from './native-bridge.mjs';

const OWNER = '__ismonacoEditorOwner';
const ATTRIBUTE = 'data-dynamic-form-element-id';
const validText = (value) => typeof value === 'string' && new TextEncoder().encode(value).length <= 524288;

export function createEditorBridge(view, options) {
  const source = getNativeSource(view);
  if (!source) throw new Error('NATIVE_EDITOR_NOT_READY');
  const { frame, form, field, element, editor } = source;
  if (typeof editor.getReadOnly !== 'function' || typeof editor.setValue !== 'function'
      || typeof editor.on !== 'function' || typeof editor.off !== 'function') throw new Error('NATIVE_API_UNSUPPORTED');
  if (typeof editor.getReadOnly() !== 'boolean') throw new Error('NATIVE_PERMISSION_UNKNOWN');
  const saveIds = options.saveButtons;
  if (!saveIds.length || !saveIds.some((id) => form.querySelectorAll(`[${ATTRIBUTE}="${id}"]`).length === 1)) {
    throw new Error('NATIVE_SAVE_UNSUPPORTED');
  }
  let last = editor.getValue();
  if (!validText(last) || last !== options.getValue()) throw new Error('INITIAL_BUFFER_MISMATCH');
  let writing = false, updating = false, failed = false, released = false, activated = false;
  let nativeMode = false, height = 760;
  let previousDisplay, previousPriority;
  const owner = { frame, release: () => release() };

  function current() {
    const next = getNativeSource(view);
    if (released || !next || next.form !== form || next.field !== field
        || next.editor !== editor || next.element !== element) throw new Error('FORM_CHANGED');
    return editor.getValue();
  }
  function showNative() {
    if (field[OWNER] === owner) {
      field.style.setProperty('display', previousDisplay, previousPriority);
      delete field[OWNER];
    }
  }
  function fault() {
    if (!failed) {
      failed = true;
      showNative();
      options.onFault(); // Keep the Monaco buffer in memory; never log/copy it automatically.
    }
  }
  function synchronized() {
    try { return !failed && current() === options.getValue() && editor.getReadOnly() === false; }
    catch { return false; }
  }
  function guard(event) {
    const id = event.target?.closest?.('isp-form-view-element')?.getAttribute(ATTRIBUTE);
    const shortcut = event.type === 'keydown' && event.code === 'KeyS' && (event.ctrlKey || event.metaKey);
    const save = event.type === 'submit' || shortcut || (event.type === 'click' && saveIds.includes(id));
    if (save && !synchronized()) {
      event.preventDefault(); event.stopImmediatePropagation(); fault();
    } else if (!save && event.type === 'click' && (options.cancelButtons.includes(id)
          || (event.target?.closest?.('button') && event.target?.closest?.('isp-form-view-header-layout-container')))
        && options.getValue() !== last
        && !view.confirm('Monaco değişiklikleri panele aktarılamadı. Kaydetmeden kapatmak istiyor musunuz?')) {
      event.preventDefault(); event.stopImmediatePropagation();
    }
  }
  function nativeChanged() {
    if (writing || failed || released || nativeMode) return;
    try {
      const next = current();
      if (!validText(next) || options.getValue() !== last) throw new Error('BUFFER_CONFLICT');
      last = next;
      updating = true;
      try { options.replaceValue(next); } finally { updating = false; }
      options.onReadOnly(editor.getReadOnly());
    } catch { fault(); }
  }
  function detach() {
    showNative();
    editor.off('change', nativeChanged);
    for (const type of ['click', 'submit', 'keydown']) form.removeEventListener(type, guard, true);
    activated = false;
  }
  function activate() {
    if (activated) return;
    current();
    if (field[OWNER] && field[OWNER].frame !== frame) throw new Error('EDITOR_ALREADY_OWNED');
    field[OWNER]?.release();
    previousDisplay = field.style.getPropertyValue('display');
    previousPriority = field.style.getPropertyPriority('display');
    field[OWNER] = owner;
    editor.on('change', nativeChanged);
    for (const type of ['click', 'submit', 'keydown']) form.addEventListener(type, guard, true);
    field.style.setProperty('display', 'none', 'important');
    activated = true;
  }
  function setHeight(value) {
    const host = frame.closest('isp-form-view-frame-auxiliary');
    if (host) host.style.height = `${value}px`;
  }
  function closeControl() {
    if (released || options.saveAndCloseButton !== 'ok' || !saveIds.includes('ok')) return null;
    const controls = form.querySelectorAll(`[${ATTRIBUTE}="ok"]`);
    if (controls.length !== 1) return null;
    const buttons = controls[0].querySelectorAll('button');
    if (buttons.length !== 1 || !form.contains(buttons[0])) return null;
    return buttons[0];
  }
  function release() {
    if (released) return;
    detach();
    released = true;
  }
  return {
    get readOnly() { return nativeMode || failed || editor.getReadOnly() !== false; },
    get canSaveAndClose() { return !!closeControl(); },
    get hasPending() { return !nativeMode && options.getValue() !== last; },
    activate,
    commit(value) {
      if (updating) return true;
      try {
        if (nativeMode || failed || !validText(value) || current() !== last || editor.getReadOnly() !== false) throw new Error('SYNC_REFUSED');
        writing = true;
        try { editor.setValue(value, -1); } finally { writing = false; }
        if (current() !== value) throw new Error('SYNC_MISMATCH');
        last = value;
        return true;
      } catch { fault(); return false; }
    },
    requestSave() {
      if (nativeMode) return false;
      if (!synchronized()) { fault(); return false; }
      options.beforeSave?.(); // Reveal native result/error UI before submitting.
      const host = field.querySelector('isp-form-view-code-field');
      if (!host) return false;
      host.dispatchEvent(new view.KeyboardEvent('keydown', {
        key: 's', code: 'KeyS', ctrlKey: true, bubbles: true, cancelable: true,
      }));
      return true; // Submitted through native UI; not a server-save acknowledgement.
    },
    requestSaveAndClose() {
      if (nativeMode) return false;
      if (!synchronized()) { fault(); return false; }
      const button = closeControl();
      if (!button || button.disabled || button.getAttribute('aria-disabled') === 'true') return false;
      options.beforeSave?.();
      // Fullscreen exit must not retarget the form or button before the click.
      if (!synchronized() || closeControl() !== button || button.disabled) return false;
      button.click(); // Native ok action owns the request, errors and eventual close.
      return true;
    },
    useNative() {
      if (options.getValue() !== last
          && !view.confirm('Monaco değişiklikleri panele aktarılamadı. Metni kopyalamadan mevcut editöre dönmek istiyor musunuz?')) return false;
      detach();
      nativeMode = true;
      setHeight(88); // Only a switch-back toolbar remains; Monaco itself is hidden.
      return true;
    },
    useMonaco() {
      if (!nativeMode) return false;
      try {
        const next = current();
        if (!validText(next) || typeof editor.getReadOnly() !== 'boolean') throw new Error('NATIVE_BUFFER_UNSUPPORTED');
        updating = true;
        try { options.replaceValue(next); } finally { updating = false; }
        if (options.getValue() !== next) throw new Error('BUFFER_MISMATCH');
        last = next;
        failed = false;
        activate();
        nativeMode = false;
        options.onReadOnly(editor.getReadOnly());
        setHeight(height);
        return true;
      } catch {
        detach(); // Failed return always leaves the native editor accessible.
        return false;
      }
    },
    resize(value) {
      if (![620, 760, 900, 1080].includes(value)) return;
      height = value;
      if (!nativeMode) setHeight(height);
    },
    dispose: release,
  };
}
