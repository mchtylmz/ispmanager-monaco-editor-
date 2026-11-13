// Read a snapshot of only the native editor in this frame's own Phoenix form.
// No panel requests, tokens, storage, messages, host mutations or global fallback.
function binding(view) {
  const frame = view.frameElement;
  if (!frame || view.parent === view) throw new Error('NOT_EMBEDDED');
  const wrapper = frame.closest('isp-form-view-element');
  if (wrapper?.getAttribute('data-dynamic-form-element-id') !== 'ismonaco_preview-frame') {
    throw new Error('WRONG_FRAME_BINDING');
  }
  const form = frame.closest('isp-new-dynamic-form');
  if (!form?.isConnected) throw new Error('NO_NATIVE_FORM');
  return { frame, form };
}

export function getNativeSource(view) {
  const { frame, form } = binding(view);
  const fields = form.querySelectorAll('[data-dynamic-form-element-id="fdata-code-element"]');
  if (fields.length > 1) throw new Error('AMBIGUOUS_NATIVE_FIELD');
  if (fields.length === 0) return null;
  const editors = fields[0].querySelectorAll('ace-editor');
  if (editors.length > 1) throw new Error('AMBIGUOUS_NATIVE_EDITOR');
  if (editors.length === 0) return null;
  const element = editors[0];
  const editor = element.env?.editor;
  if (!editor || editor.container !== element || typeof editor.getValue !== 'function') return null;
  return { frame, form, field: fields[0], element, editor };
}

export function readFilePath(view) {
  const source = getNativeSource(view);
  if (!source) return '';
  const fields = source.form.querySelectorAll('[data-dynamic-form-element-id="full_filepath-textdata"]');
  if (fields.length !== 1) return '';
  const values = fields[0].querySelectorAll('isp-form-view-text-auxiliary .text-block');
  if (values.length !== 1) return '';
  const path = values[0].textContent?.trim();
  return typeof path === 'string' && path.startsWith('/') && !/[\x00-\x1f\x7f]/.test(path)
    && new TextEncoder().encode(path).length <= 4096 ? path : '';
}

export function readSnapshot(view) {
  const source = getNativeSource(view);
  if (!source) return null;
  const { frame, form, element, editor } = source;
  const content = editor.getValue(); // Ace's read-only public API; never setValue/execCommand.
  if (!form.isConnected || frame.closest('isp-new-dynamic-form') !== form
      || !form.contains(element)) throw new Error('FORM_CHANGED');
  if (typeof content !== 'string' || new TextEncoder().encode(content).length > 524288) {
    throw new Error('NATIVE_CONTENT_REJECTED');
  }
  return { version: 1, readOnly: true, content };
}

export async function waitForSnapshot(view, signal, timeoutMs = 5000) {
  const end = Date.now() + timeoutMs;
  while (!signal?.aborted) {
    const snapshot = readSnapshot(view);
    if (snapshot) return snapshot;
    if (Date.now() >= end) throw new Error('NATIVE_EDITOR_TIMEOUT');
    await new Promise((resolve, reject) => {
      let timer;
      const abort = () => { clearTimeout(timer); reject(new Error('ABORTED')); };
      signal?.addEventListener('abort', abort, { once: true });
      timer = setTimeout(() => { signal?.removeEventListener('abort', abort); resolve(); }, 50);
    });
  }
  throw new Error('ABORTED');
}
