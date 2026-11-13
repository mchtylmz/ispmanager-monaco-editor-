import test from 'node:test';
import assert from 'node:assert/strict';
import { validateBoot, editorOptions, guessLanguage } from '../frontend/state.mjs';

test('source text stays data and language selection is allowlisted', () => {
  const content = '</script><script>throw 1</script><?php $a = "İstanbul";';
  assert.deepEqual(validateBoot({ version: 1, readOnly: true, content, language: 'php' }), { content, language: 'php' });
  assert.equal(validateBoot({ version: 1, readOnly: true, content, language: 'https://remote' }).language, 'plaintext');
  assert.equal(guessLanguage('<?php echo 1;'), 'php');
});

test('editable or oversized bootstrap data is rejected', () => {
  for (const value of [null, {}, { version: 1, readOnly: false, content: '' },
    { version: 1, readOnly: true, content: 'ğ'.repeat(262145) }]) {
    assert.throws(() => validateBoot(value), /INVALID_BOOT/);
  }
});

test('settings cannot enable editing, links or unbounded font sizes', () => {
  const options = editorOptions({ readOnly: false, fontSize: 999, wrap: true, minimap: true });
  assert.equal(options.readOnly, true);
  assert.equal(options.domReadOnly, true);
  assert.equal(options.fontSize, 14);
  assert.equal(options.wordWrap, 'on');
  assert.equal(options.links, false);
  assert.equal(editorOptions({ fontSize: 18 }).fontSize, 18);
});
