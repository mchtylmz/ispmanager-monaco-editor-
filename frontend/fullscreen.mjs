import { getNativeSource } from './native-bridge.mjs';

// Promote only this frame's existing wrapper. No reparenting or panel-wide CSS.
export function createFullscreen(view, onChange = () => {}) {
  const source = getNativeSource(view);
  if (!source) throw new Error('NO_FULLSCREEN_SOURCE');
  const { frame, form, field, editor } = source;
  const target = frame.closest('isp-form-view-element');
  const host = frame.closest('isp-form-view-frame-auxiliary');
  let active = false, saved = [], observer;
  const styles = {
    position: 'fixed', inset: '0', width: '100vw', height: '100dvh',
    'max-width': 'none', 'max-height': 'none', margin: '0', padding: '0',
    border: '0', 'box-sizing': 'border-box', display: 'block', background: '#1e1e1e',
  };
  function patch(node, values) {
    for (const [name, value] of Object.entries(values)) {
      saved.push([node, name, node.style.getPropertyValue(name), node.style.getPropertyPriority(name)]);
      node.style.setProperty(name, value, 'important');
    }
  }
  function restore() {
    for (const [node, name, value, priority] of saved.splice(0).reverse()) {
      if (value) node.style.setProperty(name, value, priority);
      else node.style.removeProperty(name);
    }
  }
  function exit() {
    if (!active) return;
    active = false;
    observer?.disconnect();
    form.ownerDocument.removeEventListener('visibilitychange', visibility);
    try { target.hidePopover(); } catch { /* A removed frame may already be hidden. */ }
    target.removeAttribute('popover'); // Removing it restores the inline display.
    restore();
    onChange(false);
  }
  function visibility() {
    if (!target.isConnected || form.ownerDocument.hidden || form.closest?.('[hidden]') || form.getClientRects().length === 0) exit();
  }
  return {
    get active() { return active; },
    enter() {
      if (active) return true;
      try {
        const next = getNativeSource(view);
        if (!next || next.form !== form || next.field !== field || next.editor !== editor
            || !host || target.hasAttribute('popover') || typeof target.showPopover !== 'function') return false;
        patch(target, styles);
        patch(host, { height: '100%', width: '100%' });
        patch(frame, { height: '100%', width: '100%', border: '0', display: 'block', 'box-sizing': 'border-box' });
        target.setAttribute('popover', 'manual');
        target.showPopover();
        active = true;
        observer = new view.MutationObserver(visibility);
        for (let node = form; node; node = node.parentElement) {
          observer.observe(node, { attributes: true, childList: true });
        }
        form.ownerDocument.addEventListener('visibilitychange', visibility);
        onChange(true);
        return true;
      } catch {
        if (active) exit();
        else {
          target.removeAttribute('popover');
          restore();
        }
        return false;
      }
    },
    exit,
    dispose: exit,
  };
}
