import { defineChart, dot, mountChart } from '@tanstack/charts';
import { scaleLinear } from '@tanstack/charts/scales/linear';
import { project, smallest, eligible, durationText } from './math.js';

const result = JSON.parse(document.getElementById('data').textContent);
const $ = id => document.getElementById(id);
const colors = ['#73e0bd','#81b9fa','#f5bd78','#b8a4f8','#f28aab','#8bced4','#d4cc88','#dba783'];
const encoderNames = [...new Set(result.trials.map(row => row.encoder))];
const lightColors = ['#126e54','#245a9f','#95561a','#6948a0','#a23e64','#246977','#72660d','#895439'];
const color = name => (document.documentElement.classList.contains('light') ? lightColors : colors)[encoderNames.indexOf(name) % colors.length];
const escape = text => String(text).replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
let selectedId = null;
const hosts = {};
$('status').textContent = result.status.replaceAll('_',' ');
$('target').value = result.config.target_vmaf;
for (const sample of result.samples) { const option = document.createElement('option');option.value=sample.id;option.textContent=sample.label;$('sample').append(option); }
$('legend').innerHTML = encoderNames.map(name => `<span><i class="swatch" style="background:${color(name)}"></i>${escape(name)}</span>`).join('');
$('skip-title').textContent = `Skipped or failed configurations (${result.skipped.length})`;
$('skips').textContent = JSON.stringify(result.skipped, null, 2);
$('environment').textContent = JSON.stringify({environment:result.environment,identity:result.identity,format:result.config.pixel_format,profile:result.config.profile,mode:result.config.mode,tool_versions: Object.fromEntries(Object.entries(result.tools).map(([name,value])=>[name,{version:value.version.split('\n')[0],sha256:value.sha256}]))},null,2);
function drawChart(id, rows, x, y, xLabel, yLabel) {
  const dark = !document.documentElement.classList.contains('light');
  const marks = encoderNames.map(name=>dot(rows.filter(row=>row.encoder===name),{x,y,r:7,fill:color(name),stroke:dark?'#191f26':'#ffffff',strokeWidth:1}));
  const definition=defineChart({marks,scales:{x:{scale:scaleLinear,nice:true,grid:true,axis:{label:xLabel}},y:{scale:scaleLinear,nice:true,grid:true,axis:{label:yLabel},...(y==='vmaf'?{domain:[0,100]}:{})}}});
  const options={definition,height:innerWidth<760?290:330,ariaLabel:`${yLabel} versus ${xLabel}`};
  if(hosts[id])hosts[id].update(options);else hosts[id]=mountChart($(id),options);
}
function current(){const sample=result.samples.find(s=>s.id===$('sample').value);const minutes=Math.min(10080,Math.max(1,Number($('minutes').value)||60));const target=Math.min(100,Math.max(0,Number($('target').value)||0));return {sample,minutes,target,rows:sample?result.trials.filter(r=>r.sample===sample.id).map(r=>project(r,sample.seconds,minutes)):[]};}
function render(){
 $('legend').innerHTML = encoderNames.map(name => `<span><i class="swatch" style="background:${color(name)}"></i>${escape(name)}</span>`).join('');
 const {sample,minutes,target,rows}=current();
 const best=smallest(rows,target),fastest=eligible(rows,target).sort((a,b)=>a.encode_seconds-b.encode_seconds)[0];
 $('recommendation').textContent=best?`Smallest measured configuration meeting VMAF ${target}: ${best.encoder}, quality control ${best.quality}. Fastest meeting the target: ${fastest.encoder}, quality control ${fastest.quality}. Visual approval is still required.`:'No measured configuration meets this target for this sample. Lower the display threshold or run additional quality trials; no winner is certified.';
 if(!rows.length){$('metrics').innerHTML='<div class="empty">No successful trials. Review skipped configurations below.</div>';$('details').hidden=true;$('rows').innerHTML='';return;}
 if(!rows.some(row=>row.id===selectedId))selectedId=(best??rows[0]).id;
 const selected=rows.find(row=>row.id===selectedId);
 $('metrics').innerHTML=[['Selected quality score',selected.vmaf.toFixed(2),'VMAF · not a percentage'],[`Video size · ${minutes} min footage`,`${selected.gib.toFixed(2)} GiB`,'Projected · audio excluded'],['Encoding time',durationText(selected.minutes),`Projected · ${selected.timings.length} timed run${selected.timings.length===1?'':'s'}`]].map(([label,value,note])=>`<div class="metric"><small>${escape(label)}</small><div class="value">${escape(value)}</div><p>${escape(note)}</p></div>`).join('');
 drawChart('quality-chart',rows,'gib','vmaf','Projected video size (GiB)','VMAF score');drawChart('time-chart',rows,'minutes','gib','Projected encoding (minutes)','Projected video size (GiB)');
 $('rows').innerHTML=rows.slice().sort((a,b)=>a.bytes-b.bytes).map(row=>`<tr class="${row.id===selectedId?'selected':''}"><td><button class="pick" data-id="${escape(row.id)}">${escape(row.encoder)} · ${row.quality}</button><br><span class="tag">${escape(row.pixel_format)}</span></td><td class="numeric">${row.vmaf.toFixed(2)} / ${row.vmaf_p5.toFixed(2)}</td><td class="numeric">${row.ssim.toFixed(4)}</td><td class="numeric">${row.gib.toFixed(2)} GiB</td><td class="numeric">${durationText(row.minutes)}</td><td>${row.vmaf>=target?'Meets score':'Below score'}</td></tr>`).join('');
 $('details').hidden=false;$('detail-title').textContent=`${selected.encoder} · quality control ${selected.quality}`;
 for(const id of ['original-preview','wipe-original'])$(id).src=sample.preview;
 for(const id of ['encoded-preview','wipe-encoded'])$(id).src=selected.preview;
 $('exact').textContent=JSON.stringify({...selected,preview:undefined,gib:undefined,minutes:undefined},null,2);
}
$('rows').addEventListener('click',event=>{const button=event.target.closest('[data-id]');if(button){selectedId=button.dataset.id;render();}});
for(const id of ['sample','minutes','target'])$(id).addEventListener('input',()=>{if(id==='minutes')$('duration').value='custom';render();});
$('duration').addEventListener('change',()=>{if($('duration').value!=='custom')$('minutes').value=$('duration').value;render();});
$('divider').addEventListener('input',()=>{$('wipe-original').style.clipPath=`inset(0 ${100-Number($('divider').value)}% 0 0)`;});
$('theme').addEventListener('click',()=>{document.documentElement.classList.toggle('light');render();});
$('export').addEventListener('click',()=>{const trial=result.trials.find(row=>row.id===selectedId);if(!trial)return;const settings={version:1,type:'archive-settings',encoder:trial.encoder,quality:trial.quality,pixel_format:trial.pixel_format,minimum_saving:0.1,drop_audio_tracks:[3,4],audio_kbps_per_channel:192,benchmark_identity:result.identity,source_sample:trial.sample,vmaf:trial.vmaf};const blob=new Blob([JSON.stringify(settings,null,2)],{type:'application/json'});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='archive-settings.json';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);});
render();
window.__archivebench={result,render,current};
