export const LANGUAGES = Object.freeze([
  ['plaintext', 'Düz metin'], ['php', 'PHP'], ['html', 'HTML'],
  ['css', 'CSS'], ['javascript', 'JavaScript'], ['typescript', 'TypeScript'],
  ['json', 'JSON'], ['sql', 'SQL'], ['markdown', 'Markdown'],
  ['xml', 'XML'], ['yaml', 'YAML'], ['shell', 'Shell'], ['python', 'Python'],
]);

export function validateBoot(value) {
  if (!value || value.version !== 1 || value.readOnly !== true
      || typeof value.content !== 'string'
      || new TextEncoder().encode(value.content).length > 524288) {
    throw new Error('INVALID_BOOT');
  }
  return { content: value.content, language: LANGUAGES.some(([id]) => id === value.language)
    ? value.language : guessLanguage(value.content) };
}

export function guessLanguage(content) {
  const prefix = content.trimStart().slice(0, 100).toLowerCase();
  if (prefix.startsWith('<?php')) return 'php';
  if (prefix.startsWith('<!doctype html') || prefix.startsWith('<html')) return 'html';
  if (prefix.startsWith('<?xml')) return 'xml';
  return 'plaintext';
}

export function editorOptions(settings = {}, readOnly = true) {
  const fontSize = [12, 14, 16, 18, 20].includes(settings.fontSize) ? settings.fontSize : 14;
  return {
    readOnly: readOnly !== false, domReadOnly: readOnly !== false, automaticLayout: true,
    fontSize, wordWrap: settings.wrap === true ? 'on' : 'off',
    minimap: { enabled: settings.minimap === true },
    matchBrackets: 'always', bracketPairColorization: { enabled: true },
    guides: { bracketPairs: true, highlightActiveBracketPair: true },
    tabSize: 4, insertSpaces: true, scrollBeyondLastLine: false,
    unicodeHighlight: { ambiguousCharacters: false },
    // A source file is data. No Markdown links, suggestions or project providers.
    links: false, hover: { enabled: false }, contextmenu: false,
    quickSuggestions: false, suggestOnTriggerCharacters: false,
    accessibilitySupport: 'on', renderWhitespace: 'selection',
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
  };
}
