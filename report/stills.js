export function evidenceTrials(result, selected) {
  const first = selected.trials[0];
  return result.trials.filter(trial => result.samples.some(sample => sample.id === trial.sample) && trial.variant === first.variant && trial.encoder === first.encoder && trial.quality === first.quality);
}

export function safeStillPath(path) {
  return typeof path === 'string' && /^review\/[a-zA-Z0-9_-]+\/frame-\d+-(original|encoded)\.png$/.test(path);
}

export function renderStills(trial, seek) {
  let panel = document.getElementById('still-review');
  if (!panel) {
    panel = document.createElement('section'); panel.id = 'still-review';
    document.getElementById('format-summary').after(panel);
    const style = document.createElement('style');
    style.textContent = '#still-review{margin:24px 0}#still-review .controls{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:20px;padding:16px 0}#still-review output{font-weight:400;color:var(--muted);font-variant-numeric:tabular-nums}.still-pair{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px}.still-pair figure{margin:12px 0}.still-pair figcaption{font-size:13px;font-weight:600;margin-bottom:10px}.still-viewport{position:relative;overflow:hidden;background:var(--bg);border:1px solid var(--line);border-radius:5px}.still-viewport img{position:absolute;max-width:none;height:auto}@media(max-width:760px){.still-pair{grid-template-columns:1fr}#still-review .controls{grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}';
    document.head.append(style);
  }
  panel.replaceChildren();
  const evidence = trial.review_stills;
  const note = document.createElement('p'); note.className = 'note';
  note.textContent = evidence?.note ?? 'Native-size weak-moment stills are unavailable. They are generated for validated finalists after scoring, within the remaining budget. Embedded first-frame previews remain available below.';
  panel.append(note);
  if (!evidence?.moments?.length) return () => false;
  const controls = document.createElement('div'); controls.className = 'controls';
  const fields = {}, outputs = {};
  for (const [key, title, min, max, value] of [['moment','Scored moment',0,evidence.moments.length-1,0], ['zoom','Crop zoom',1,8,1], ['x','Horizontal position',0,100,50], ['y','Vertical position',0,100,50]]) {
    const label = document.createElement('label'); label.textContent = title;
    const input = document.createElement('input'); input.type = 'range'; input.min = min; input.max = max; input.value = value; input.step = key === 'zoom' ? '.25' : '1'; input.id = `still-${key}`; fields[key] = input;
    const output = document.createElement('output'); output.htmlFor = input.id; outputs[key] = output;
    label.append(output,input); controls.append(label);
  }
  panel.append(controls);
  const caption = document.createElement('p'); caption.className = 'note'; panel.append(caption);
  const pair = document.createElement('div'); pair.className = 'still-pair'; panel.append(pair);
  const images = [];
  for (const kind of ['original','encoded']) {
    const figure = document.createElement('figure'); const title = document.createElement('figcaption');
    const viewport = document.createElement('div'); viewport.className = 'still-viewport';
    const img = document.createElement('img'); img.alt = `${kind} at selected scored moment`;
    const error = document.createElement('p'); error.className = 'note'; error.hidden = true;
    img.addEventListener('error', () => { img.hidden = true; error.hidden = false; error.textContent = 'Still unavailable. Restore the review folder beside report.html or resume generation. First-frame previews remain below.'; });
    viewport.append(img); figure.append(title,viewport,error); pair.append(figure); images.push({kind,img,viewport,title,error});
  }
  function crop() {
    const zoom = Number(fields.zoom.value), x = Number(fields.x.value)/100, y = Number(fields.y.value)/100;
    outputs.zoom.textContent = `${zoom}×`;
    outputs.x.textContent = `${fields.x.value}%`;
    outputs.y.textContent = `${fields.y.value}%`;
    for (const {img} of images) { img.style.width = `${zoom*100}%`; img.style.left = `${-x*(zoom-1)*100}%`; img.style.top = `${-y*(zoom-1)*100}%`; }
  }
  function moment() {
    const frame = evidence.moments[Number(fields.moment.value)];
    outputs.moment.textContent = `${Number(fields.moment.value) + 1} of ${evidence.moments.length} · ${frame.seconds.toFixed(2)} sec`;
    caption.textContent = `Frame ${frame.frame_index} · ${frame.seconds.toFixed(3)} seconds from sample start · VMAF ${frame.vmaf.toFixed(2)}. The same normalized crop is shown in both native images. Enlarging a reduced output does not recover detail.`;
    for (const {kind,img,viewport,title,error} of images) {
      const asset = frame[kind]; title.textContent = `${kind === 'original' ? 'Original' : 'Encoded'} · ${asset.width} × ${asset.height}`;
      viewport.style.aspectRatio = `${asset.width}/${asset.height}`; img.hidden = false; error.hidden = true;
      if (safeStillPath(asset.path)) img.src = asset.path; else {img.removeAttribute('src'); img.hidden = true; error.hidden = false; error.textContent = 'Invalid still path. Regenerate the review assets.';}
    }
    crop();
  }
  fields.moment.addEventListener('input', () => { moment(); seek(evidence.moments[Number(fields.moment.value)].seconds); });
  for (const key of ['zoom','x','y']) fields[key].addEventListener('input', crop);
  moment();
  return seconds => {
    const index = evidence.moments.findIndex(frame => Math.abs(frame.seconds - seconds) < 0.0001);
    if (index < 0) return false;
    fields.moment.value = index;
    moment();
    return true;
  };
}
