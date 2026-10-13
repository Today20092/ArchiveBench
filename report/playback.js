export const safeAssetPath = value => typeof value === 'string' && !/[\r\n]/.test(value) && /^review\/[A-Za-z0-9_-]+\/[A-Za-z0-9_-]+\.(mp4|mkv|png)$/.test(value);

// One controller owns playback intent; media events only report readiness.
export function pairedPlayback(original, encoded, status) {
  const videos = [original, encoded];
  let generation = 0, operation = 0, wanted = false, blocked = false, seeking = false, starting = false;
  const say = message => { status.textContent = message; };
  const pause = () => videos.forEach(video => video.pause());
  const ready = () => videos.every(video => video.readyState >= 3 && !video.seeking && !video.error);
  async function play() {
    wanted = true;
    if (blocked || seeking || !ready()) { say('Waiting for both previews to be ready.'); return; }
    const token = generation, attempt = ++operation;
    starting = true;
    try {
      await Promise.all(videos.map(video => video.play()));
      if (token !== generation || attempt !== operation || !wanted) return;
      say('Paired playback. Browser timing is approximate, not frame-perfect.');
    } catch {
      if (token !== generation || attempt !== operation) return;
      wanted = false; pause(); say('Playback was blocked or unsupported. Try Play both again or use the exact clip in a native player.');
    } finally { if (token === generation && attempt === operation) starting = false; }
  }
  function stop() { wanted = false; operation++; starting = false; pause(); say('Both previews paused.'); }
  function recover() {
    if (!ready()) return;
    blocked = false;
    if (!seeking && wanted && !starting) play();
    else if (!wanted) say('Both previews ready. Browser timing is approximate.');
  }
  function seek(seconds) {
    if (!videos.every(video => video.readyState >= 1 && Number.isFinite(video.duration))) { say('Load both previews before seeking.'); return; }
    const token = generation, attempt = ++operation;
    starting = false; seeking = true; pause();
    const target = Math.max(0, Math.min(seconds, ...videos.map(video => video.duration)));
    say(`Seeking both previews to ${target.toFixed(2)} seconds.`);
    Promise.all(videos.map(video => new Promise(resolve => {
      if (Math.abs(video.currentTime - target) < .001 && !video.seeking) { resolve(); return; }
      const done = () => { cleanup(); resolve(); };
      const timer = setTimeout(done, 5000);
      const cleanup = () => { clearTimeout(timer); video.removeEventListener('seeked', done); video.removeEventListener('error', done); };
      video.addEventListener('seeked', done); video.addEventListener('error', done);
      video.currentTime = target;
    }))).then(() => {
      if (token !== generation || attempt !== operation) return;
      seeking = false;
      if (!ready() || videos.some(video => Math.abs(video.currentTime - target) > .08)) { blocked = true; wanted = false; say('The seek did not complete on both previews. Restore the companion folder or use a native player.'); return; }
      say(`Both previews at ${target.toFixed(2)} seconds. Browser display is not frame-perfect.`);
      if (wanted) play();
    });
  }
  for (const video of videos) {
    video.controls = false;
    video.addEventListener('waiting', () => { if (!wanted) return; blocked = true; operation++; starting = false; pause(); say('Both previews paused while one buffers.'); });
    for (const event of ['canplay', 'loadeddata']) video.addEventListener(event, recover);
    video.addEventListener('ended', () => { stop(); say('Sample ended. Both previews paused.'); });
    video.addEventListener('error', () => { stop(); blocked = true; say('Preview missing or unsupported. Keep the review folder beside report.html, or open the exact clip in a native player.'); });
  }
  original.addEventListener('timeupdate', () => {
    if (!wanted || seeking || videos.some(video => video.paused)) return;
    const drift = Math.abs(original.currentTime - encoded.currentTime);
    if (drift > .12) { say('Playback drift detected. Aligning both previews.'); seek(Math.min(original.currentTime, encoded.currentTime)); }
  });
  return {
    play, stop, seek,
    reset() { generation++; operation++; wanted = false; blocked = false; seeking = false; starting = false; pause(); videos.forEach(video => { video.removeAttribute('src'); video.load(); }); say('Companion previews are unavailable for this trial. Standalone stills and measurements remain available.'); },
    load(paths) { this.reset(); if (!paths.every(safeAssetPath)) { say('Unsafe companion path rejected.'); return; } videos.forEach((video, i) => { video.src = paths[i]; video.load(); }); say('Loading converted companion previews.'); }
  };
}
