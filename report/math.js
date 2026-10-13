export function project(trial, sampleSeconds, minutes) {
  const factor = minutes * 60 / sampleSeconds;
  return { ...trial, gib: trial.bytes * factor / 1073741824, minutes: trial.encode_seconds * factor / 60 };
}
export function eligible(rows, target, lowTarget = null, maxMinutes = null) {
  return rows.filter(row => row.complete !== false && row.vmaf >= target &&
    (row.validation_vmaf == null || row.validation_vmaf >= target) &&
    (lowTarget === null || (Number.isFinite(row.vmaf_p5) && row.vmaf_p5 >= lowTarget)) &&
    (lowTarget === null || row.validation_vmaf == null || (Number.isFinite(row.validation_vmaf_p5) && row.validation_vmaf_p5 >= lowTarget)) &&
    (maxMinutes === null || row.minutes <= maxMinutes));
}
export function smallest(rows, target, lowTarget = null, maxMinutes = null) {
  return eligible(rows, target, lowTarget, maxMinutes).sort((a,b) => a.gib - b.gib || a.bytes - b.bytes)[0] ?? null;
}
export function recommendations(rows, target, lowTarget = null, maxMinutes = null, sampleId = '') {
  return sampleId ? [] : eligible(rows, target, lowTarget, maxMinutes).filter(row => row.evidence_status === 'validated');
}
export const configurationKey = row => JSON.stringify([row.variant ?? 'legacy', row.encoder, row.quality, row.resolution ?? 'original']);

export function evidenceStatus(result, row) {
  const selected = result.validation_shortlist?.some(candidate => candidate.variant === (row.variant ?? 'legacy') && candidate.encoder === row.encoder && candidate.quality === row.quality);
  if (!selected) return 'provisional';
  const required = result.config.validation_samples ?? [];
  const tuning = result.trials.filter(trial => (trial.stage ?? 'tuning') === 'tuning' && (trial.variant ?? 'legacy') === (row.variant ?? 'legacy') && trial.encoder === row.encoder && trial.quality === row.quality);
  const evidence = result.trials.filter(trial => trial.stage === 'validation' && trial.variant === row.variant && trial.encoder === row.encoder && trial.quality === row.quality);
  if (result.skipped?.some(failure => failure.stage === 'validation' && failure.variant === row.variant && failure.encoder === row.encoder && failure.quality === row.quality && failure.terminal)) return 'failed';
  if (evidence.some(trial => trial.vmaf < result.validation_target)) return 'failed';
  if (tuning.some(trial => trial.vmaf < result.validation_target)) return 'failed';
  if (!result.config.samples.every((_, i) => tuning.some(trial => trial.sample === `sample-${i + 1}`)) || required.length !== result.validation_required || required.length === 0 || !required.every((_, i) => evidence.some(trial => trial.sample === `validation-${i + 1}`))) return 'incomplete';
  return 'validated';
}

export function configurations(result, minutes = null, sampleId = '') {
  const tuningSamples = result.samples.filter(sample => (sample.stage ?? 'tuning') === 'tuning');
  const samples = sampleId ? tuningSamples.filter(sample => sample.id === sampleId) : tuningSamples;
  const groups = new Map();
  for (const trial of result.trials) {
    if ((trial.stage ?? 'tuning') !== 'tuning') continue;
    if (!samples.some(sample => sample.id === trial.sample)) continue;
    const key = configurationKey(trial);
    if (!groups.has(key)) groups.set(key, new Map());
    groups.get(key).set(trial.sample, trial);
  }
  const expected = sampleId ? 1 : Math.max(samples.length, result.config.samples.length);
  return [...groups].map(([id, group]) => {
    const trials = [...group.values()];
    const seconds = samples.filter(sample => group.has(sample.id)).reduce((sum, sample) => sum + sample.seconds, 0);
    const weakest = [...trials].sort((a,b) => a.vmaf - b.vmaf)[0];
    const total = {...trials[0], id, trials, complete: trials.length === expected, coverage: trials.length, expected,
      weakest_sample: weakest.sample, evidence_status:'provisional',
      bytes: trials.reduce((sum, trial) => sum + trial.bytes, 0),
      encode_seconds: trials.reduce((sum, trial) => sum + trial.encode_seconds, 0),
      vmaf: Math.min(...trials.map(trial => trial.vmaf)),
      vmaf_p5: trials.every(trial => Number.isFinite(trial.vmaf_p5)) ? Math.min(...trials.map(trial => trial.vmaf_p5)) : null,
      ssim: Math.min(...trials.map(trial => trial.ssim))};
    total.evidence_status = evidenceStatus(result, total);
    const validation = result.trials.filter(trial => trial.stage === 'validation' && trial.variant === total.variant && trial.encoder === total.encoder && trial.quality === total.quality);
    total.validation_coverage = validation.length;
    total.validation_expected = result.validation_required ?? 0;
    total.validation_vmaf = validation.length ? Math.min(...validation.map(trial => trial.vmaf)) : null;
    total.validation_vmaf_p5 = validation.length && validation.every(trial => Number.isFinite(trial.vmaf_p5)) ? Math.min(...validation.map(trial => trial.vmaf_p5)) : null;
    const sources = new Map();
    for (const sample of samples) {
      if (!group.has(sample.id)) continue;
      const source = sample.source_id ?? sample.id;
      if (!sources.has(source)) sources.set(source, []);
      sources.get(source).push(sample);
    }
    const knownDurations = samples.every(sample => Number.isFinite(sample.source_seconds) && sample.source_seconds > 0);
    if (!knownDurations) return {...project(total, seconds, minutes ?? 60), projection_basis:'sample-duration extrapolation'};
    let projectedBytes = 0, projectedSeconds = 0, sourceSeconds = 0;
    for (const sections of sources.values()) {
      const duration = sections[0].source_seconds;
      sourceSeconds += duration;
      projectedBytes += duration * sections.reduce((sum, sample) => sum + group.get(sample.id).bytes / sample.seconds, 0) / sections.length;
      projectedSeconds += duration * sections.reduce((sum, sample) => sum + group.get(sample.id).encode_seconds / sample.seconds, 0) / sections.length;
    }
    const factor = minutes === null ? 1 : minutes * 60 / sourceSeconds;
    return {...total, source_seconds:sourceSeconds, projected_bytes:projectedBytes,
      projected_encode_seconds:projectedSeconds, projection_basis:'selected-source video-only projection',
      gib:projectedBytes * factor / 1073741824, minutes:projectedSeconds * factor / 60};
  });
}

export function tradeoff(selected, baseline) {
  return {
    savingPercent: baseline.gib > 0 ? (1 - selected.gib / baseline.gib) * 100 : null,
    timeRatio: baseline.minutes > 0 ? selected.minutes / baseline.minutes : null,
    extraMinutes: selected.minutes - baseline.minutes,
  };
}
export function durationText(minutes) {
  const rounded = Math.round(minutes);
  return rounded >= 60 ? `${Math.floor(rounded/60)}h ${rounded%60}m` : `${minutes < 1 ? minutes.toFixed(1) : rounded} min`;
}
export function pareto(rows, dimensions) {
  return rows.filter(row => !rows.some(other => other !== row &&
    dimensions.every(([key, direction]) => direction * other[key] <= direction * row[key]) &&
    dimensions.some(([key, direction]) => direction * other[key] < direction * row[key])));
}
export function archiveSettings(result, trial) {
  const config = result.config;
  const variant = config.variants?.find(variant => variant.id === trial.variant) ?? config;
  const validation = (result.trials ?? []).filter(row => row.stage === 'validation' && row.variant === trial.variant && row.encoder === trial.encoder && row.quality === trial.quality);
  return {version:2,type:'archive-settings',encoder:trial.encoder,quality:trial.quality,
    pixel_format:variant.pixel_format === 'source' ? 'source' : trial.pixel_format,
    resolution:trial.resolution ?? variant.resolution ?? 'original',
    variant:trial.variant ?? 'legacy',variant_label:variant.label ?? 'Single format',
    measured_pixel_format:trial.pixel_format,measured_width:trial.width,measured_height:trial.height,
    minimum_saving:0.1,audio_mode:config.audio_mode ?? 'copy',
    drop_audio_tracks:config.drop_audio_tracks ?? [],audio_kbps_per_channel:config.audio_kbps_per_channel ?? 192,
    subtitles:config.subtitles ?? 'copy',attachments:config.attachments ?? 'copy',metadata:config.metadata ?? 'copy',
    benchmark_identity:result.identity,source_sample:trial.sample,vmaf:trial.vmaf,
    evidence_status:evidenceStatus(result, trial),evidence_scope:validation.length ? 'tuning and validation' : 'tuning',validated:evidenceStatus(result, trial) === 'validated',
    validation_target:result.validation_target ?? null,validation_coverage:validation.length,validation_expected:result.validation_required ?? 0,
    validation_vmaf:validation.length ? Math.min(...validation.map(row => row.vmaf)) : null};
}
