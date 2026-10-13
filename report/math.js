export function project(trial, sampleSeconds, minutes) {
  const factor = minutes * 60 / sampleSeconds;
  return { ...trial, gib: trial.bytes * factor / 1073741824, minutes: trial.encode_seconds * factor / 60 };
}
export function eligible(rows, target) { return rows.filter(row => row.vmaf >= target); }
export function smallest(rows, target) { return eligible(rows, target).sort((a,b) => a.bytes-b.bytes)[0] ?? null; }
export function durationText(minutes) {
  const rounded = Math.round(minutes);
  return rounded >= 60 ? `${Math.floor(rounded/60)}h ${rounded%60}m` : `${minutes < 1 ? minutes.toFixed(1) : rounded} min`;
}
