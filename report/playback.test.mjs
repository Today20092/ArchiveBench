import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, mkdir, writeFile, readFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {chromium} from '@playwright/test';
import {safeAssetPath} from './playback.js';

test('public companion references reject escaped and external paths', () => {
  assert.equal(safeAssetPath('review/abc/original.mp4'), true);
  for (const path of ['../a', 'https://example/a', 'review/a%2fb/original.mp4', 'review/../original.mp4', 'review/a/original.mp4?x', '//example/a']) assert.equal(safeAssetPath(path), false);
});

test('paired previews really load from file and survive seek, buffer, rejection and missing files', async () => {
  const root = await mkdtemp(join(tmpdir(), 'archivebench-playback-'));
  const browser = await chromium.launch({headless:true, ...(process.env.ARCHIVEBENCH_BROWSER ? {executablePath:process.env.ARCHIVEBENCH_BROWSER} : process.platform === 'win32' ? {channel:'msedge'} : {})});
  try {
    await mkdir(join(root, 'review', 'pair'), {recursive:true});
    execFileSync('ffmpeg', ['-v','error','-f','lavfi','-i','testsrc2=size=160x90:rate=30','-t','3','-c:v','libx264','-pix_fmt','yuv420p',join(root,'review','pair','original.mp4')]);
    execFileSync('ffmpeg', ['-v','error','-i',join(root,'review','pair','original.mp4'),'-vf','scale=80:44','-c:v','libx264',join(root,'review','pair','encoded.mp4')]);
    const module = (await readFile(new URL('./playback.js', import.meta.url),'utf8')).replaceAll('export ', '');
    await writeFile(join(root,'report.html'), `<video id="a" muted></video><video id="b" muted></video><p id="message"></p><script>${module}\nwindow.pair=pairedPlayback(a,b,message); pair.load(['review/pair/original.mp4','review/pair/encoded.mp4']);</script>`);
    const page = await browser.newPage();
    const network=[];
    page.on('request', request => {if (/^https?:/.test(request.url())) network.push(request.url());});
    await page.goto(pathToFileURL(join(root,'report.html')).href);
    await page.waitForFunction(() => a.readyState >= 3 && b.readyState >= 3);
    assert.deepEqual(await page.evaluate(() => [a.videoWidth,b.videoWidth]), [160,80]);
    await page.evaluate(() => pair.play());
    await page.waitForFunction(() => !a.paused && !b.paused && a.currentTime > .1);
    await page.evaluate(() => pair.stop());
    assert.deepEqual(await page.evaluate(() => [a.paused,b.paused]), [true,true]);
    await page.evaluate(() => pair.seek(1));
    await page.waitForFunction(() => !a.seeking && !b.seeking && Math.abs(a.currentTime-1)<.08 && Math.abs(b.currentTime-1)<.08);
    await page.evaluate(() => {a.play = () => Promise.reject(new Error('blocked')); pair.play();});
    await page.waitForFunction(() => message.textContent.includes('blocked'));
    assert.deepEqual(await page.evaluate(() => [a.paused,b.paused]), [true,true]);
    await page.evaluate(() => {delete a.play; pair.play();});
    await page.waitForFunction(() => !a.paused && !b.paused);
    await page.evaluate(() => a.dispatchEvent(new Event('waiting')));
    assert.deepEqual(await page.evaluate(() => [a.paused,b.paused]), [true,true]);
    await page.evaluate(() => {a.dispatchEvent(new Event('canplay')); b.dispatchEvent(new Event('canplay'));});
    await page.waitForFunction(() => !a.paused && !b.paused);
    await page.evaluate(() => {pair.stop(); a.dispatchEvent(new Event('canplay')); b.dispatchEvent(new Event('canplay'));});
    assert.deepEqual(await page.evaluate(() => [a.paused,b.paused]), [true,true]);
    await page.evaluate(() => {pair.seek(2.8);});
    await page.waitForFunction(() => !a.seeking && !b.seeking);
    await page.evaluate(() => pair.play());
    await page.waitForFunction(() => a.paused && b.paused && message.textContent.includes('ended'));
    await page.evaluate(() => {pair.play(); pair.load(['review/pair/missing.mp4','review/pair/encoded.mp4']);});
    await page.waitForFunction(() => message.textContent.includes('missing'));
    assert.deepEqual(await page.evaluate(() => [a.paused,b.paused]), [true,true]);
    assert.deepEqual(network, []);
  } finally {await browser.close(); await rm(root,{recursive:true,force:true});}
});
