import test from 'node:test';
import assert from 'node:assert/strict';
import {project,smallest,durationText,pareto,archiveSettings,configurations,eligible,tradeoff} from './math.js';
test('projections convert seconds/bytes consistently',()=>{const row=project({bytes:1073741824,encode_seconds:40},20,10);assert.equal(row.gib,30);assert.equal(row.minutes,20);});
test('winner must meet target, not merely be closest',()=>{assert.equal(smallest([{bytes:1,vmaf:90},{bytes:2,vmaf:96}],95).bytes,2);assert.equal(smallest([{bytes:1,vmaf:90}],95),null);});
test('duration formatting',()=>{assert.equal(durationText(100),'1h 40m');});
test('archive exports preserve explicit output and retention choices',()=>{
 const trial={encoder:'libx265',quality:24,pixel_format:'yuv422p10le',width:1920,height:1080,resolution:'1080p',sample:'one',vmaf:94};
 const config={pixel_format:'source',audio_mode:'aac',drop_audio_tracks:[2],audio_kbps_per_channel:128,subtitles:'drop',attachments:'copy',metadata:'copy'};
 const settings=archiveSettings({config,identity:'run'},trial);
 assert.equal(settings.version,2);assert.equal(settings.pixel_format,'source');assert.equal(settings.measured_pixel_format,'yuv422p10le');assert.equal(settings.resolution,'1080p');
 for(const key of ['audio_mode','drop_audio_tracks','audio_kbps_per_channel','subtitles','attachments','metadata'])assert.deepEqual(settings[key],config[key]);
 const defaults=archiveSettings({config:{pixel_format:'yuv420p10le'},identity:'old'},trial);
 assert.equal(defaults.audio_mode,'copy');assert.deepEqual(defaults.drop_audio_tracks,[]);assert.equal(defaults.subtitles,'copy');
});
test('Pareto keeps only nondominated measured points, including ties',()=>{const rows=[{id:'a',bytes:10,vmaf:90},{id:'b',bytes:20,vmaf:95},{id:'c',bytes:30,vmaf:94},{id:'d',bytes:20,vmaf:95}];assert.deepEqual(pareto(rows,[['bytes',1],['vmaf',-1]]).map(r=>r.id),['a','b','d']);});
test('speed/storage frontier applies quality cutoff first',()=>{const rows=[{id:'low',bytes:1,encode_seconds:1,vmaf:80},{id:'small',bytes:10,encode_seconds:4,vmaf:95},{id:'fast',bytes:20,encode_seconds:2,vmaf:95},{id:'dominated',bytes:30,encode_seconds:5,vmaf:96}];assert.deepEqual(pareto(rows.filter(r=>r.vmaf>=95),[['bytes',1],['encode_seconds',1]]).map(r=>r.id),['small','fast']);});

const collection = () => ({config:{samples:[{},{}]}, samples:[{id:'one',seconds:10},{id:'two',seconds:30}], trials:[
 {id:'a1',sample:'one',encoder:'libx265',quality:24,bytes:100,encode_seconds:10,vmaf:99,vmaf_p5:94,ssim:.99},
 {id:'a2',sample:'two',encoder:'libx265',quality:24,bytes:600,encode_seconds:90,vmaf:91,vmaf_p5:80,ssim:.95},
 {id:'b1',sample:'one',encoder:'libx265',quality:28,bytes:50,encode_seconds:5,vmaf:95,vmaf_p5:92,ssim:.97},
]});
test('collection uses exact settings, full coverage and weakest sample, not a passing average',()=>{
 const rows=configurations(collection(),1);
 assert.equal(rows.length,2);assert.equal(rows[0].vmaf,91);assert.equal(rows[0].vmaf_p5,80);
 assert.equal(rows[0].complete,true);assert.equal(rows[1].complete,false);
 assert.equal(eligible(rows,93).length,0);
 assert.equal(rows[0].gib,1050/1073741824);assert.equal(rows[0].minutes,2.5);
 assert.equal(eligible(configurations(collection(),1,'one'),93).length,2);
});
test('missing planned samples cannot qualify and independent low-tail/time constraints are inclusive',()=>{
 const result=collection();result.config.samples.push({});
 assert.equal(eligible(configurations(result,1),90).length,0);
 const rows=configurations(collection(),1);
 assert.equal(eligible(rows,91,80,2.5).length,1);
 assert.equal(eligible(rows,91,80.1).length,0);
 assert.equal(eligible(rows,91,null,2.4).length,0);
 delete result.trials[0].vmaf_p5;
 const sample=configurations(result,1,'one');
 assert.equal(eligible(sample,98).length,1);assert.equal(eligible(sample,98,0).length,0);
});
test('tradeoffs name a baseline and handle zero denominators',()=>{
 assert.deepEqual(tradeoff({gib:5,minutes:20},{gib:10,minutes:10}),{savingPercent:50,timeRatio:2,extraMinutes:10});
 assert.deepEqual(tradeoff({gib:10,minutes:10},{gib:5,minutes:20}),{savingPercent:-100,timeRatio:.5,extraMinutes:-10});
 assert.deepEqual(tradeoff({gib:1,minutes:1},{gib:0,minutes:0}),{savingPercent:null,timeRatio:null,extraMinutes:1});
});
test('empty collections and unknown sample scopes remain empty',()=>{
 const result=collection();result.trials=[];
 assert.deepEqual(configurations(result,60),[]);
 assert.deepEqual(configurations(collection(),60,'missing'),[]);
});
