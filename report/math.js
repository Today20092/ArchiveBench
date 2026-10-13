export function project(trial, sampleSeconds, minutes) {
  const factor = minutes * 60 / sampleSeconds;
  return { ...trial, gib: trial.bytes * factor / 1073741824, minutes: trial.encode_seconds * factor / 60 };
}
export function eligible(rows, target, lowTarget = null, maxMinutes = null) {
  return rows.filter(row => row.complete !== false && row.vmaf >= target &&
    (lowTarget === null || (Number.isFinite(row.vmaf_p5) && row.vmaf_p5 >= lowTarget)) &&
    (maxMinutes === null || row.minutes <= maxMinutes));
}
export function smallest(rows, target, lowTarget = null, maxMinutes = null) {
  return eligible(rows, target, lowTarget, maxMinutes).sort((a,b) => a.gib - b.gib || a.bytes - b.bytes)[0] ?? null;
}
export const configurationKey = row => JSON.stringify([row.encoder, row.quality, row.resolution ?? 'original']);

// Weight projections by measured sample duration, not by the number of samples.
export function configurations(result, minutes, sampleId = '') {
  const samples = sampleId ? result.samples.filter(sample => sample.id === sampleId) : result.samples;
  const groups = new Map();
  for (const trial of result.trials) {
    if (!samples.some(sample => sample.id === trial.sample)) continue;
    const key = configurationKey(trial);
    if (!groups.has(key)) groups.set(key, new Map());
    groups.get(key).set(trial.sample, trial);
  }
  const expected = sampleId ? 1 : Math.max(samples.length, result.config.samples.length);
  return [...groups].map(([id, group]) => {
    const trials = [...group.values()];
    const seconds = samples.filter(sample => group.has(sample.id)).reduce((sum, sample) => sum + sample.seconds, 0);
    const total = {...trials[0], id, trials, complete: trials.length === expected, coverage: trials.length, expected,
      bytes: trials.reduce((sum, trial) => sum + trial.bytes, 0),
      encode_seconds: trials.reduce((sum, trial) => sum + trial.encode_seconds, 0),
      vmaf: Math.min(...trials.map(trial => trial.vmaf)),
      vmaf_p5: trials.every(trial => Number.isFinite(trial.vmaf_p5)) ? Math.min(...trials.map(trial => trial.vmaf_p5)) : null,
      ssim: Math.min(...trials.map(trial => trial.ssim))};
    return project(total, seconds, minutes);
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
  return {version:2,type:'archive-settings',encoder:trial.encoder,quality:trial.quality,
    pixel_format:config.pixel_format === 'source' ? 'source' : trial.pixel_format,
    resolution:trial.resolution ?? config.resolution ?? 'original',
    measured_pixel_format:trial.pixel_format,measured_width:trial.width,measured_height:trial.height,
    minimum_saving:0.1,audio_mode:config.audio_mode ?? 'copy',
    drop_audio_tracks:config.drop_audio_tracks ?? [],audio_kbps_per_channel:config.audio_kbps_per_channel ?? 192,
    subtitles:config.subtitles ?? 'copy',attachments:config.attachments ?? 'copy',metadata:config.metadata ?? 'copy',
    benchmark_identity:result.identity,source_sample:trial.sample,vmaf:trial.vmaf};
}
