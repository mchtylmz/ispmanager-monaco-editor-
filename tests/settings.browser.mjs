// Browser plugin not available. Actual backend and the hash-pinned Phoenix submit
// method are exercised locally; tab service/rendering and JSON conversion are a harness.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE));
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
const errors = [], requests = [];
page.on('pageerror', e => errors.push(e.message));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('request', r => requests.push(r.url()));
const fields = { theme: 'Tema', font_size: 'Yazı boyutu', wrap: 'Satır kaydır', minimap: 'Kod haritası', height: 'Editör yüksekliği', fullscreen: 'Varsayılan tam ekran' };
async function open(query = '') {
  await page.goto('http://127.0.0.1:8767/' + query);
  await page.locator('html[data-ready=true]').waitFor();
  assert.equal(await page.title(), 'Native settings submit regression');
}
async function save() {
  const before = await page.evaluate(() => window.submissions);
  await page.getByRole('button', { name: 'Kaydet', exact: true }).click();
  await page.waitForFunction(count => window.submissions === count + 1, before);
}
async function completeForm() {
  assert.equal(await page.locator('#settings select').count(), 6);
  assert.equal(await page.locator('#title').innerText(), 'Monaco — Sunucu varsayılanları');
  assert.equal(await page.locator('#closed').isVisible(), false);
}
try {
  // Reproduce the reported bug with the exact old 0.2.2 handler and native method.
  await open('?legacy=true&standalone=true'); await completeForm(); await save();
  assert.equal(await page.locator('#settings select').count(), 0);
  assert.equal(await page.locator('#title').innerText(), '');
  for (const standalone of ['true', 'false']) {
    await open('?standalone=' + standalone); await completeForm();
    const values = { theme: 'light', font_size: '16', wrap: 'off', minimap: 'on', height: '900', fullscreen: 'off' };
    for (const [name, value] of Object.entries(values)) await page.getByLabel(fields[name], { exact: true }).selectOption(value);
    await save(); await completeForm();
    assert.equal(await page.getByRole('status').innerText(), 'Ayarlar kaydedildi.');
    for (const [name, value] of Object.entries(values)) assert.equal(await page.getByLabel(fields[name], { exact: true }).inputValue(), value);
    await page.reload(); await page.locator('html[data-ready=true]').waitFor(); await completeForm();
    assert.equal(await page.getByRole('status').innerText(), '');
    for (const [name, value] of Object.entries(values)) assert.equal(await page.getByLabel(fields[name], { exact: true }).inputValue(), value);
    await page.getByLabel(fields.fullscreen, { exact: true }).selectOption('on');
    await save(); await completeForm();
    assert.equal(await page.getByLabel(fields.fullscreen, { exact: true }).inputValue(), 'on');
  }
  await page.screenshot({ path: '/tmp/ismonaco-settings-saved.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: '/tmp/ismonaco-settings-saved-mobile.png', fullPage: true });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.setViewportSize({ width: 1200, height: 900 });
  // A failed save immediately after success must also clear the old success text.
  await page.getByLabel(fields.theme, { exact: true }).evaluate(select => { const option = new Option('invalid', 'PRIVATE_INPUT_INVALID'); select.add(option); select.value=option.value; });
  await save(); await completeForm();
  assert.match(await page.getByRole('alert').innerText(), /Ayarlar kaydedilemedi/);
  assert.equal(await page.getByRole('status').innerText(), '');
  assert.equal((await page.locator('body').innerText()).includes('PRIVATE_INPUT'), false);
  await page.reload(); await page.locator('html[data-ready=true]').waitFor();
  assert.equal(await page.getByLabel(fields.theme, { exact: true }).inputValue(), 'light');
  await open('?io=true&standalone=true');
  await page.getByLabel(fields.font_size, { exact: true }).selectOption('20');
  await save(); await completeForm();
  assert.match(await page.getByRole('alert').innerText(), /Ayarlar kaydedilemedi/);
  assert.equal(await page.getByRole('status').innerText(), '');
  await page.reload(); await page.locator('html[data-ready=true]').waitFor();
  assert.equal(await page.getByLabel(fields.font_size, { exact: true }).inputValue(), '16');
  await open('?role=normal');
  assert.equal(await page.locator('#settings select').count(), 0);
  assert.match(await page.getByRole('alert').innerText(), /yalnızca root/);
  assert.deepEqual(errors, []);
  assert.equal(requests.every(url => url.startsWith('http://127.0.0.1:8767/')), true);
  console.log('SETTINGS_BROWSER_OK: exact 0.2.2 blank reproduced; actual backend + native submit method; standalone/normal save/reload/repeated save; visible invalid/IO/access errors; 1200/390px; temporary config only');
} finally { await browser.close(); }
