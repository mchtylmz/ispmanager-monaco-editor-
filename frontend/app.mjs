import * as monaco from 'monaco-editor/editor/editor.api.js';
import '../node_modules/monaco-editor/esm/vs/base/browser/ui/codicons/codicon/codicon.css';
import 'monaco-editor/editor/contrib/find/browser/findController.js';
import { conf as phpConf, language as phpTokens } from 'monaco-editor/languages/definitions/php/php.js';
import { conf as htmlConf, language as htmlTokens } from 'monaco-editor/languages/definitions/html/html.js';
import 'monaco-editor/languages/definitions/css/register.js';
import 'monaco-editor/languages/definitions/javascript/register.js';
import 'monaco-editor/languages/definitions/typescript/register.js';
import 'monaco-editor/languages/definitions/sql/register.js';
import 'monaco-editor/languages/definitions/markdown/register.js';
import 'monaco-editor/languages/definitions/xml/register.js';
import 'monaco-editor/languages/definitions/yaml/register.js';
import 'monaco-editor/languages/definitions/shell/register.js';
import 'monaco-editor/languages/definitions/python/register.js';
import { createTokenizationSupport } from 'monaco-editor/languages/features/json/tokenization.js';
import './style.css';
import { LANGUAGES, editorOptions, validateBoot } from './state.mjs';
import { readFilePath, waitForSnapshot } from './native-bridge.mjs';
import { createEditorBridge } from './editor-bridge.mjs';
import { parseConfiguration } from './preferences.mjs';
import { createFullscreen } from './fullscreen.mjs';
import { attachTagHighlights } from './tag-pairs.mjs';
import 'monaco-editor/editor/contrib/bracketMatching/browser/bracketMatching.js';

globalThis.MonacoEnvironment = {
  getWorker() {
    return new Worker(new URL('./editor.worker.js', import.meta.url), { type: 'module' });
  },
};

for (const [id, configuration, tokens] of [['html', htmlConf, htmlTokens], ['php', phpConf, phpTokens]]) {
  monaco.languages.register({ id });
  monaco.languages.setLanguageConfiguration(id, configuration);
  monaco.languages.setMonarchTokensProvider(id, tokens);
}
for (const [name, base, background, border] of [['ismonaco-dark', 'vs-dark', '#eab30826', '#e4b341'], ['ismonaco-light', 'vs', '#cf8b1726', '#a36512']]) {
  monaco.editor.defineTheme(name, { base, inherit: true, rules: [], colors: {
    'editorBracketMatch.background': background, 'editorBracketMatch.border': border,
  } });
}

monaco.languages.register({ id: 'json', aliases: ['JSON'] });
monaco.languages.setTokensProvider('json', createTokenizationSupport(true));

let editor;
let model;
let bridge;
let fullscreen;
const listeners = [];
const lifecycle = new AbortController();
function listen(node, event, action) {
  node.addEventListener(event, action);
  listeners.push(() => node.removeEventListener(event, action));
}

async function start() {
  const configuration = parseConfiguration(location.hash);
  const preferences = configuration.preferences;
  const boot = validateBoot(await waitForSnapshot(window, lifecycle.signal));
  if (lifecycle.signal.aborted) return;
  const select = document.getElementById('language');
  for (const [id, label] of LANGUAGES) select.add(new Option(label, id));
  select.value = boot.language;
  model = monaco.editor.createModel(boot.content, boot.language);
  editor = monaco.editor.create(document.getElementById('editor'), {
    ...editorOptions(preferences), model, theme: preferences.theme === 'dark' ? 'ismonaco-dark' : 'ismonaco-light', ariaLabel: 'Monaco dosya editörü',
  });
  const currentValue = () => model.getValue(undefined, true); // Preserve BOM and the model's EOL.
  const readonly = (value) => {
    editor.updateOptions({ readOnly: value !== false, domReadOnly: value !== false });
    document.getElementById('fullscreen-save').disabled = value !== false;
    document.getElementById('fullscreen-save-close').disabled = value !== false || !bridge?.canSaveAndClose;
    document.getElementById('mode').textContent = value !== false ? 'Salt okunur' : 'Düzenlenebilir';
  };
  bridge = createEditorBridge(window, {
    ...configuration, getValue: currentValue, replaceValue: (value) => model.setValue(value),
    onReadOnly: readonly,
    beforeSave: () => fullscreen?.exit(),
    onFault: () => {
      fullscreen?.exit();
      readonly(true);
      document.getElementById('status').textContent = 'Aktarım durdu. Monaco metnini kopyalayabilir veya mevcut editöre dönebilirsiniz.';
      document.getElementById('copy-buffer').hidden = false;
    },
  });
  readonly(bridge.readOnly);
  const path = readFilePath(window);
  document.getElementById('file-path').textContent = path;
  document.getElementById('file-path').title = path;
  document.getElementById('file-path').hidden = true;
  const tags = attachTagHighlights(monaco, editor, model, document.getElementById('tag-pair'));
  listeners.push(() => tags.dispose());
  document.documentElement.dataset.theme = preferences.theme;
  document.getElementById('theme').value = preferences.theme;
  document.getElementById('font').value = String(preferences.fontSize);
  document.getElementById('wrap').checked = preferences.wrap;
  document.getElementById('minimap').checked = preferences.minimap;
  document.getElementById('height').value = String(preferences.height);
  bridge.resize(preferences.height);
  fullscreen = createFullscreen(window, (active) => {
    const button = document.getElementById('fullscreen');
    document.getElementById('fullscreen-label').textContent = active ? 'Tam ekrandan çık' : 'Tam ekran';
    document.getElementById('escape-hint').hidden = !active;
    document.getElementById('file-path').hidden = !active || !path;
    button.setAttribute('aria-pressed', String(active));
    document.getElementById('height').disabled = active;
    document.getElementById('fullscreen-save').hidden = !active;
    document.getElementById('fullscreen-save-close').hidden = !active;
    editor.layout();
    if (active) editor.focus();
  });
  const changes = model.onDidChangeContent(() => {
    if (bridge.commit(currentValue())) document.getElementById('status').textContent = 'Kaydetmeye hazır — panelin Kaydet düğmesini kullanın.';
  });
  listeners.push(() => changes.dispose());
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
    if (!bridge.requestSave()) document.getElementById('status').textContent = 'Panelin Kaydet düğmesini kullanın.';
  });
  // Appearance defaults come from the server. No browser storage or credentials.
  listen(select, 'change', () => monaco.editor.setModelLanguage(model, select.value));
  listen(document.getElementById('theme'), 'change', (event) => {
    monaco.editor.setTheme(event.target.value === 'dark' ? 'ismonaco-dark' : 'ismonaco-light');
    document.documentElement.dataset.theme = event.target.value === 'dark' ? 'dark' : 'light';
  });
  listen(document.getElementById('font'), 'change', (event) => {
    editor.updateOptions({ fontSize: editorOptions({ fontSize: Number(event.target.value) }).fontSize });
  });
  listen(document.getElementById('wrap'), 'change', (event) => {
    editor.updateOptions({ wordWrap: event.target.checked ? 'on' : 'off' });
  });
  listen(document.getElementById('minimap'), 'change', (event) => {
    editor.updateOptions({ minimap: { enabled: event.target.checked } });
  });
  listen(document.getElementById('height'), 'change', (event) => bridge.resize(Number(event.target.value)));
  const setNativeMode = (active) => {
    for (const id of ['toolbar', 'editor', 'editor-footer']) document.getElementById(id).hidden = active;
    document.getElementById('native-view').hidden = !active;
    if (!active) { editor.layout(); editor.focus(); }
  };
  listen(document.getElementById('native-editor'), 'click', () => {
    fullscreen.exit();
    if (bridge.useNative()) { readonly(true); setNativeMode(true); }
  });
  listen(document.getElementById('advanced-editor'), 'click', () => {
    if (bridge.useMonaco()) {
      setNativeMode(false);
      document.getElementById('copy-buffer').hidden = true;
      document.getElementById('native-status').textContent = 'Metin editörü etkin.';
      document.getElementById('status').textContent = bridge.readOnly ? 'Salt okunur dosya' : 'Düzenlemeye hazır';
    } else {
      document.getElementById('native-status').textContent = 'Geçiş yapılamadı. Mevcut editör kullanılabilir; dosyayı yeniden açabilirsiniz.';
    }
  });
  listen(document.getElementById('fullscreen'), 'click', () => {
    if (fullscreen.active) fullscreen.exit();
    else if (!fullscreen.enter()) document.getElementById('status').textContent = 'Tam ekran açılamadı; normal görünüm kullanılabilir.';
    editor.focus();
  });
  listen(document.getElementById('fullscreen-save'), 'click', () => {
    if (!bridge.requestSave()) document.getElementById('status').textContent = 'Panelin Kaydet düğmesini kullanın.';
  });
  listen(document.getElementById('fullscreen-save-close'), 'click', () => {
    if (!bridge.requestSaveAndClose()) document.getElementById('status').textContent = 'Panelin Kaydet ve kapat düğmesini kullanın.';
  });
  listen(window, 'keydown', (event) => {
    if (event.key === 'Escape' && !event.defaultPrevented && fullscreen.active) {
      event.preventDefault(); fullscreen.exit(); editor.focus();
    }
  });
  listen(document.getElementById('copy-buffer'), 'click', async () => {
    try {
      await navigator.clipboard.writeText(currentValue());
      document.getElementById('status').textContent = 'Monaco metni kopyalandı.';
    } catch { document.getElementById('status').textContent = 'Metni editörden seçip kopyalayabilirsiniz.'; }
  });
  listen(document.getElementById('find'), 'click', () => {
    editor.focus();
    editor.getAction('actions.find').run();
  });
  const position = document.getElementById('position');
  const subscription = editor.onDidChangeCursorPosition(({ position: cursor }) => {
    position.textContent = `Satır ${cursor.lineNumber}, sütun ${cursor.column}`;
  });
  listeners.push(() => subscription.dispose());
  bridge.activate(); // Hide native UI only after editor creation and binding checks succeed.
  document.getElementById('status').textContent = bridge.readOnly ? 'Salt okunur dosya' : 'Düzenlemeye hazır';
  document.documentElement.dataset.ready = 'true';
  if (preferences.fullscreen) fullscreen.enter();
}

function dispose() {
  lifecycle.abort();
  listeners.splice(0).forEach((remove) => remove());
  fullscreen?.dispose();
  fullscreen = undefined;
  bridge?.dispose();
  bridge = undefined;
  editor?.dispose();
  model?.dispose();
  editor = undefined;
  model = undefined;
}
window.addEventListener('pagehide', (event) => {
  if (!event.persisted) dispose();
});
window.addEventListener('beforeunload', (event) => {
  if (bridge?.hasPending) { event.preventDefault(); event.returnValue = ''; }
});
start().catch(() => {
  dispose();
  document.getElementById('status').textContent = 'Monaco açılamadı. Panelin mevcut editörünü kullanın.';
  document.documentElement.dataset.ready = 'false';
});
