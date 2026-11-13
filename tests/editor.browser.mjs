// Browser plugin not available. Local Chrome + actual Ace; no live panel writes.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE));
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
const errors = [], requests = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
page.on('request', (request) => requests.push(request));
const nativeValue = () => page.evaluate(() => document.getElementById('native').env.editor.getValue());
const field = () => page.locator('#selected-form > [data-dynamic-form-element-id="fdata-code-element"]');
const frame = () => page.frameLocator('#preview-frame');
async function open(route = '/') {
  await page.goto('http://127.0.0.1:8766' + route);
  await frame().locator('html[data-ready="true"]').waitFor();
  assert.equal(await page.title(), 'Monaco yerel entegrasyon testi');
}
try {
  for (const route of ['/', '/normal', '/slow']) {
    await open(route);
    assert.equal(await frame().locator('#server-settings').count(), 0);
    assert.equal(await frame().getByRole('button', { name: 'Tam ekrandan çık' }).getAttribute('aria-pressed'), 'true');
    const full = await page.locator('#preview-frame').boundingBox();
    assert.equal(Math.round(full.x), 0); assert.equal(Math.round(full.y), 0);
    assert.equal(Math.round(full.width), 1440); assert.equal(Math.round(full.height), 1100);
    await frame().getByRole('button', { name: 'Tam ekrandan çık' }).click();
    assert.equal(await frame().getByLabel('Tema', { exact: true }).inputValue(), 'dark');
    assert.equal(await frame().getByLabel('Yazı boyutu').inputValue(), '14');
    assert.equal(await frame().getByLabel('Satır kaydır').isChecked(), true);
    assert.equal(await frame().getByLabel('Kod haritası').isChecked(), true);
    assert.equal(await frame().getByLabel('Editör yüksekliği').inputValue(), '760');
    assert.equal(await field().isVisible(), false);
    assert.equal(await frame().locator('h1').count(), 0);
    const positions = await page.evaluate(() => ({ file: document.getElementById('native-filename').getBoundingClientRect().bottom, encoding: document.getElementById('native-encoding').getBoundingClientRect().bottom, editor: document.getElementById('preview-frame').getBoundingClientRect().top }));
    assert.equal(positions.file <= positions.encoding && positions.encoding <= positions.editor, true);
    assert.equal(await frame().locator('#mode').innerText(), 'Düzenlenebilir');
    assert.equal(await frame().locator('.view-lines').innerText().then((s) => s.includes('OTHER_FORM_PRIVATE_DATA')), false);
    assert.equal(await page.evaluate(() => globalThis.PWNED), undefined);
    const original = await nativeValue();
    await frame().locator('.view-lines').click();
    await page.keyboard.press('Meta+ArrowUp');
    await page.keyboard.insertText('MONACO_EDIT');
    assert.equal(await nativeValue(), '\ufeffMONACO_EDIT' + original.slice(1));
    await page.getByRole('button', { name: 'Save', exact: true }).click();
    assert.equal(await page.evaluate(() => window.nativeSubmittedContent), await nativeValue());
    assert.equal(await page.evaluate(() => window.nativeSaveCount), 1);
    // Monaco undo/redo updates the existing panel model too, including its BOM.
    await frame().locator('.view-lines').click();
    await page.keyboard.press('Meta+z');
    assert.equal(await nativeValue(), original);
    await page.keyboard.press('Meta+Shift+z');
    assert.match(await nativeValue(), /MONACO_EDIT/);
    const beforeShortcut = await page.evaluate(() => window.nativeSaveCount);
    await page.keyboard.press('Meta+s');
    assert.equal(await page.evaluate(() => window.nativeSaveCount), beforeShortcut + 1);
    assert.equal(await page.evaluate(() => window.nativeSubmittedContent), await nativeValue());
    // Native reload/encoding changes must update Monaco without a write-back loop.
    await page.evaluate(() => document.getElementById('native').env.editor.setValue('<?php /* NATIVE_RELOAD */', -1));
    await frame().getByText('<?php /* NATIVE_RELOAD */', { exact: false }).first().waitFor();
    await frame().getByLabel('Editör yüksekliği').selectOption('900');
    assert.equal(await page.locator('#preview-frame').evaluate((node) => node.getBoundingClientRect().height > 850), true);
    await frame().getByRole('button', { name: 'Bul', exact: true }).click();
    await frame().locator('.find-widget.visible').waitFor();
    if (route === '/') await page.screenshot({ path: '/tmp/ismonaco-editor-desktop.png', fullPage: true });
  }
  await open('/normal');
  // Top layer must escape panel transforms and clean up when its tab hides.
  await page.evaluate(() => { document.getElementById('selected-form').style.cssText = 'transform:translateZ(0);overflow:hidden;height:120px'; });
  const transformedFull = await page.locator('#preview-frame').boundingBox();
  assert.equal(Math.round(transformedFull.x), 0); assert.equal(Math.round(transformedFull.width), 1440);
  await page.evaluate(() => { document.getElementById('selected-form').hidden = true; });
  await page.waitForFunction(() => !document.querySelector('[data-dynamic-form-element-id="ismonaco_preview-frame"]').hasAttribute('popover'));
  await page.evaluate(() => { const form = document.getElementById('selected-form'); form.hidden = false; form.style.cssText = ''; });
  await frame().getByRole('button', { name: 'Tam ekran', exact: true }).click();
  await page.screenshot({ path: '/tmp/ismonaco-fullscreen-desktop.png', fullPage: false });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: '/tmp/ismonaco-fullscreen-mobile.png', fullPage: true });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  const mobileFull = await page.locator('#preview-frame').boundingBox();
  assert.equal(Math.round(mobileFull.width), 390); assert.equal(Math.round(mobileFull.height), 844);
  await page.keyboard.press('Escape');
  assert.equal(await frame().getByRole('button', { name: 'Tam ekran', exact: true }).getAttribute('aria-pressed'), 'false');
  await page.setViewportSize({ width: 1440, height: 1100 });
  await open('/custom');
  assert.equal(await frame().getByLabel('Tema', { exact: true }).inputValue(), 'light');
  assert.equal(await frame().getByLabel('Yazı boyutu').inputValue(), '16');
  assert.equal(await frame().getByLabel('Satır kaydır').isChecked(), false);
  assert.equal(await frame().getByLabel('Kod haritası').isChecked(), false);
  assert.equal(await frame().getByLabel('Editör yüksekliği').inputValue(), '900');
  assert.equal(await frame().getByRole('button', { name: 'Tam ekran', exact: true }).getAttribute('aria-pressed'), 'false');
  await frame().getByRole('button', { name: 'Tam ekran', exact: true }).click();
  await frame().getByRole('button', { name: 'Kaydet', exact: true }).click();
  assert.equal(await page.evaluate(() => window.nativeSaveCount), 1);
  assert.equal(await frame().getByRole('button', { name: 'Tam ekran', exact: true }).getAttribute('aria-pressed'), 'false');
  await frame().getByRole('button', { name: 'Metin editörü' }).click();
  assert.equal(await field().isVisible(), true);
  assert.equal(await frame().locator('#editor').isVisible(), false);
  await page.evaluate(() => document.getElementById('native').env.editor.setValue('NATIVE_UNSAVED_CHANGE', -1));
  await frame().getByRole('button', { name: 'Gelişmiş editöre geç' }).click();
  assert.equal(await field().isVisible(), false);
  assert.match(await frame().locator('.view-lines').innerText(), /NATIVE_UNSAVED_CHANGE/);
  assert.equal(await nativeValue(), 'NATIVE_UNSAVED_CHANGE');
  await frame().getByRole('button', { name: 'Metin editörü' }).click();
  assert.equal(await field().isVisible(), true);
  await frame().getByRole('button', { name: 'Gelişmiş editöre geç' }).click();
  assert.equal(await field().isVisible(), false);
  await open('/readonly');
  const readonlyValue = await nativeValue();
  await frame().locator('.view-lines').click(); await page.keyboard.type('FORBIDDEN');
  assert.equal(await nativeValue(), readonlyValue);
  assert.equal(await frame().locator('#mode').innerText(), 'Salt okunur');
  await open();
  // A failed setter must preserve pending Monaco text and block the native save.
  await page.evaluate(() => { document.getElementById('native').env.editor.setValue = () => { throw new Error('fixture failure'); }; });
  await frame().locator('.view-lines').click(); await page.keyboard.insertText('PENDING_EDIT');
  await frame().getByRole('button', { name: 'Monaco metnini kopyala' }).waitFor();
  assert.equal(await field().isVisible(), true);
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  assert.equal(await page.evaluate(() => window.nativeSaveCount || 0), 0);
  assert.match(await frame().locator('.view-lines').innerText(), /PENDING_EDIT/);
  // Discard only the synthetic pending buffer to continue the test.
  page.once('dialog', (dialog) => dialog.accept());
  await frame().getByRole('button', { name: 'Metin editörü' }).click();
  for (const route of ['/denied', '/ambiguous']) {
    await page.goto('http://127.0.0.1:8766' + route);
    if (route === '/denied') assert.equal(await page.locator('iframe').count(), 0);
    else { await frame().locator('html[data-ready="false"]').waitFor(); assert.equal(await field().first().isVisible(), true); }
  }
  await page.goto('http://127.0.0.1:8766/manimg/ismonaco-editor-0.2.5/frame.html');
  await page.locator('html[data-ready="false"]').waitFor();
  assert.equal(requests.some((request) => request.method() !== 'GET' || !request.url().startsWith('http://127.0.0.1:8766/')), false);
  assert.deepEqual(errors, []);
  console.log('EDITOR_BROWSER_OK: code position/no heading; bidirectional switch/native unsaved buffer; fullscreen default on/off, manual/Escape/save exit, mobile viewport; no server-settings button; single editable Monaco; native model/save and Ctrl-S; BOM, undo/redo; server defaults; root/normal/readonly; fallback/error/ambiguous; 1440/390px; no API requests');
} finally { await browser.close(); }
