import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DEFAULT_PREFERENCES, normalizePreferences, parseConfiguration } from '../frontend/preferences.mjs';

test('requested defaults match the server payload exactly', () => {
  const server = JSON.parse(readFileSync(new URL('../integration/editor/defaults.json', import.meta.url)));
  assert.deepEqual(DEFAULT_PREFERENCES, server);
  assert.deepEqual(normalizePreferences(), server);
});
test('appearance settings cannot inject content, privileges or invalid dimensions', () => {
  const result = normalizePreferences({ theme: 'remote', height: 999999, fontSize: false,
    wrap: 'on', minimap: false, readOnly: false, content: 'PRIVATE', role: 'root' });
  assert.equal(result.theme, 'dark');
  assert.equal(result.height, 760);
  assert.equal(result.minimap, false);
  assert.equal(result.fullscreen, true);
  assert.equal(normalizePreferences({ fullscreen: false }).fullscreen, false);
  assert.equal(normalizePreferences({ fullscreen: 'false' }).fullscreen, true);
  assert.equal('content' in result, false);
  assert.equal('readOnly' in result, false);
});
test('boot configuration is bounded and native control ids are allowlisted', () => {
  const valid = { version: 1, saveButtons: ['apply', 'apply'], cancelButtons: ['cancel'],
    canConfigure: true, preferences: { height: 900, wrap: false } };
  const encode = (v) => '#' + new URLSearchParams({ boot: JSON.stringify(v) });
  const result = parseConfiguration(encode(valid));
  assert.deepEqual(result.saveButtons, ['apply']);
  assert.equal(result.preferences.height, 900);
  assert.equal(result.preferences.wrap, false);
  assert.equal(result.canConfigure, true);
  for (const value of ['', '#' + 'x'.repeat(4096), '#boot=invalid',
    encode({ ...valid, saveButtons: ['a"] button'] }), encode({ ...valid, saveButtons: Array(9).fill('ok') }), encode({ ...valid, saveAndCloseButton: 'cancel' }), encode({ ...valid, saveAndCloseButton: 'ok' })]) {
    assert.throws(() => parseConfiguration(value));
  }
});
