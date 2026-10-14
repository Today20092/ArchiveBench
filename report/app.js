import { barX, createMark, defineChart, dot, hexagon, lineY, ruleY, mountChart } from '@tanstack/charts';
import { tooltip } from '@tanstack/charts/tooltip';
import { portal } from '@tanstack/charts/tooltip/portal';
import { scaleLinear } from '@tanstack/charts/scales/linear';
import { scaleBand } from '@tanstack/charts/scales/band';
import { configurations, eligible, recommendations, durationText, pareto, archiveSettings, tradeoff } from './math.js';
import { evidenceTrials, renderStills } from './stills.js';
import { pairedPlayback, safeAssetPath } from './playback.js';

const $ = id => document.getElementById(id);
const result = JSON.parse($('data').textContent);
const escape = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = value => Number.isFinite(value) ? value.toFixed(2) : 'Unavailable';
const footageLength = minutes => {
  const seconds = Math.round(minutes * 600) / 10;
  return seconds < 60 ? `${seconds} sec` : `${Math.floor(seconds / 60)} min${seconds % 60 ? ` ${Number((seconds % 60).toFixed(1))} sec` : ''}`;
};
const hardware = name => /_(nvenc|qsv|amf|vaapi|videotoolbox)$/.test(name) ? 'GPU' : 'CPU';
const codec = name => name.includes('264') ? 'H.264' : name.includes('265') || name.includes('hevc') ? 'H.265' : name.includes('vp9') ? 'VP9' : 'AV1';
const category = name => $('color-mode').value === 'hardware' ? hardware(name) : codec(name);
const seriesColor = category => getComputedStyle(document.documentElement).getPropertyValue(`--series-${category.toLowerCase().replace('.', '')}`).trim();
const color = name => seriesColor(category(name));
const codecColor = name => seriesColor(codec(name));
const qualityLabel = row => `${row.encoder.endsWith('_nvenc') ? 'CQ' : row.encoder === 'librav1e' || /_(amf|vaapi)$/.test(row.encoder) ? 'QP' : row.encoder.endsWith('_qsv') ? 'ICQ' : row.encoder.endsWith('_videotoolbox') ? 'q:v' : 'CRF'} ${row.quality}`;
const qualityName = row => qualityLabel(row).replace(/^CRF /, 'constant rate factor ').replace(/^CQ /, 'constant quality ').replace(/^QP /, 'quantizer ').replace(/^ICQ /, 'intelligent constant quality ').replace(/^q:v /, 'quality setting ');
const variant = row => result.config.variants?.find(variant => variant.id === row.variant);
const label = row => `${codec(row.encoder)} · ${qualityLabel(row)}${result.config.variants?.length > 1 ? ` · ${variant(row)?.label ?? row.variant}` : ''}`;
const evidenceText = row => ({validated:'Passed fresh-footage checks', provisional:'Not yet checked on fresh footage', failed:'Failed saved quality checks', incomplete:'Required checks are incomplete'}[row.evidence_status]);
const encoderNames = [...new Set(result.trials.map(row => row.encoder))];
const hiddenEncoders = new Set(), reviewed = new Set(), hosts = {}, mediaURLs = {};
let selectedId = null, pinnedId = null, inspectedTrialId = null;
let showStill = () => false;

$('status').textContent = result.status.replaceAll('_', ' ');
$('target').value = result.config.target_vmaf;
for (const sample of result.samples.filter(sample => (sample.stage ?? 'tuning') === 'tuning')) $('sample').add(new Option(sample.label, sample.id));
const sampledSeconds = result.samples.reduce((sum, sample) => sum + sample.seconds, 0);
const sourceDurations = new Map(result.samples.filter(sample => Number.isFinite(sample.source_seconds)).map(sample => [sample.source_id ?? sample.id, sample.source_seconds]));
const sourceMinutes = sourceDurations.size ? [...sourceDurations.values()].reduce((sum, seconds) => sum + seconds, 0) / 60 : 60;
$('minutes').value = sourceMinutes;
$('duration').value = 'source';
$('duration').options[0].textContent = sourceDurations.size ? `Tested sources · ${footageLength(sourceMinutes)}` : 'Default estimate · 1 hour';
const footageLabels = [...new Set(result.samples.filter(sample => (sample.stage ?? 'tuning') === 'tuning').map(sample => sample.label))];
$('overview').textContent = `${footageLabels.slice(0, 2).join(' · ') || 'No footage measured'}${footageLabels.length > 2 ? ` and ${footageLabels.length - 2} more sections` : ''}. Compared ${[...new Set(encoderNames.map(codec))].join(', ') || 'no codecs'} using short footage sections.`;
$('coverage').textContent = `${result.samples.filter(sample => (sample.stage ?? 'tuning') === 'tuning').length} of ${result.config.samples.length} planned tuning samples · ${result.samples.filter(sample => sample.stage === 'validation').length}/${result.validation_required ?? 0} fresh sections measured · ${sampledSeconds.toFixed(1)} seconds sampled · ${result.trials.length} measured trials · ${result.config.mode} mode. ${result.samples.map(sample => `${sample.label} (${sample.video.width} × ${sample.video.height})`).join('; ')}`;
$('run-limit').textContent = [result.status !== 'completed' ? 'Partial experiment. Missing measurements cannot qualify a configuration.' : '', result.skipped.length ? `${result.skipped.length} skipped or failed probes. See technical notes for details.` : ''].filter(Boolean).join(' ');
$('run-limit').hidden = !$('run-limit').textContent;
$('skip-title').textContent = `Skipped or failed configurations (${result.skipped.length})`;
$('skips').textContent = JSON.stringify(result.skipped, null, 2);
$('environment').textContent = JSON.stringify({environment:result.environment, identity:result.identity, config:result.config, tools:Object.fromEntries(Object.entries(result.tools).map(([name, value]) => [name, {version:value.version.split('\n')[0], sha256:value.sha256}]))}, null, 2);
const savedRows = recommendations(configurations(result, 60), result.config.target_vmaf);
const savedSmallest = [...savedRows].sort((a,b) => a.gib-b.gib)[0];
const savedFastest = [...savedRows].sort((a,b) => a.minutes-b.minutes)[0];
$('outcome').textContent = savedSmallest ? 'Validated settings are available. Compare size and time, then review the footage before exporting settings.' : 'No validated project recommendation yet. Explore the measurements; fresh-footage validation is absent, failed or incomplete.';
$('saved-conclusion').textContent = `Saved mean target: ${result.config.target_vmaf}. ` + (savedSmallest ? `Smallest validated collection choice: ${label(savedSmallest)}. Fastest: ${label(savedFastest)}. Fresh footage passed the saved target. Visual review remains separate.` : 'Provisional tuning evidence. No validated project recommendation, because fresh-footage validation is absent, failed or incomplete. Per-sample results remain available for exploration.');

function optional(id, minimum, maximum = Infinity) {
  const value = $(id).value.trim();
  return value === '' ? null : Math.min(maximum, Math.max(minimum, Number(value)));
}
function current() {
  const minutes = $('duration').value === 'source' ? sourceMinutes : Math.max(0.001, Number($('minutes').value) || sourceMinutes);
  const target = Math.min(100, Math.max(0, Number($('target').value) || 0));
  const lowTarget = optional('low-target', 0, 100), maxMinutes = optional('max-time', 0.1);
  const rows = configurations(result, minutes, $('sample').value);
  return {minutes, target, lowTarget, maxMinutes, rows, qualifying:eligible(rows, target, lowTarget, maxMinutes), recommended:recommendations(rows, target, lowTarget, maxMinutes, $('sample').value)};
}
function checkText(row, state) {
  if (!row.complete) return `Incomplete: ${row.coverage}/${row.expected} samples`;
  if (row.vmaf < state.target) return 'Below minimum quality score';
  if (row.validation_vmaf !== null && row.validation_vmaf < state.target) return 'Fresh footage is below minimum quality score';
  if (state.lowTarget !== null && (!Number.isFinite(row.vmaf_p5) || row.vmaf_p5 < state.lowTarget)) return 'Weakest 5% is below minimum score';
  if (state.lowTarget !== null && row.validation_vmaf !== null && (!Number.isFinite(row.validation_vmaf_p5) || row.validation_vmaf_p5 < state.lowTarget)) return 'Fresh footage weakest 5% is below minimum score';
  if (state.maxMinutes !== null && row.minutes > state.maxMinutes) return 'Over projected time limit';
  return `Passes active checks · ${row.evidence_status} · fresh ${row.validation_coverage}/${row.validation_expected}`;
}
function choices(rows) {
  return {smallest:[...rows].sort((a,b) => a.gib-b.gib)[0], fastest:[...rows].sort((a,b) => a.minutes-b.minutes)[0], highest:[...rows].sort((a,b) => b.vmaf-a.vmaf)[0]};
}
function ordered(rows, key) {
  const direction = key.startsWith('vmaf') ? -1 : 1;
  return [...rows].sort((a,b) => {
    if (!Number.isFinite(a[key])) return Number.isFinite(b[key]) ? 1 : 0;
    if (!Number.isFinite(b[key])) return -1;
    return direction * (a[key]-b[key]);
  });
}
function select(id) {
  selectedId = id;
  render();
}
function mount(id, definition, options = {}) {
  const settings = {definition, height:innerWidth < 1000 ? 300 : 340, ...options};
  if (hosts[id]) hosts[id].update(settings);
  else hosts[id] = mountChart($(id), settings);
}
function clearChart(id, message = '') {
  hosts[id]?.destroy();
  delete hosts[id];
  $(id).textContent = message;
}
function chartTheme() {
  const style = getComputedStyle(document.documentElement);
  return Object.fromEntries([['foreground','--fg'],['background','--surface'],['muted','--muted'],['grid','--line']].map(([key, variable]) => [key, style.getPropertyValue(variable).trim()]));
}
function drawChart(id, state, x, y, xLabel, yLabel) {
  const rows = state.rows.filter(row => !hiddenEncoders.has(row.encoder));
  const theme = chartTheme(), marks = [createMark(() => ({
    id:'preferred-corner', channels:{},
    // Screen-space shading indicates direction, not a measured eligibility cutoff.
    render:({chart}) => ({nodes:[{
      kind:'rect', key:'preferred-corner', x:chart.x,
      y:chart.y + (y === 'vmaf' ? 0 : chart.height / 2),
      width:chart.width / 2, height:chart.height / 2,
      style:{fill:'var(--accent)', fillOpacity:0.12},
    }]}),
  }))];
  const frontier = pareto(y === 'vmaf' ? rows.filter(row => row.complete) : eligible(rows, state.target, state.lowTarget, state.maxMinutes), y === 'vmaf' ? [[x,1],[y,-1]] : [[x,1],[y,1]]).sort((a,b) => a[x]-b[x]);
  if (frontier.length > 1) marks.push(lineY(frontier, {x, y, stroke:theme.foreground, strokeWidth:1.2}));
  if (y === 'vmaf') marks.push(ruleY([state.target], {stroke:theme.foreground, strokeWidth:1, strokeDasharray:'5 5'}));
  for (const name of encoderNames) {
    const data = rows.filter(row => row.encoder === name && row.id !== selectedId);
    if (data.length) marks.push(dot(data, {x, y, r:5, fill:color(name), stroke:theme.foreground, strokeWidth:1}));
  }
  const selected = rows.filter(row => row.id === selectedId);
  if (selected.length) marks.push(dot(selected, {id:'selected-point', x, y, r:9, fill:color(selected[0].encoder), stroke:theme.foreground, strokeWidth:2}));
  const pinned = rows.filter(row => row.id === pinnedId);
  if (pinned.length) marks.push(hexagon(pinned, {id:'pinned-point', x, y, r:16, fill:'none', stroke:theme.foreground, strokeWidth:2}));
  const legend = $(id).parentElement.querySelector('.chart-legend');
  const groups = [...new Set(encoderNames.map(category))];
  legend.innerHTML = `<span class="direction-key" title="Direction of improvement only; quality checks still determine recommendations."><i></i>${y === 'vmaf' ? '↖ Higher quality, smaller files' : '↙ Smaller files, faster encoding'}</span>` + groups.map(group => {
    const members = encoderNames.filter(name => category(name) === group);
      return `<button data-category="${escape(group)}" style="--series-color:${color(members[0])}" aria-pressed="${members.some(name => !hiddenEncoders.has(name))}" aria-label="Show ${escape(group)} in charts"><i class="swatch" style="background:${color(members[0])}"></i>${escape(group)}</button>`;
  }).join('') + '<span class="frontier-key">Measured frontier</span>' + (y === 'vmaf' ? '<span class="target-key">Minimum score</span>' : '');
  if (!rows.length) { clearChart(id, 'No measurements in this view.'); return; }
  const definition = defineChart({marks, theme, focus:'nearest', maxFocusDistance:24,
    tooltip:{use:tooltip, portal, anchor:'point', placement:['top','bottom'], offset:22, className:'benchmark-tooltip', content:points => {
      const point = points[0];
      const row = point.datum;
      if (!row?.encoder) return {title:'Minimum quality score', rows:[{label:'VMAF', value:String(state.target)}]};
      return {title:label(row), color:color(row.encoder), rows:[
        {label:'Quality score', value:number(row.vmaf)},
        {label:'Estimated video size', value:`${number(row.gib)} GiB`},
        {label:'Estimated encode time', value:durationText(row.minutes)},
        {label:'Evidence', value:evidenceText(row), color:state.recommended.includes(row) ? 'var(--accent)' : 'var(--warn)'},
        {label:'Active checks', value:checkText(row, state).split(' · ')[0]},
        {label:'Inspect result', value:'Click or press Enter'},
      ]};
    }}, scales:{x:{scale:scaleLinear, nice:true, grid:true, axis:{label:xLabel}}, y:{scale:scaleLinear, nice:true, grid:true, axis:{label:yLabel}}}});
  mount(id, definition, {ariaLabel:`${yLabel} versus ${xLabel}. Select a measured configuration.`, onSelect:point => {if (point?.datum?.id) select(point.datum.id);}});
}

function renderComparison(selected, baseline) {
  for (const id of ['compare-size','compare-time']) if (hosts[id]) clearChart(id);
  $('clear-pin').hidden = !pinnedId;
  const rows = current().rows;
  $('comparison').innerHTML = `<h3>Compare two settings</h3><div class="compare-identities">${[[baseline,baseline ? label(baseline) : 'Choose a comparison','compare-a'],[selected,label(selected),'compare-b']].map(([row,title,id]) => `<label style="--codec-color:${codecColor(row?.encoder ?? selected.encoder)}">${escape(title)}<select id="${id}"><option value="">Choose settings</option>${rows.map(option => `<option value="${escape(option.id)}" ${option.id === row?.id ? 'selected' : ''}>${escape(label(option))} · ${escape(option.encoder)}</option>`).join('')}</select>${row ? `<span class="note">${number(row.gib)} GiB · ${durationText(row.minutes)} encoding · quality ${number(row.vmaf)}<br>${escape(evidenceText(row))}</span>` : ''}</label>`).join('')}</div><div id="comparison-details"></div>`;
  const details = $('comparison-details');
  if (!baseline || baseline.id === selected.id) {
    details.textContent = baseline ? 'Both selectors have the same settings. Choose a different result to compare.' : 'Choose another setting to compare file size, encoding time and quality with your current selection.';
    return;
  }
  // Different sample coverage is not a meaningful storage/time comparison.
  if (selected.trials.map(t => t.sample).sort().join('|') !== baseline.trials.map(t => t.sample).sort().join('|')) {
    details.textContent = 'These configurations cover different samples. Choose a shared sample scope before comparing size, time and quality.';
    return;
  }
  const delta = tradeoff(selected, baseline);
  const saving = delta.savingPercent === null ? 'Size comparison unavailable' : `${Math.abs(delta.savingPercent).toFixed(1)}% ${delta.savingPercent >= 0 ? 'smaller' : 'larger'}`;
  const timing = delta.timeRatio === null ? 'Time ratio unavailable' : `${delta.timeRatio.toFixed(2)}× the encoding time`;
  const qualityDelta = selected.vmaf - baseline.vmaf;
  const quality = Number.isFinite(qualityDelta) ? `${number(Math.abs(qualityDelta))} VMAF points ${qualityDelta >= 0 ? 'higher' : 'lower'}` : 'Quality difference unavailable';
  details.innerHTML = `<p id="comparison-summary"><strong>${escape(label(selected))} compared with ${escape(label(baseline))}:</strong> ${saving}; ${durationText(Math.abs(delta.extraMinutes))} ${delta.extraMinutes >= 0 ? 'longer' : 'less'} encoding; ${quality}.</p><div class="compare-plots"><div><h3>Video size <span>${saving}</span></h3><div id="compare-size"></div></div><div><h3>Encoding time <span>${durationText(Math.abs(delta.extraMinutes))} ${delta.extraMinutes >= 0 ? 'longer' : 'less'}</span></h3><div id="compare-time"></div></div></div><p class="note">${timing}. Outline: ${escape(label(baseline))}. Filled: ${escape(label(selected))}. Both estimates cover the same footage. Each chart starts at zero; size and time use separate units. Quality is ${$('sample').value ? 'sample mean VMAF' : 'weakest sample mean VMAF'}.</p>`;
  for (const [id,key,unit] of [['compare-size','gib','Video size (GiB)'],['compare-time','minutes','Encoding time (minutes)']]) {
    const marks = [barX([baseline], {x:key, y:() => `${label(baseline)}${label(baseline) === label(selected) ? ` · ${baseline.encoder}` : ''}`, fill:'none', stroke:codecColor(baseline.encoder), strokeWidth:2, maxThickness:18}), barX([selected], {x:key, y:() => `${label(selected)}${label(baseline) === label(selected) ? ` · ${selected.encoder}` : ''}`, fill:codecColor(selected.encoder), maxThickness:18})];
    mount(id, defineChart({marks, theme:chartTheme(), scales:{x:{scale:scaleLinear, domain:[0,Math.max(baseline[key],selected[key],Number.EPSILON)], axis:{label:unit}}, y:{scale:scaleBand}}}), {height:150, ariaLabel:`${unit}: ${label(baseline)} ${number(baseline[key])}, ${label(selected)} ${number(selected[key])}. Bars start at zero.`});
  }
}

function render() {
  const state = current(), {rows, minutes, target} = state;
  const {smallest, fastest, highest} = choices(state.recommended);
  if (!rows.some(row => row.id === selectedId)) selectedId = (smallest ?? rows[0])?.id ?? null;
  const selected = rows.find(row => row.id === selectedId), baseline = rows.find(row => row.id === pinnedId);
  if (!baseline) pinnedId = null;
  $('custom-duration').hidden = $('duration').value !== 'custom';
  $('duration-note').textContent = `Estimates for ${footageLength(minutes)} of footage. Only ${footageLength(sampledSeconds / 60)} was measured. Changing this length does not run a benchmark.`;
  $('scope-note').textContent = $('sample').value ? 'One sample only. A pass here does not qualify these settings for all footage.' : 'Comparing all tested footage. Recommendations require every planned quality check to pass.';
  $('color-key').textContent = `Color: ${$('color-mode').value === 'hardware' ? 'CPU / GPU' : 'codec'}. Legend buttons affect chart visibility only.`;
  drawChart('time-chart', state, 'minutes', 'gib', 'Projected encoding (minutes)', 'Projected video size (GiB)');
  drawChart('quality-chart', state, 'gib', 'vmaf', 'Projected video size (GiB)', $('sample').value ? 'Mean VMAF' : 'Weakest sample mean VMAF');
  const card = (row, title) => `<button class="recommendation-choice" style="--codec-color:${codecColor(row.encoder)}" data-id="${escape(row.id)}" aria-pressed="${row.id === selectedId}"><span class="recommendation-label">${title}</span><strong>${escape(codec(row.encoder))}</strong><span>${escape(qualityName(row))}${result.config.variants?.length > 1 ? ` · ${escape(variant(row)?.label ?? row.variant)}` : ''}</span><span class="recommendation-values">${number(row.gib)} GiB · ${durationText(row.minutes)} encoding · quality ${number(row.vmaf)}</span></button>`;
  $('recommendation').innerHTML = smallest ? `<h2>Start with what matters to you</h2><p class="note">These settings passed quality checks on every required section, including fresh footage. Size and time are estimates. Review the footage before archiving.</p><div class="recommendation-grid">${card(smallest, 'Smallest file')}${card(fastest, 'Fastest encode')}${card(highest, 'Highest measured quality')}</div><p class="note">Among ${state.recommended.length} settings that pass the active checks. One setting may win more than one category.</p>` : '<h2>No fully checked choice in this view</h2><p class="note">No validated project recommendation. You can still explore the charts. Missing, failed or incomplete fresh-footage checks need resolving before these settings can be recommended.</p>';
  $('selection').hidden = !selected;
  $('evidence').hidden = !selected;
  $('handoff').hidden = !selected;
  if (!selected) {
    $('result-count').textContent = 'No measured configurations. Review skipped or failed probes below.';
    $('rows').innerHTML = '';
    clearChart('frame-chart');
    resetMedia();
    return;
  }
  $('selected-title').textContent = label(selected);
  $('selection').style.setProperty('--codec-color', codecColor(selected.encoder));
  $('comparison').style.setProperty('--comparison-color', codecColor(baseline?.encoder ?? selected.encoder));
  const reviewCount = selected.trials.filter(trial => reviewed.has(trial.id)).length;
  const timingCounts = selected.trials.map(trial => trial.timings.length);
  const minRuns = Math.min(...timingCounts), maxRuns = Math.max(...timingCounts);
  $('selection-status').textContent = `${evidenceText(selected)}. ${checkText(selected, state).split(' · ')[0]}. ${reviewCount}/${selected.expected} samples marked visually reviewed.${hiddenEncoders.has(selected.encoder) ? ' Selected encoder is hidden in the charts.' : ''}`;
  $('metrics').innerHTML = [
    ['Quality score', number(selected.vmaf), $('sample').value ? 'Sample mean VMAF' : 'Weakest sample mean VMAF'],
    ['Estimated video size', `${number(selected.gib)} GiB`, `For ${footageLength(minutes)} of footage; video only`],
    ['Estimated encoding time', durationText(selected.minutes), `For ${footageLength(minutes)} of footage`],
  ].map(([title,value,note]) => `<div class="metric"><small>${escape(title)}</small><div class="value">${escape(value)}</div><p>${escape(note)}</p></div>`).join('');
  $('selection-details').textContent = `${selected.coverage}/${selected.expected} samples measured; fresh checks ${selected.validation_coverage}/${selected.validation_expected}. Encoder: ${selected.encoder}. Weakest scene: ${result.samples.find(sample => sample.id === selected.weakest_sample)?.label ?? selected.weakest_sample}. Low 5%: ${number(selected.vmaf_p5)}. Active minimum: ${target}. ${selected.projection_basis}. Audio and other streams excluded. ${minRuns === maxRuns ? minRuns : `${minRuns}–${maxRuns}`} timed runs per sample.`;
  renderComparison(selected, baseline);
  $('result-count').textContent = `${rows.length} measured configurations. Select a result to inspect it. Use the two settings selectors above to compare. Size and time are estimates for ${footageLength(minutes)} of footage.`;
  $('rows').innerHTML = ordered(rows, $('sort-by').value).map(row => `<tr class="${row.id === selectedId ? 'selected' : ''} ${row.id === pinnedId ? 'pinned' : ''}"><td><button class="pick" data-id="${escape(row.id)}" aria-pressed="${row.id === selectedId}"><i class="swatch" style="background:${codecColor(row.encoder)}"></i>${escape(label(row))}</button><span class="configuration-meta">${escape(codec(row.encoder))} · ${hardware(row.encoder)} · ${escape(variant(row)?.pixel_format ?? result.config.pixel_format)} · ${escape(variant(row)?.resolution ?? row.resolution ?? 'original')}</span></td><td class="numeric">${number(row.vmaf)}</td><td class="numeric">${number(row.vmaf_p5)}</td><td class="numeric">${number(row.gib)} GiB</td><td class="numeric">${durationText(row.minutes)}</td><td><span class="score-status ${state.qualifying.includes(row) ? 'meets' : 'below'}">${escape(checkText(row, state))}</span><span class="cell-secondary">${row.coverage}/${row.expected} samples</span></td><td><button data-pin="${escape(row.id)}" aria-pressed="${row.id === pinnedId}" aria-label="Compare with ${escape(label(row))}">${row.id === pinnedId ? 'In comparison' : 'Compare'}</button></td></tr>`).join('');
  const policy = archiveSettings(result, selected.trials[0]);
  $('retention-summary').textContent = `Archive export: audio ${policy.audio_mode}${policy.audio_mode === 'aac' ? ` at ${policy.audio_kbps_per_channel} kbps/channel` : ''}; omitted audio tracks: ${policy.drop_audio_tracks.join(', ') || 'none'}. Subtitles: ${policy.subtitles}; attachments: ${policy.attachments}; metadata and chapters: ${policy.metadata}. Audio retention is not benchmarked.`;
  renderEvidence(selected, baseline, state);
}

function sampleBars(trial, name, target, selected) {
  if (!trial) return `<p class="quality-caption">${escape(name)}: not measured</p>`;
  const clamp = score => Math.min(100, Math.max(0, score));
  return `<div class="quality-track" aria-hidden="true"><span class="quality-bar" style="width:${clamp(trial.vmaf)}%;background:${selected ? 'var(--accent)' : 'var(--blue)'}"></span>${Number.isFinite(trial.vmaf_p5) ? `<span class="quality-p5" style="left:${clamp(trial.vmaf_p5)}%"></span>` : ''}<span class="quality-target" style="left:${target}%"></span></div><div class="quality-caption">${escape(name)}: mean ${number(trial.vmaf)} · low 5% ${number(trial.vmaf_p5)}</div>`;
}
function renderEvidence(selected, baseline, state) {
  const allSelected = configurations(result, state.minutes).find(row => row.id === selected.id);
  const allBaseline = configurations(result, state.minutes).find(row => row.id === baseline?.id);
  $('sample-evidence').innerHTML = result.samples.filter(sample => (sample.stage ?? 'tuning') === 'tuning').map(sample => {
    const trial = allSelected.trials.find(row => row.sample === sample.id), pinned = allBaseline?.trials.find(row => row.sample === sample.id);
    const passes = trial && eligible([trial], state.target, state.lowTarget).length;
    return `<div class="sample-row"><div class="sample-label"><button data-sample="${escape(sample.id)}" ${trial ? '' : 'disabled'}>${escape(sample.label)}</button><p class="${passes ? 'meets' : 'below'}">${trial ? passes ? 'Passes quality floors' : 'Quality floors not met' : 'Not measured at these settings'}</p></div><div>${sampleBars(trial, 'Selected', state.target, true)}${allBaseline && allBaseline.id !== allSelected.id ? sampleBars(pinned, 'Comparison', state.target, false) : ''}</div></div>`;
  }).join('');
  const missing = Math.max(0, result.config.samples.length - result.samples.length);
  if (missing) $('sample-evidence').insertAdjacentHTML('beforeend', `<p class="warn note">${missing} planned samples have no validated sample data. Collection qualification is blocked.</p>`);
  const previous = $('review-sample').value;
  const reviewTrials = evidenceTrials(result, selected);
  $('review-sample').replaceChildren(...reviewTrials.map(trial => new Option(`${trial.stage ?? 'tuning'} · ${result.samples.find(sample => sample.id === trial.sample).label}`, trial.sample)));
  if (reviewTrials.some(trial => trial.sample === previous)) $('review-sample').value = previous;
  const trial = reviewTrials.find(row => row.sample === $('review-sample').value);
  const sample = result.samples.find(row => row.id === trial.sample);
  const pinnedTrial = baseline?.trials.find(row => row.sample === sample.id);
  if (inspectedTrialId !== trial.id) { loadReviewMedia(trial, sample); inspectedTrialId = trial.id; $('cursor-time').textContent = ''; }
  $('reviewed').checked = reviewed.has(trial.id);
  $('detail-title').textContent = `${sample.label} · ${label(trial)}`;
  const output = {width:trial.width ?? sample.output_video?.width ?? sample.video.width, height:trial.height ?? sample.output_video?.height ?? sample.video.height, pix_fmt:trial.pixel_format ?? sample.output_video?.pix_fmt};
  $('format-summary').textContent = `Source: ${sample.video.width} × ${sample.video.height} ${sample.video.pix_fmt}. Output: ${output.width} × ${output.height} ${output.pix_fmt}. Frame rate retained. Measured ${number(trial.bytes/1048576)} MiB in ${trial.encode_seconds.toFixed(2)} seconds.`;
  const preview = (id, source) => { if (typeof source === 'string' && /^data:image\/(png|jpeg|webp);base64,/.test(source)) { $(id).src = source; $(id).hidden = false; } else { $(id).removeAttribute('src'); $(id).hidden = true; } };
  for (const id of ['original-preview','wipe-original']) preview(id, sample.preview);
  for (const id of ['encoded-preview','wipe-encoded']) preview(id, trial.preview);
  $('baseline-preview-wrap').hidden = !pinnedTrial || pinnedTrial.id === trial.id;
  preview('baseline-preview', pinnedTrial?.preview);
  $('exact').textContent = JSON.stringify({...trial, preview:undefined, vmaf_frames:undefined}, null, 2);
  const settings = archiveSettings(result, trial);
  $('handoff-title').textContent = `${codec(trial.encoder)} with ${qualityName(trial)}`;
  $('handoff').style.setProperty('--codec-color', codecColor(trial.encoder));
  $('handoff-settings').textContent = JSON.stringify(settings, null, 2);
  $('handoff-status').textContent = `${evidenceText(selected)}. ${checkText(selected, state).split(' · ')[0]}. Review the footage before encoding.`;
  $('copy-status').textContent = '';
  $('handoff-message').value = `I chose ${codec(trial.encoder)} with ${qualityName(trial)} in ArchiveBench.\n\nUse encoder ${settings.encoder}, quality ${settings.quality}, pixel format ${settings.pixel_format}, and resolution ${settings.resolution}. Use the attached archive-settings.json for the full format and stream-retention settings.\n\nFor ${footageLength(state.minutes)} of footage, the report estimates ${number(selected.gib)} GiB of video and ${durationText(selected.minutes)} of encoding. Measured quality score: ${number(selected.vmaf)} VMAF. Saved evidence: ${settings.evidence_status}; fresh checks: ${settings.validation_coverage}/${settings.validation_expected}. Active checks: ${checkText(selected, state)}.\n\nHelp me review these settings and prepare an archive script using the project's verification checks. Keep originals intact. Confirm footage paths and visual review before encoding.`;
  drawFrames(trial, pinnedTrial, state);
  showStill = renderStills(trial, seek);
}
function drawFrames(trial, baseline, state) {
  const frames = trial.vmaf_frames ?? [], pinned = baseline?.id !== trial.id ? baseline?.vmaf_frames ?? [] : [];
  $('frame-chart').hidden = !frames.length;
  $('frame-note').textContent = frames.length ? `${frames.length} scored frames for the selected sample. Green: selected${pinned.length ? '; blue: baseline' : ''}. Click a point or a low-score shortcut to seek loaded sample clips. Gaps may reflect metric subsampling; lines join measured scores.${baseline && baseline.id !== trial.id && !pinned.length ? ' Baseline frame scores are unavailable.' : ''}` : 'Frame-level scores were not saved in this run. Mean and low-5% values cannot reconstruct a timeline. New benchmarks save scored-frame timestamps; no data has been invented for this report.';
  const weak = [];
  for (const frame of [...frames].sort((a,b) => a.vmaf-b.vmaf)) {
    if (weak.every(other => Math.abs(other.seconds-frame.seconds) >= 1)) weak.push(frame);
    if (weak.length === 3) break;
  }
  $('weak-moments').innerHTML = weak.map(frame => `<button data-seek="${frame.seconds}" class="note">${frame.seconds.toFixed(2)}s · VMAF ${number(frame.vmaf)}</button>`).join('');
  if (!frames.length || !$('evidence').open) { clearChart('frame-chart'); return; }
  const theme = chartTheme(), marks = [ruleY([state.target], {stroke:theme.foreground, strokeDasharray:'5 5'})];
  const accent = document.documentElement.classList.contains('light') ? '#126e54' : '#73e0bd';
  const blue = document.documentElement.classList.contains('light') ? '#245a9f' : '#81b9fa';
  for (const [data, stroke, series] of [[frames,accent,'Selected'],[pinned,blue,'Baseline']]) if (data.length) {
    const points = data.map(frame => ({...frame, series}));
    marks.push(lineY(points, {x:'seconds', y:'vmaf', stroke, strokeWidth:1.5}), dot(points, {x:'seconds', y:'vmaf', fill:stroke, r:3}));
  }
  mount('frame-chart', defineChart({marks, theme, focus:'nearest', tooltip:{use:tooltip, className:'benchmark-tooltip', format:point => Number.isFinite(point.datum?.seconds) ? `${point.datum.series} · ${point.datum.seconds.toFixed(2)}s\nVMAF ${number(point.datum.vmaf)}` : `Mean VMAF floor: ${state.target}`}, scales:{x:{scale:scaleLinear, axis:{label:'Seconds from sample start'}}, y:{scale:scaleLinear, grid:true, axis:{label:'Frame VMAF'}}}}), {ariaLabel:'Measured frame quality over sample time. Click to seek both loaded clips.', onSelect:point => {if (Number.isFinite(point?.datum?.seconds)) seek(point.datum.seconds);}});
}

const pair = pairedPlayback($('original-video'), $('encoded-video'), $('video-status'));
const mediaPanel = $('media-controls');
$('original-video').closest('.video-grid').after(mediaPanel);
function loadReviewMedia(trial, sample) {
  resetMedia();
  const assets = trial.review_media;
  const link = $('exact-clip');
  link.hidden = !safeAssetPath(assets?.exact?.path);
  link.removeAttribute('href');
  if (!link.hidden) link.href = assets.exact.path;
  $('conversion-details').textContent = assets ? ['original','encoded'].filter(kind => assets[kind]).map(kind => {
    const media = assets[kind];
    return `${kind}: converted ${media.codec}, ${media.bit_depth}-bit ${media.pixel_format}, ${media.width} × ${media.height}, ${media.fps} fps, video only.`;
  }).join(' ') : 'No companion previews were generated for this trial.';
  if (assets?.status === 'available') pair.load([assets.original?.path, assets.encoded?.path]);
  else $('video-status').textContent = assets?.note ?? 'Companion previews unavailable. Load matching trimmed clips manually or inspect standalone stills.';
}
function resetMedia() {
  pair.reset();
  for (const kind of ['original','encoded']) {
    const video = $(`${kind}-video`);
    video.pause(); video.removeAttribute('src'); video.load();
    if (mediaURLs[kind]) URL.revokeObjectURL(mediaURLs[kind]);
    delete mediaURLs[kind]; $(`${kind}-file`).value = '';
  }
  $('video-status').textContent = 'Load both sample clips for synchronized playback and seeking.';
}
function seek(seconds) {
  pair.seek(seconds);
  const shown = showStill(seconds);
  for (const button of $('weak-moments').querySelectorAll('[data-seek]')) button.setAttribute('aria-pressed', String(Math.abs(Number(button.dataset.seek) - seconds) < 0.0001));
  $('cursor-time').textContent = `Selected sample time: ${seconds.toFixed(2)} seconds. ${shown ? 'Saved frame displayed below.' : 'No saved still for this exact time.'} ${Object.keys(mediaURLs).length === 2 ? 'Loaded players seek together.' : shown ? '' : 'Load both trimmed sample clips to review this moment.'}`;
}
for (const kind of ['original','encoded']) {
  const video = $(`${kind}-video`);
  $(`${kind}-file`).addEventListener('change', event => {
    const file = event.target.files[0]; if (!file) return;
    pair.stop(); if (mediaURLs[kind]) URL.revokeObjectURL(mediaURLs[kind]);
    mediaURLs[kind] = URL.createObjectURL(file); video.src = mediaURLs[kind];
    $('video-status').textContent = 'Clips loaded locally. Confirm they match this sample and configuration; no identity verification is performed.';
  });
}
$('play-pair').addEventListener('click', () => pair.play());
$('pause-pair').addEventListener('click', () => pair.stop());
$('seek-pair').addEventListener('input', event => seek(Number(event.target.value)));
$('original-video').addEventListener('loadedmetadata', () => {$('seek-pair').max = $('original-video').duration;});
function download(name, data) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)], {type:'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
for (const id of ['rows','recommendation']) $(id).addEventListener('click', event => {
  const pin = event.target.closest('[data-pin]'), pick = event.target.closest('[data-id]');
  if (pin) { pinnedId = pin.dataset.pin; render(); }
  else if (pick) select(pick.dataset.id);
});
$('comparison').addEventListener('change', event => {
  const id = event.target.id;
  if (id !== 'compare-a' && id !== 'compare-b') return;
  if (id === 'compare-a') pinnedId = event.target.value || null;
  else if (event.target.value) selectedId = event.target.value;
  render();
  $(id).focus();
});
$('clear-pin').addEventListener('click', () => {pinnedId = null; render();});
$('review-result').addEventListener('click', () => {$('evidence').open = true;});
$('copy-handoff').addEventListener('click', async () => {
  const message = $('handoff-message');
  try { await navigator.clipboard.writeText(message.value); $('copy-status').textContent = 'Message copied. Attach the settings download when you send it.'; }
  catch { message.focus(); message.select(); $('copy-status').textContent = 'Message selected. Press Ctrl+C or use your device’s Copy action.'; }
});
document.querySelector('.plots').addEventListener('click', event => {
  const button = event.target.closest('[data-category]'); if (!button) return;
  const members = encoderNames.filter(name => category(name) === button.dataset.category);
  if (members.every(name => hiddenEncoders.has(name))) members.forEach(name => hiddenEncoders.delete(name));
  else members.forEach(name => hiddenEncoders.add(name));
  render();
});
$('color-mode').addEventListener('change', () => {hiddenEncoders.clear(); render();});
for (const id of ['sample','minutes','target','low-target','max-time','sort-by']) $(id).addEventListener('input', () => {if (id === 'minutes') $('duration').value = 'custom'; if (id === 'sample' && $('sample').value) $('review-sample').value = $('sample').value; render();});
$('duration').addEventListener('change', () => {if ($('duration').value === 'source') $('minutes').value = sourceMinutes; else if ($('duration').value !== 'custom') $('minutes').value = $('duration').value; else $('minutes').value = Number(Number($('minutes').value).toFixed(3)); render();});
$('reset').addEventListener('click', () => {$('target').value = result.config.target_vmaf; $('low-target').value = ''; $('max-time').value = ''; $('sample').value = ''; $('minutes').value = sourceMinutes; $('duration').value = 'source'; hiddenEncoders.clear(); render();});
document.querySelector('.quality-starts').addEventListener('click', event => {const button = event.target.closest('[data-target]'); if (button) {$('target').value = button.dataset.target; render();}});
$('divider').addEventListener('input', () => {$('wipe-original').style.clipPath = `inset(0 ${100-Number($('divider').value)}% 0 0)`;});
$('theme').addEventListener('click', () => {document.documentElement.classList.toggle('light'); render();});
$('evidence').addEventListener('toggle', () => {if ($('evidence').open) render();});
$('review-sample').addEventListener('change', render);
$('sample-evidence').addEventListener('click', event => {const button = event.target.closest('[data-sample]'); if (button) {if ($('sample').value) $('sample').value = button.dataset.sample; render(); $('review-sample').value = button.dataset.sample; render();}});
$('weak-moments').addEventListener('click', event => {const button = event.target.closest('[data-seek]'); if (button) seek(Number(button.dataset.seek));});
$('reviewed').addEventListener('change', () => {if ($('reviewed').checked) reviewed.add(inspectedTrialId); else reviewed.delete(inspectedTrialId); render();});
$('export').addEventListener('click', () => {const trial = result.trials.find(row => row.id === inspectedTrialId); if (trial) download('archive-settings.json', archiveSettings(result, trial));});
$('export-decision').addEventListener('click', () => {
  const state = current(), selected = state.rows.find(row => row.id === selectedId), baseline = state.rows.find(row => row.id === pinnedId);
  if (!selected) return;
  const measurement = row => ({configuration:label(row), samples:row.trials.map(trial => ({id:trial.sample, trial_id:trial.id, bytes:trial.bytes, encode_seconds:trial.encode_seconds, timings:trial.timings, vmaf:trial.vmaf, vmaf_p5:trial.vmaf_p5, visually_reviewed:reviewed.has(trial.id)})), projected_video_gib:row.gib, projected_encode_minutes:row.minutes, coverage:`${row.coverage}/${row.expected}`, checks:checkText(row,state), evidence_status:row.evidence_status,validation_coverage:`${row.validation_coverage}/${row.validation_expected}`,validation_vmaf:row.validation_vmaf,validation_target:result.validation_target ?? null});
  download('archive-decision.json', {type:'archive-decision', version:1, benchmark_identity:result.identity, experiment_status:result.status, saved_mean_target:result.config.target_vmaf,
    scope:$('sample').value || 'collection', footage_minutes:state.minutes, mean_floor:state.target, low_5_floor:state.lowTarget, max_encode_minutes:state.maxMinutes,
    selected:measurement(selected), baseline:baseline ? measurement(baseline) : null, settings:archiveSettings(result, selected.trials.find(trial => trial.id === inspectedTrialId) ?? selected.trials[0]),
    outstanding_review:[...result.samples.filter(sample => (sample.stage ?? 'tuning') === 'tuning').filter(sample => !$('sample').value || sample.id === $('sample').value).filter(sample => !selected.trials.some(trial => trial.sample === sample.id && reviewed.has(trial.id))).map(sample => sample.label),
      ...(!$('sample').value && result.samples.length < result.config.samples.length ? [`${result.config.samples.length-result.samples.length} planned samples have no validated data`] : [])],
    limits:['Size and time are video-only projections of the measured sample mix.', 'Review marks are self-reported in this session; they do not authorize cleanup.', 'Check chroma, resolution, stream retention and editor compatibility before archiving.']});
});
render();
window.__archivebench = {result, render, current};
