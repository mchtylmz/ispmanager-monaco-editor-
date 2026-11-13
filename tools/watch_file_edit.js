// Temporary DevTools diagnostic. Observe one native request; send none ourselves.
// Never read credentials, headers, storage, cookies, file text or error messages into output.
(() => {
  const key = '__ismonacoPreviewDiagnosticStop';
  if (typeof globalThis[key] === 'function') globalThis[key]();
  const prototype = XMLHttpRequest.prototype;
  const original = prototype.send;
  let active = true;
  let timer;

  function stop() {
    active = false;
    if (prototype.send === watchedSend) prototype.send = original;
    clearTimeout(timer);
    if (globalThis[key] === stop) delete globalThis[key];
  }

  function inspect() {
    if (!active) return;
    let url;
    try { url = new URL(this.responseURL, location.href); } catch { return; }
    if (url.origin !== location.origin || url.pathname !== '/ispmgr'
        || url.searchParams.get('func') !== 'file.edit') return;
    stop();
    const report = { status: 'OK', httpStatus: this.status, format: 'unknown',
      metadataKeyPresent: false, previewDataKeyPresent: false,
      previewNamedElementPresent: false, htmlDataKeyPresent: false, errorKeyPresent: false };
    try {
      const isJSON = this.responseType === 'json';
      if (!isJSON && !['', 'text'].includes(this.responseType)) throw new Error();
      const text = isJSON ? null : this.responseText;
      if (text !== null && (typeof text !== 'string' || text.length > 4194304)) throw new Error();
      if (!isJSON && text.trimStart().startsWith('<')) {
        report.format = 'xml';
        if (/<!DOCTYPE|<!ENTITY/i.test(text)) throw new Error();
        const xml = new DOMParser().parseFromString(text, 'application/xml');
        if (xml.querySelector('parsererror')) throw new Error();
        report.metadataKeyPresent = !!xml.querySelector('metadata');
        report.previewDataKeyPresent = !!xml.querySelector('ismonaco_preview');
        report.previewNamedElementPresent = !!xml.querySelector('[name="ismonaco_preview"]');
        report.htmlDataKeyPresent = !!xml.querySelector('htmldata');
        report.errorKeyPresent = !!xml.querySelector('error');
      } else {
        report.format = 'json';
        const pending = [{ value: isJSON ? this.response : JSON.parse(text), depth: 0 }];
        let count = 0;
        while (pending.length) {
          const { value, depth } = pending.pop();
          if (++count > 20000 || depth > 40) throw new Error();
          if (!value || typeof value !== 'object') continue;
          for (const [name, child] of Object.entries(value)) {
            if (name === 'metadata') report.metadataKeyPresent = true;
            if (name === 'ismonaco_preview') report.previewDataKeyPresent = true;
            if (/^[@$]?name$/.test(name) && child === 'ismonaco_preview') report.previewNamedElementPresent = true;
            if (name === 'htmldata') report.htmlDataKeyPresent = true;
            if (name === 'error') report.errorKeyPresent = true;
            // Do not inspect string values: they can contain file contents.
            if (child && typeof child === 'object') pending.push({ value: child, depth: depth + 1 });
          }
        }
      }
    } catch {
      report.status = 'UNSUPPORTED_RESPONSE';
    }
    console.log('MONACO_NATIVE_CHECK\n' + JSON.stringify(report, null, 2));
  }

  function watchedSend(...args) {
    try { this.addEventListener('load', inspect, { once: true }); } catch { /* Native call still proceeds. */ }
    return original.apply(this, args);
  }
  prototype.send = watchedSend;
  globalThis[key] = stop;
  timer = setTimeout(() => {
    if (active) { stop(); console.log('MONACO_NATIVE_CHECK_TIMEOUT'); }
  }, 120000);
  console.log('MONACO_IZLEME_HAZIR: Kaydedilmemiş değişiklik yoksa Düzenle sekmesini kapatıp dosyayı yeniden açın.');
})();
