import { chromium } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import { evidenceTrials, safeStillPath } from './stills.js';
import { configurationKey } from './math.js';

assert.equal(safeStillPath('review/a/frame-5-original.png'), true);
for (const path of ['../private.png','https://example.com/a.png','review/a/../frame-5-original.png','review/a/frame-5-original.png?x','review/a/%2e.png']) assert.equal(safeStillPath(path), false);
const html = await readFile(process.argv[2] || 'runs/demo/benchmark/report.html', 'utf8');
const payload = JSON.parse(html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const trial = payload.trials[0];
trial.review_stills = {status:'complete', note:'Native RGB PNG conversion cannot certify bit depth.', moments:[{frame_index:5,seconds:.167,vmaf:80,original:{path:'review/a/frame-5-original.png',width:320,height:180},encoded:{path:'review/a/frame-5-encoded.png',width:160,height:90}}]};
const extra = {...trial,id:'heldout-review',sample:'heldout-review',stage:'validation'};
payload.trials.push(extra); payload.samples.push({...payload.samples[0],id:'heldout-review',stage:'validation',label:'Fresh <scene>'});
assert.ok(evidenceTrials(payload,{trials:[trial]}).includes(extra));
const browser = await chromium.launch({headless:true,executablePath:process.env.ARCHIVEBENCH_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
try {
  const page = await browser.newPage(); const errors=[]; page.on('pageerror',error=>errors.push(error.message));
  await page.setContent(html.replace(/(<script id="data" type="application\/json">)[\s\S]*?(<\/script>)/,(_,start,end)=>start+JSON.stringify(payload).replaceAll('<','\\u003c')+end));
  await page.waitForFunction(()=>window.__archivebench);
  await page.evaluate(id=>{document.getElementById('sample').value='sample-1';window.__archivebench.render();},trial.id);
  await page.locator('#evidence').evaluate(element=>element.open=true);
  await page.locator('[data-id]').evaluateAll((buttons,key)=>buttons.find(button=>button.dataset.id===key).click(),configurationKey(trial));
  await page.locator('#review-sample').selectOption(trial.sample);
  assert.match(await page.locator('#still-review').innerText(),/Native RGB/);
  await page.locator('#still-zoom').fill('4'); await page.locator('#still-zoom').dispatchEvent('input');
  await page.locator('#still-x').fill('100'); await page.locator('#still-x').dispatchEvent('input');
  const styles=await page.locator('.still-viewport img').evaluateAll(images=>images.map(img=>[img.style.width,img.style.left,img.style.top]));
  assert.deepEqual(styles,[['400%','-300%','-150%'],['400%','-300%','-150%']]);
  assert.match(await page.locator('#still-review').innerText(),/does not recover detail/);
  await page.locator('.still-viewport img').first().dispatchEvent('error');
  assert.match(await page.locator('#still-review').innerText(),/Restore the review folder/);
  assert.match(await page.locator('#review-sample').innerText(),/validation · Fresh <scene>/);
  for (const width of [1440,390]) {await page.setViewportSize({width,height:900}); assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);}
  assert.deepEqual(errors,[]);
  console.log('Still browser checks passed: crop alignment, missing assets, stage selection, narrow/wide layouts.');
} finally {await browser.close();}
