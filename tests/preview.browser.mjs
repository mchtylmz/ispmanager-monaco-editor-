// Browser plugin not available. Use an installed Playwright module and Chrome.
// Run against tools/preview_server.py, never a live panel or user site.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';

if (!process.env.PLAYWRIGHT_MODULE) throw new Error('Set PLAYWRIGHT_MODULE to installed playwright/index.mjs');
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE));
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
const warnings = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('console', (message) => {
  if (message.type() === 'error') errors.push(message.text());
  if (message.type() === 'warning') warnings.push(message.text());
});
const requests = [];
page.on('request', (request) => requests.push(request.url()));
try {
  for (const route of ['/', '/normal', '/slow']) {
    await page.goto('http://127.0.0.1:8765' + route);
    assert.equal(await page.title(), 'Monaco yerel entegrasyon testi');
    assert.equal(new URL(page.url()).pathname, route);
    const frame = page.frameLocator('#preview-frame');
    await frame.locator('html[data-ready="true"]').waitFor();
    assert.match(await frame.locator('#status').innerText(), /Monaco hazır/);
    assert.equal(await frame.locator('#language').inputValue(), 'php');
    assert.equal(await page.evaluate(() => globalThis.PWNED), undefined);
    assert.equal(await frame.locator('.monaco-editor').count(), 1);
    assert.equal(await frame.locator('.view-lines').innerText().then((s) => s.includes('OTHER_FORM_PRIVATE_DATA')), false);
    const original = await page.evaluate(() => document.getElementById('native').env.editor.getValue());
    // Real key input must not alter the read-only model/native form.
    await frame.locator('.view-lines').click();
    await page.keyboard.type('MUST_NOT_BE_WRITTEN');
    assert.equal(await page.evaluate(() => document.getElementById('native').env.editor.getValue()), original);
    assert.equal(await frame.locator('.view-lines').innerText().then((s) => s.includes('MUST_NOT_BE_WRITTEN')), false);
    assert.equal(await page.evaluate(() => window.nativeWrites), 0);
    await frame.getByLabel('Tema', { exact: true }).selectOption('dark');
    await frame.locator('.monaco-editor.vs-dark').waitFor();
    await frame.getByLabel('Kod dili').selectOption('json');
    assert.equal(await frame.getByLabel('Kod dili').inputValue(), 'json');
    await frame.getByLabel('Yazı boyutu').selectOption('18');
    await frame.getByLabel('Satır kaydır').check();
    await frame.getByLabel('Kod haritası').check();
    await frame.getByRole('button', { name: 'Bul', exact: true }).click();
    await frame.locator('.find-widget.visible').waitFor();
    await frame.getByLabel('Kod dili').selectOption('php');
    const actualFrame = page.frames().find((item) => item.url().includes('/ismonaco-preview-0.1.2/frame.html'));
    assert.equal(await actualFrame.evaluate(async () => {
      const faces = await document.fonts.load('16px codicon');
      return faces.length > 0 && faces.every((font) => font.status === 'loaded');
    }), true);
    await actualFrame.waitForFunction(() => new Set([...document.querySelectorAll('.view-line span')]
      .map((item) => getComputedStyle(item).color)).size > 2);
    assert.equal(await actualFrame.evaluate(() => new Promise((resolve) => {
      const worker = new Worker('/manimg/ismonaco-preview-0.1.2/editor.worker.js', { type: 'module' });
      worker.onerror = () => { worker.terminate(); resolve(false); };
      setTimeout(() => { worker.terminate(); resolve(true); }, 400);
    })), true);
    if (route === '/') await page.screenshot({ path: '/tmp/ismonaco-desktop.png', fullPage: true });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: '/tmp/ismonaco-mobile.png', fullPage: true });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.goto('http://127.0.0.1:8765/denied');
  assert.equal(await page.locator('iframe').count(), 0);
  await page.locator('#denied').waitFor();
  await page.goto('http://127.0.0.1:8765/ambiguous');
  await page.frameLocator('#preview-frame').locator('html[data-ready="false"]').waitFor();
  await page.goto('http://127.0.0.1:8765/manimg/ismonaco-preview-0.1.2/frame.html');
  await page.locator('html[data-ready="false"]').waitFor();
  assert.equal(await page.locator('.monaco-editor').count(), 0);
  assert.equal(requests.some((url) => !url.startsWith('http://127.0.0.1:8765/') ), false);
  assert.deepEqual(errors, []);
  assert.deepEqual(warnings.filter((message) => !message.includes('allow-scripts and allow-same-origin')), []);
  console.log('BROWSER_OK: real Ace bridge in synthetic root/normal forms, delayed load, decoy form isolation, readonly/no native writes, settings/search, denied/ambiguous/standalone fail-closed, local worker/font; 1440/390px');
} finally {
  await browser.close();
}
