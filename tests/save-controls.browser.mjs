// Local real Monaco/Ace; native submit/close outcome is a harness, never live disk.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE));
const browser=await chromium.launch({channel:'chrome',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
const f=()=>page.frameLocator('#preview-frame');
async function open(route='/') {await page.goto('http://127.0.0.1:8766'+route);await f().locator('html[data-ready=true]').waitFor();assert.equal(await page.title(),'Monaco yerel entegrasyon testi')}
async function labels(){return (await f().locator('.actions button:visible').allTextContents()).map(s=>s.trim())}
try{
 await open();
 assert.deepEqual(await labels(),['Tam ekrandan çık','Metin editörü','Kaydet','Kaydet ve çık']);
 assert.equal(await f().locator('#file-path').isVisible(),true);
 await f().getByRole('button',{name:'Tam ekrandan çık',exact:true}).click();
 assert.deepEqual(await labels(),['Tam ekran','Metin editörü']);
 assert.equal(await f().locator('#file-path').isVisible(),false);
 assert.equal(await f().locator('#escape-hint').isVisible(),false);
 await f().getByRole('button',{name:'Tam ekran',exact:true}).click();
 await f().getByRole('button',{name:'Kaydet',exact:true}).click();
 assert.equal(await page.evaluate(()=>window.nativeSaveCount),1);
 assert.equal(await page.evaluate(()=>window.nativeClosed||false),false);
 await f().getByRole('button',{name:'Tam ekran',exact:true}).click();
 await f().locator('.view-lines').click();await page.keyboard.press('Meta+s');
 assert.equal(await page.evaluate(()=>window.nativeSaveCount),2);
 assert.equal(await page.evaluate(()=>window.nativeSaveCloseCount||0),0);
 await f().getByRole('button',{name:'Tam ekran',exact:true}).click();
 await f().locator('.view-lines').click();await page.keyboard.insertText('SAVE_AND_CLOSE_TEST');
 const expected=await page.evaluate(()=>window.nativeModel);
 await f().getByRole('button',{name:'Kaydet ve çık',exact:true}).click();
 assert.equal(await page.evaluate(()=>window.nativeSaveCloseCount),1);
 assert.equal(await page.evaluate(()=>window.nativeClosed),true);
 assert.equal(await page.evaluate(()=>window.nativeSubmittedContent),expected);
 await open('/save-close-error');
 await f().getByRole('button',{name:'Kaydet ve çık',exact:true}).click();
 await page.getByRole('alert').filter({hasText:'Native save rejected'}).waitFor();
 assert.equal(await page.evaluate(()=>window.nativeClosed||false),false);
 assert.equal(await f().locator('.view-lines').isVisible(),true);
 await open('/readonly');
 assert.equal(await f().getByRole('button',{name:'Kaydet ve çık',exact:true}).isDisabled(),true);
 await page.setViewportSize({width:390,height:844});
 await open();
 await page.screenshot({path:'/tmp/ismonaco-save-controls-mobile.png',fullPage:false});
 assert.equal(await f().locator('body').evaluate(n=>n.scrollWidth<=innerWidth),true);
 await page.setViewportSize({width:1440,height:1000});await open();
 await page.screenshot({path:'/tmp/ismonaco-save-controls-full.png',fullPage:false});
 await f().getByRole('button',{name:'Tam ekrandan çık',exact:true}).click();
 await page.screenshot({path:'/tmp/ismonaco-save-controls-inline.png',fullPage:false});
 assert.deepEqual(errors,[]);
 console.log('SAVE_CONTROLS_BROWSER_OK: fullscreen-only path/save buttons; order and label; save and Cmd-S never close; native ok receives latest text; native rejection keeps editor; readonly; 1440/390px');
}finally{await browser.close()}
