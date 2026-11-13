// Content safety + the actual Phoenix mapping contract; not a live panel test.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';

const cases=JSON.parse(execFileSync('python3',['-I','-B','-c',`
import json,runpy,xml.etree.ElementTree as E
m=runpy.run_path('integration/site-notice/site_notice.py')
text='IP A: Web\\nIP B: Mail\\n<script>parent.PWNED=true</script> <img src=x onerror="alert(1)"> & {{7*7}}'
xml=b'<doc func="site.edit"><metadata name="site.edit" type="form"><form><page name="mainsettings"/></form></metadata></doc>'
out=[]
for style in ('info','warning'):
 class Store:
  def load(self): return dict(version=1,style=style,text=text)
 r=E.fromstring(m['transform'](xml,dict(PARAM_func='site.edit',AUTH_USER='root',AUTH_LEVEL='30'),Store()))
 out.append(dict(style=style,text=text,html=r.findtext('ismonaco_site_notice'),attributes=r.find('metadata/form/page/field/textdata').attrib))
print(json.dumps(out))
`],{encoding:'utf8'}));

if(process.env.PANEL_FORM_BUNDLE){
 const contract=JSON.parse(readFileSync('tests/fixtures/ispmanager-6.155.0/site-notice-contract.json','utf8'));
 const source=readFileSync(process.env.PANEL_FORM_BUNDLE,'utf8');
 assert.equal(createHash('sha256').update(source).digest('hex'),contract.renderer.sha256);
 const start=source.indexOf('function Kr('),end=source.indexOf('m();function nl(',start);
 assert.ok(start>=0&&end>start);
 const valueStart=source.indexOf('function kc('),valueEnd=start;
 assert.ok(valueStart>=0&&valueEnd>valueStart);
 const mapper=new Function('W','uo',source.slice(valueStart,valueEnd)+source.slice(start,end)+';return Kr;')({getStringValue:(n,d)=>d[n]||'',getMessage:()=>''},()=>({}));
 for(const c of cases){
  const attrs=Object.fromEntries(Object.entries(c.attributes).map(([k,v])=>['$'+k,v]));
  const element=mapper(attrs,{$name:'ismonaco_site_notice_field',$noname:'yes'},{ismonaco_site_notice:c.html});
  assert.equal(element.banner,c.style);assert.equal(element.renderAsHTML,true);assert.equal(element.HTML,c.html);
 }
}
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE));
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
 const page=await browser.newPage();const errors=[];const requests=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
 for(const c of cases){
  await page.setContent('<main><section id="banner"></section><textarea rows="5"></textarea></main>');
  await page.locator('#banner').evaluate((n,html)=>{n.innerHTML=html},c.html);
  await page.locator('textarea').fill(c.text);
  assert.equal(await page.locator('#banner script, #banner img, #banner a').count(),0);
  assert.equal(await page.locator('#banner').innerText(),c.text);
  assert.equal(await page.locator('textarea').inputValue(),c.text);
  assert.equal(await page.evaluate(()=>window.PWNED||false),false);
 }
 assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
 console.log('SITE_NOTICE_BROWSER_OK: actual Phoenix banner/status/html mapping; generated line breaks; script/img literal; textarea round-trip; no script errors/network');
}finally{await browser.close()}
