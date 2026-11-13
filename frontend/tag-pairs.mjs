const VOID = new Set('area base br col embed hr img input link meta param source track wbr'.split(' '));

// Consume Monaco's HTML tokens, so PHP strings/comments and script bodies are
// never parsed as markup. Work is bounded by the existing 512 KiB editor limit.
export function buildTagPairs(lines, tokens, eol = '\n') {
  const tags = [], pairs = new Map(), stack = [], counts = new Map();
  let offset = 0, pending;
  for (let row = 0; row < lines.length; row++) {
    const line = lines[row], items = tokens[row] || [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i], text = line.slice(item.offset, items[i + 1]?.offset ?? line.length);
      if (item.type === 'tag.html') {
        const match = /^[\w:-]+/.exec(text);
        const prefix = line.slice(Math.max(0, item.offset - 2), item.offset);
        if (match && (prefix.endsWith('<') || prefix.endsWith('</'))) {
          const closing = prefix.endsWith('</');
          pending = { name: match[0].toLowerCase(), closing, start: offset + item.offset - (closing ? 2 : 1),
            nameStart: offset + item.offset, nameEnd: offset + item.offset + match[0].length };
        }
      } else if (pending && item.type === 'delimiter.html' && /^(?:\/?>)$/.test(text)) {
        const tag = { ...pending, end: offset + item.offset + text.length };
        if (tags.length >= 20000) return { tags: [], pairs: new Map() };
        tags.push(tag); pending = undefined;
        if (!tag.closing && text !== '/>' && !VOID.has(tag.name)) {
          stack.push(tag); counts.set(tag.name, (counts.get(tag.name) || 0) + 1);
        } else if (tag.closing && counts.get(tag.name)) {
          let open;
          do { open = stack.pop(); counts.set(open.name, counts.get(open.name) - 1); } while (open.name !== tag.name);
          pairs.set(open.start, tag); pairs.set(tag.start, open);
        }
      }
    }
    offset += line.length + eol.length;
  }
  return { tags, pairs };
}

export function tagPairAt(index, offset) {
  let low = 0, high = index.tags.length - 1, candidate;
  while (low <= high) {
    const middle = (low + high) >> 1, tag = index.tags[middle];
    if (tag.start <= offset) { candidate = tag; low = middle + 1; } else high = middle - 1;
  }
  const pair = candidate && offset <= candidate.end && index.pairs.get(candidate.start);
  return pair ? [candidate, pair] : [];
}

export function attachTagHighlights(monaco, editor, model, label) {
  let timer, index = { tags: [], pairs: new Map() };
  const decorations = editor.createDecorationsCollection();
  function update() {
    const matches = tagPairAt(index, model.getOffsetAt(editor.getPosition()));
    decorations.set(matches.map(tag => ({
      range: monaco.Range.fromPositions(model.getPositionAt(tag.nameStart), model.getPositionAt(tag.nameEnd)),
      options: { inlineClassName: 'ismonaco-tag-match', overviewRuler: { color: '#d49b23', position: monaco.editor.OverviewRulerLane.Right } },
    })));
    label.hidden = matches.length === 0;
    label.textContent = matches.length ? `${matches[0].name}: ${model.getPositionAt(matches[0].nameStart).lineNumber} ↔ ${model.getPositionAt(matches[1].nameStart).lineNumber}` : '';
  }
  function scan() {
    clearTimeout(timer);
    index = ['html', 'php'].includes(model.getLanguageId())
      ? buildTagPairs(model.getLinesContent(), monaco.editor.tokenize(model.getValue(), model.getLanguageId()), model.getEOL())
      : { tags: [], pairs: new Map() };
    update();
  }
  const listeners = [editor.onDidChangeCursorPosition(update), model.onDidChangeContent(() => {
    index = { tags: [], pairs: new Map() }; update(); clearTimeout(timer); timer = setTimeout(scan, 160);
  }), model.onDidChangeLanguage(scan)];
  scan();
  return { dispose() { clearTimeout(timer); listeners.forEach(listener => listener.dispose()); decorations.clear(); } };
}
