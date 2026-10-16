import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const html = await readFile(process.argv[2] || 'runs/fixed-demo/benchmark/report.html','utf8');
const browser = await chromium.launch({headless:true,executablePath:process.env.ARCHIVEBENCH_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
try {
 const context = await browser.newContext({offline:true,acceptDownloads:true});
 const page = await context.newPage(), errors=[], requests=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(/^https?:/.test(r.url())) requests.push(r.url());});
 await page.setContent(html);
 await page.waitForFunction(()=>window.__archivebench);
 assert.match(await page.locator('#outcome').innerText(),/Fixed-setting/);
 assert.match(await page.locator('#quality-levels').innerText(),/Measured starting/);
 assert.equal(await page.locator('#target').inputValue(),'0');
 assert.equal(await page.locator('#sample').inputValue(),'sample-1');
 await page.locator('#export-preset').scrollIntoViewIfNeeded();
 const [download] = await Promise.all([page.waitForEvent('download'),page.locator('#export-preset').click()]);
 const preset = JSON.parse(await readFile(await download.path(),'utf8'));
 assert.equal(preset.settings.validated,false);
 assert.equal(preset.evidence.measurement_status,'measured starting point');
 assert.ok(preset.evidence.estimates.video_bytes_per_second>0);
 for(const width of [1440,390]) {await page.setViewportSize({width,height:900});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);}
 assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
 console.log('Fixed report, starting preset export, responsive layout and offline checks passed');
} finally {await browser.close();}
