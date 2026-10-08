/* Nexsound · utilidades compartidas por todas las herramientas (necesita Engine cargado antes). */
const NX = (() => {
  'use strict';
  const E = Engine;
  const $ = (id) => document.getElementById(id);
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const db = (v) => 20 * Math.log10(Math.max(v, 1e-12));
  const undb = (d) => Math.pow(10, d / 20);
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmtTime = (s) => { s = Math.max(0, s); const m = Math.floor(s / 60), r = Math.floor(s % 60); return m + ':' + String(r).padStart(2, '0'); };
  const cleanName = (s) => s.replace(/\.[^.]+$/, '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^\w\-]+/g, '_').replace(/^_+|_+$/g, '') || 'tema';

  // ---------- audio de un archivo (cualquier formato que lea el navegador) a 44,1 kHz estéreo
  async function decodeFile(file) {
    const buf = await file.arrayBuffer();
    const Ctx = window.OfflineAudioContext || window.webkitOfflineAudioContext;
    const ctx = new Ctx(2, 1, 44100);
    let ab;
    try { ab = await new Promise((res, rej) => { const p = ctx.decodeAudioData(buf, res, rej); if (p && p.then) p.then(res, rej); }); }
    catch (e) { throw new Error('No se pudo leer «' + file.name + '». Prueba con MP3 o WAV.'); }
    const L = new Float32Array(ab.getChannelData(0)), R = ab.numberOfChannels > 1 ? new Float32Array(ab.getChannelData(1)) : new Float32Array(L);
    return { L, R, sr: ab.sampleRate, name: file.name, duration: ab.duration };
  }

  // ---------- zona para soltar archivos
  function dropzone(el, input, onFiles) {
    ['dragenter', 'dragover'].forEach((t) => el.addEventListener(t, (e) => { e.preventDefault(); el.classList.add('over'); }));
    ['dragleave', 'drop'].forEach((t) => el.addEventListener(t, (e) => { e.preventDefault(); el.classList.remove('over'); }));
    el.addEventListener('drop', (e) => { const f = [...(e.dataTransfer.files || [])]; if (f.length) onFiles(f); });
    input.addEventListener('change', (e) => { const f = [...e.target.files]; if (f.length) onFiles(f); e.target.value = ''; });
  }

  // ---------- avisos
  function toast(m, ms = 3500) {
    let t = $('nx-toast'); if (!t) { t = document.createElement('div'); t.id = 'nx-toast'; t.className = 'toast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
    t.textContent = m; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => (t.hidden = true), ms);
  }

  // ---------- descargas: dentro de Claude con permiso del visitante (formatos no admitidos van en ZIP); fuera, enlace directo
  const CLAUDE_EXT = ['gif', 'png', 'jpg', 'jpeg', 'webp', 'mp4', 'webm', 'txt', 'json', 'md', 'docx', 'pptx', 'epub', 'csv', 'ttf', 'html', 'svg', 'pdf', 'xlsx', 'zip'];
  let capP;
  function downloadsCap() { if (!capP) capP = (async () => { try { return window.claude && window.claude.use ? await window.claude.use('downloads') : null; } catch (e) { return null; } })(); return capP; }
  function linkSave(name, blob) { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 5000); toast('Descargando ' + name); }
  async function save(name, data) {
    const blob = data instanceof Blob ? data : new Blob([data]);
    const cap = await downloadsCap();
    if (!cap) return linkSave(name, blob);
    let fn = name, payload = blob; const ext = name.split('.').pop().toLowerCase();
    if (!CLAUDE_EXT.includes(ext)) { const bytes = new Uint8Array(await blob.arrayBuffer()); payload = new Blob(E.zipParts([{ name, data: bytes }]), { type: 'application/zip' }); fn = name.replace(/\.[^.]+$/, '') + '.zip'; }
    try { await cap.save({ filename: fn, data: payload }); toast('Descarga lista: ' + fn); }
    catch (e) { if (e && e.code === 'declined') return; if (e && e.code === 'rate_limited') return toast('Ya hay una descarga esperando tu confirmación.'); linkSave(name, blob); }
  }
  const zip = (files) => new Blob(E.zipParts(files.map((f) => ({ name: f.name, data: f.data instanceof Uint8Array ? f.data : typeof f.data === 'string' ? new TextEncoder().encode(f.data) : new Uint8Array(f.data) }))), { type: 'application/zip' });
  const wav = (L, R, sr) => E.wav24(L, R, sr);

  // ---------- reproductor (uno a la vez)
  const player = (() => {
    let ctx = null, src = null, gain = null, startedAt = 0, offset = 0, onStop = null, cur = null;
    function ensure() { ctx = ctx || new (window.AudioContext || window.webkitAudioContext)(); return ctx; }
    function stop() { if (src) { src.onended = null; try { src.stop(); } catch (e) {} src = null; } const cb = onStop; onStop = null; cur = null; if (cb) cb(); }
    function play(L, R, sr, opts = {}) {
      stop(); ensure(); if (ctx.state === 'suspended') ctx.resume();
      const buf = ctx.createBuffer(2, L.length, sr); buf.copyToChannel(L, 0); buf.copyToChannel(R, 1);
      src = ctx.createBufferSource(); src.buffer = buf; gain = ctx.createGain(); gain.gain.value = opts.gain ?? 1;
      src.connect(gain).connect(opts.dest || ctx.destination);
      offset = clamp(opts.offset || 0, 0, buf.duration); startedAt = ctx.currentTime; src.start(0, offset, opts.duration);
      onStop = opts.onStop || null; cur = opts.id ?? null;
      const me = src; src.onended = () => { if (src === me) stop(); };
      return src;
    }
    const position = () => (src && ctx ? offset + ctx.currentTime - startedAt : null);
    return { play, stop, position, ctx: () => ensure(), current: () => cur, playing: () => !!src };
  })();
  // botón ▶/■ enlazado al reproductor
  const ICON_PLAY = '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3 1.5v11l9.5-5.5z" fill="currentColor"/></svg>';
  const ICON_STOP = '<svg viewBox="0 0 14 14" aria-hidden="true"><rect x="2.5" y="2.5" width="9" height="9" rx="1" fill="currentColor"/></svg>';
  function playButton(btn, getAudio, id) {
    btn.innerHTML = ICON_PLAY;
    btn.addEventListener('click', () => {
      if (player.current() === id) { player.stop(); return; }
      const a = getAudio(); if (!a) return;
      player.play(a.L, a.R, a.sr, { id, offset: a.offset, duration: a.duration, gain: a.gain, onStop: () => { btn.classList.remove('on'); btn.innerHTML = ICON_PLAY; } });
      btn.classList.add('on'); btn.innerHTML = ICON_STOP;
    });
  }

  // ---------- dibujo
  function setupCanvas(cv) { const dpr = window.devicePixelRatio || 1, w = cv.clientWidth || 300, h = cv.clientHeight || 60; cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); const x = cv.getContext('2d'); x.setTransform(dpr, 0, 0, dpr, 0, 0); return { x, w, h }; }
  function drawWave(cv, L, R, color, from = 0, to = L.length) {
    const { x, w, h } = setupCanvas(cv); x.clearRect(0, 0, w, h);
    x.fillStyle = css('--line'); x.fillRect(0, h / 2, w, 1);
    const n = to - from, step = Math.max(1, Math.floor(n / w)); const pk = []; let mx = 1e-9;
    for (let p = 0; p < w; p++) { let m = 0; const a = from + p * step; for (let i = a; i < Math.min(to, a + step); i += Math.max(1, step >> 6)) m = Math.max(m, Math.abs(L[i]), Math.abs(R[i])); pk.push(m); mx = Math.max(mx, m); }
    x.fillStyle = color || css('--accent');
    pk.forEach((m, p) => { const hh = Math.max(1, (m / mx) * (h - 4)); x.fillRect(p, (h - hh) / 2, 1, hh); });
    return { x, w, h };
  }

  // ---------- filtros biquad (RBJ) en el dominio del tiempo
  function biquad(type, f0, sr, q = 0.7071, gainDb = 0) {
    const A = Math.pow(10, gainDb / 40), w0 = 2 * Math.PI * f0 / sr, c = Math.cos(w0), s = Math.sin(w0), al = s / (2 * q);
    let b0, b1, b2, a0, a1, a2;
    if (type === 'lowpass') { b0 = (1 - c) / 2; b1 = 1 - c; b2 = (1 - c) / 2; a0 = 1 + al; a1 = -2 * c; a2 = 1 - al; }
    else if (type === 'highpass') { b0 = (1 + c) / 2; b1 = -(1 + c); b2 = (1 + c) / 2; a0 = 1 + al; a1 = -2 * c; a2 = 1 - al; }
    else if (type === 'peak') { b0 = 1 + al * A; b1 = -2 * c; b2 = 1 - al * A; a0 = 1 + al / A; a1 = -2 * c; a2 = 1 - al / A; }
    else if (type === 'lowshelf') { const sa = 2 * Math.sqrt(A) * al; b0 = A * ((A + 1) - (A - 1) * c + sa); b1 = 2 * A * ((A - 1) - (A + 1) * c); b2 = A * ((A + 1) - (A - 1) * c - sa); a0 = (A + 1) + (A - 1) * c + sa; a1 = -2 * ((A - 1) + (A + 1) * c); a2 = (A + 1) + (A - 1) * c - sa; }
    else if (type === 'highshelf') { const sa = 2 * Math.sqrt(A) * al; b0 = A * ((A + 1) + (A - 1) * c + sa); b1 = -2 * A * ((A - 1) + (A + 1) * c); b2 = A * ((A + 1) + (A - 1) * c - sa); a0 = (A + 1) - (A - 1) * c + sa; a1 = 2 * ((A - 1) - (A + 1) * c); a2 = (A + 1) - (A - 1) * c - sa; }
    else if (type === 'bandpass') { b0 = al; b1 = 0; b2 = -al; a0 = 1 + al; a1 = -2 * c; a2 = 1 - al; }
    return [b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0];
  }
  function filt(x, co, out) {
    const [b0, b1, b2, a1, a2] = co, y = out || new Float32Array(x.length); let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
    for (let i = 0; i < x.length; i++) { const v = x[i], o = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2; x2 = x1; x1 = v; y2 = y1; y1 = o; y[i] = o; }
    return y;
  }

  // ---------- loudness (ITU-R BS.1770 / EBU R128): integrado, rango, pico real aproximado
  function loudness(L, R, sr) {
    const k1 = biquad('highshelf', 1681.97, sr, 0.7071, 3.9998), k2 = biquad('highpass', 38.13, sr, 0.5003);
    const kl = filt(filt(L, k1), k2), kr = filt(filt(R, k1), k2);
    const blk = Math.round(0.4 * sr), hop = Math.round(0.1 * sr), ms = [];
    const pl = new Float64Array(L.length + 1), pr = new Float64Array(L.length + 1);
    for (let i = 0; i < L.length; i++) { pl[i + 1] = pl[i] + kl[i] * kl[i]; pr[i + 1] = pr[i] + kr[i] * kr[i]; }
    for (let a = 0; a + blk <= L.length; a += hop) ms.push(((pl[a + blk] - pl[a]) + (pr[a + blk] - pr[a])) / blk);
    const lk = (m) => -0.691 + 10 * Math.log10(m + 1e-15);
    let g1 = ms.filter((m) => lk(m) > -70); const mean = (a) => a.reduce((s, v) => s + v, 0) / Math.max(a.length, 1);
    const rel = lk(mean(g1)) - 10, g2 = g1.filter((m) => lk(m) > rel), I = g2.length ? lk(mean(g2)) : -70;
    // rango de sonoridad con bloques de 3 s
    const sb = Math.round(3 * sr), st = [];
    for (let a = 0; a + sb <= L.length; a += Math.round(sr)) st.push(lk(((pl[a + sb] - pl[a]) + (pr[a + sb] - pr[a])) / sb));
    const stG = st.filter((v) => v > -70), stRel = stG.length ? 10 * Math.log10(mean(stG.map((v) => Math.pow(10, v / 10)))) - 20 : -70;
    const sv = stG.filter((v) => v > stRel).sort((a, b) => a - b), pct = (p) => sv.length ? sv[Math.min(sv.length - 1, Math.floor(p * (sv.length - 1)))] : 0;
    const LRA = sv.length ? pct(0.95) - pct(0.1) : 0;
    const shortMax = st.length ? Math.max(...st) : -70;
    // pico real: interpolación sinc ×4 alrededor de los picos de muestra más altos
    let sp = 0; for (let i = 0; i < L.length; i++) { const v = Math.max(Math.abs(L[i]), Math.abs(R[i])); if (v > sp) sp = v; }
    let tp = sp; const thr = sp * 0.85;
    const sinc = (t) => (t === 0 ? 1 : Math.sin(Math.PI * t) / (Math.PI * t));
    for (const ch of [L, R]) for (let i = 8; i < ch.length - 8; i++) {
      if (Math.abs(ch[i]) < thr) continue;
      for (let ph = 1; ph < 4; ph++) { const f = ph / 4; let v = 0; for (let k = -7; k <= 8; k++) { const t = f - k, wv = 0.5 + 0.5 * Math.cos(Math.PI * t / 8.5); v += ch[i + k] * sinc(t) * wv; } tp = Math.max(tp, Math.abs(v)); }
      i += 2;
    }
    return { I, LRA, shortMax, samplePeak: db(sp), truePeak: db(tp), crest: db(sp) - (I + 0.691) };
  }

  // ---------- espectro medio en tercios de octava
  const THIRDS = (() => { const f = []; for (let i = -17; i <= 13; i++) f.push(1000 * Math.pow(2, i / 3)); return f.filter((v) => v >= 20 && v <= 20000); })();
  function spectrum(L, R, sr, opts = {}) {
    const N = 8192, w = E.hann(N), re = new Float64Array(N), im = new Float64Array(N), acc = new Float64Array(N / 2 + 1), accS = new Float64Array(N / 2 + 1);
    const hop = Math.max(N, Math.floor(L.length / 160)); let c = 0;
    for (let a = 0; a + N < L.length; a += hop) {
      for (let i = 0; i < N; i++) { re[i] = (L[a + i] + R[a + i]) * 0.5 * w[i]; im[i] = (L[a + i] - R[a + i]) * 0.5 * w[i]; }
      E.fft(re, im, false);
      for (let k = 0; k <= N / 2; k++) { const nk = (N - k) % N; const mr = (re[k] + re[nk]) / 2, mi = (im[k] - im[nk]) / 2, sr_ = (im[k] + im[nk]) / 2, si = (re[nk] - re[k]) / 2; acc[k] += mr * mr + mi * mi; accS[k] += sr_ * sr_ + si * si; }
      c++;
    }
    const bands = THIRDS.map((fc) => { const lo = fc / Math.pow(2, 1 / 6), hi = fc * Math.pow(2, 1 / 6); let m = 0, s = 0; for (let k = Math.max(1, Math.floor(lo * N / sr)); k <= Math.min(N / 2, Math.ceil(hi * N / sr)); k++) { m += acc[k]; s += accS[k]; } return { fc, mid: 10 * Math.log10(m / Math.max(c, 1) + 1e-15), side: 10 * Math.log10(s / Math.max(c, 1) + 1e-15) }; });
    return { bands, raw: acc, rawSide: accS, N, frames: c };
  }

  // ---------- FIR de fase lineal a partir de una curva (Hz → dB) y convolución por bloques
  function firFromCurve(curveHz, curveDb, sr, taps = 4096) {
    const N = taps, re = new Float64Array(N), im = new Float64Array(N), lf = curveHz.map(Math.log);
    for (let k = 0; k <= N / 2; k++) {
      const f = Math.max(k * sr / N, curveHz[0]), l = Math.log(f); let g;
      if (l <= lf[0]) g = curveDb[0]; else if (l >= lf[lf.length - 1]) g = curveDb[curveDb.length - 1];
      else { let j = 1; while (lf[j] < l) j++; const t = (l - lf[j - 1]) / (lf[j] - lf[j - 1]); g = curveDb[j - 1] * (1 - t) + curveDb[j] * t; }
      re[k] = undb(g); if (k > 0 && k < N / 2) re[N - k] = re[k];
    }
    E.fft(re, im, true);
    const h = new Float32Array(N);
    for (let i = 0; i < N; i++) { const j = (i + N / 2) % N, wv = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (N - 1)); h[i] = re[j] * wv; }
    return h;
  }
  function convolve(x, h) {
    const M = h.length, N = E.nextPow2(M * 4), Bk = N - M + 1, hr = new Float64Array(N), hi = new Float64Array(N);
    hr.set(h); E.fft(hr, hi, false);
    const y = new Float32Array(x.length), re = new Float64Array(N), im = new Float64Array(N), lat = M >> 1, tail = new Float64Array(M - 1);
    const out = new Float32Array(x.length + M);
    for (let a = 0; a < x.length; a += Bk) {
      re.fill(0); im.fill(0); for (let i = 0; i < Bk && a + i < x.length; i++) re[i] = x[a + i];
      E.fft(re, im, false);
      for (let k = 0; k < N; k++) { const r = re[k] * hr[k] - im[k] * hi[k], i2 = re[k] * hi[k] + im[k] * hr[k]; re[k] = r; im[k] = i2; }
      E.fft(re, im, true);
      for (let i = 0; i < N && a + i < out.length; i++) out[a + i] += re[i];
    }
    for (let i = 0; i < x.length; i++) y[i] = out[i + lat];
    return y;
  }

  // ---------- limitador con anticipación (brickwall): techo en dBFS, liberación en ms
  function limit(L, R, sr, ceilingDb = -1, releaseMs = 80, lookMs = 5) {
    const c = undb(ceilingDb), n = L.length, la = Math.max(1, Math.round(lookMs / 1000 * sr)), need = new Float32Array(n);
    for (let i = 0; i < n; i++) { const p = Math.max(Math.abs(L[i]), Math.abs(R[i])); need[i] = p > c ? c / p : 1; }
    // mínimo deslizante hacia delante (ventana la)
    const mn = new Float32Array(n), dq = new Int32Array(n); let h = 0, t = 0;
    for (let i = n - 1; i >= 0; i--) { while (t > h && need[dq[t - 1]] >= need[i]) t--; dq[t++] = i; while (dq[h] > i + la) h++; mn[i] = need[dq[h]]; }
    const rel = Math.exp(-1 / (releaseMs / 1000 * sr)); let g = 1;
    for (let i = 0; i < n; i++) { g = mn[i] < g ? mn[i] : mn[i] + (g - mn[i]) * rel; mn[i] = g; }
    // suavizado del ataque (media móvil de la ventana) y aplicación
    const oL = new Float32Array(n), oR = new Float32Array(n), ring = new Float32Array(la); let s = 0;
    for (let i = 0; i < n; i++) {
      s += mn[i]; if (i >= la) s -= ring[i % la]; ring[i % la] = mn[i];
      const gg = Math.min(s / Math.min(i + 1, la), mn[i]);
      oL[i] = L[i] * gg; oR[i] = R[i] * gg;
      if (oL[i] > c) oL[i] = c; else if (oL[i] < -c) oL[i] = -c; if (oR[i] > c) oR[i] = c; else if (oR[i] < -c) oR[i] = -c;
    }
    return { L: oL, R: oR };
  }

  // ---------- análisis con Engine en un Worker (no bloquea la página)
  function engineWorker(fnName, payload, onProgress) {
    const src = document.getElementById('engine-src').textContent + `
self.onmessage = (e) => { try { const { fn, args } = e.data;
  const r = Engine[fn](...args, (stage, p) => self.postMessage({ type: 'progress', stage: typeof stage === 'number' ? 'Analizando' : stage, p: typeof stage === 'number' ? stage : p }));
  const tr = []; const walk = (o, d) => { if (!o || d > 4) return; if (o instanceof Float32Array) { if (!tr.includes(o.buffer)) tr.push(o.buffer); return; } if (typeof o === 'object') for (const k in o) walk(o[k], d + 1); };
  walk(r, 0); self.postMessage({ type: 'done', r }, tr);
} catch (err) { self.postMessage({ type: 'error', message: String(err && err.message || err) }); } };`;
    const w = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' })));
    return new Promise((resolve, reject) => {
      w.onmessage = (e) => { const d = e.data; if (d.type === 'progress') onProgress && onProgress(d.stage, d.p); else if (d.type === 'done') { w.terminate(); resolve(d.r); } else { w.terminate(); reject(new Error(d.message)); } };
      w.onerror = (e) => { w.terminate(); reject(new Error(e.message || 'El análisis se detuvo.')); };
      const tr = []; for (const a of payload) if (a instanceof Float32Array) tr.push(a.buffer);
      w.postMessage({ fn: fnName, args: payload }, tr);
    });
  }

  // ---------- tarea pesada en un Worker con Engine + NX: fn(...args, progress) se ejecuta fuera de la página
  function task(fn, args, onProgress) {
    const lib = document.getElementById('engine-src').textContent + '\n' + document.getElementById('core-src').textContent;
    const src = lib + `
const __fn = (${fn.toString()});
self.onmessage = async (e) => { try {
  const r = await __fn(...e.data, (p, label) => self.postMessage({ type: 'progress', p, label }));
  const tr = []; const walk = (o, d) => { if (!o || d > 5) return; if (ArrayBuffer.isView(o)) { if (!tr.includes(o.buffer)) tr.push(o.buffer); return; } if (typeof o === 'object') for (const k in o) walk(o[k], d + 1); };
  walk(r, 0); self.postMessage({ type: 'done', r }, tr);
} catch (err) { self.postMessage({ type: 'error', message: String(err && err.message || err) }); } };`;
    const w = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' })));
    return new Promise((resolve, reject) => {
      w.onmessage = (e) => { const d = e.data; if (d.type === 'progress') onProgress && onProgress(d.p, d.label); else if (d.type === 'done') { w.terminate(); resolve(d.r); } else { w.terminate(); reject(new Error(d.message)); } };
      w.onerror = (e) => { w.terminate(); reject(new Error(e.message || 'El proceso se detuvo.')); };
      w.postMessage(args);
    });
  }

  // ---------- Camelot (mezcla armónica)
  const CAMELOT_MAJ = { 0: '8B', 7: '9B', 2: '10B', 9: '11B', 4: '12B', 11: '1B', 6: '2B', 1: '3B', 8: '4B', 3: '5B', 10: '6B', 5: '7B' };
  const CAMELOT_MIN = { 9: '8A', 4: '9A', 11: '10A', 6: '11A', 1: '12A', 8: '1A', 3: '2A', 10: '3A', 5: '4A', 0: '5A', 7: '6A', 2: '7A' };
  const camelot = (root, mode) => (mode === 'menor' ? CAMELOT_MIN : CAMELOT_MAJ)[root];
  function camelotCompatible(a, b) { // misma, ±1 o relativa (A↔B mismo número)
    const pa = { n: parseInt(a), l: a.slice(-1) }, pb = { n: parseInt(b), l: b.slice(-1) };
    if (pa.n === pb.n) return true; const d = Math.min((pa.n - pb.n + 12) % 12, (pb.n - pa.n + 12) % 12);
    return d === 1 && pa.l === pb.l;
  }

  // ---------- generación de PDF muy simple (texto) sin librerías
  function textPdf(lines, title) {
    const enc = (s) => s.replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)');
    const WIN = { '€': 0x80, '–': 0x96, '—': 0x97, '‘': 0x91, '’': 0x92, '“': 0x93, '”': 0x94, '•': 0x95, '…': 0x85, '→': 0x3E };
    const toLatin = (s) => Array.from(s).map((ch) => (WIN[ch] ? String.fromCharCode(WIN[ch]) : ch.charCodeAt(0) < 256 ? ch : '?')).join('');
    const pages = []; const perPage = 50; for (let i = 0; i < lines.length; i += perPage) pages.push(lines.slice(i, i + perPage));
    const objs = []; const add = (s) => { objs.push(s); return objs.length; };
    const font = add('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>');
    const fontB = add('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>');
    const pageIds = []; const pagesId = objs.length + 1 + pages.length * 2;
    for (const pg of pages) {
      let s = 'BT\n'; let y = 800;
      for (const ln of pg) { const bold = ln.startsWith('# '), t = bold ? ln.slice(2) : ln; s += `/${bold ? 'F2' : 'F1'} ${bold ? 13 : 10} Tf 1 0 0 1 50 ${y} Tm (${enc(toLatin(t))}) Tj\n`; y -= bold ? 20 : 15; }
      s += 'ET';
      const c = add(`<< /Length ${s.length} >>\nstream\n${s}\nendstream`);
      pageIds.push(add(`<< /Type /Page /Parent ${pagesId} 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 ${font} 0 R /F2 ${fontB} 0 R >> >> /Contents ${c} 0 R >>`));
    }
    add(`<< /Type /Pages /Kids [${pageIds.map((i) => i + ' 0 R').join(' ')}] /Count ${pageIds.length} >>`);
    const cat = add(`<< /Type /Catalog /Pages ${pagesId} 0 R >>`);
    const info = add(`<< /Title (${enc(toLatin(title))}) /Producer (Nexsound) >>`);
    let out = '%PDF-1.4\n'; const offs = [];
    const bytes = (s) => { const u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i) & 255; return u; };
    objs.forEach((o, i) => { offs.push(out.length); out += `${i + 1} 0 obj\n${o}\nendobj\n`; });
    const xref = out.length; out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n` + offs.map((o) => String(o).padStart(10, '0') + ' 00000 n \n').join('');
    out += `trailer\n<< /Size ${objs.length + 1} /Root ${cat} 0 R /Info ${info} 0 R >>\nstartxref\n${xref}\n%%EOF`;
    return new Blob([bytes(out)], { type: 'application/pdf' });
  }

  // ---------- grabación de vídeo desde un canvas + audio (WebM)
  function recordCanvas(canvas, audio, fps, drawFrame, onProgress) {
    return new Promise((resolve, reject) => {
      if (!window.MediaRecorder || !canvas.captureStream) return reject(new Error('Este navegador no puede grabar vídeo. Usa Chrome o Firefox.'));
      const ctx = new (window.AudioContext || window.webkitAudioContext)(), dest = ctx.createMediaStreamDestination();
      const buf = ctx.createBuffer(2, audio.L.length, audio.sr); buf.copyToChannel(audio.L, 0); buf.copyToChannel(audio.R, 1);
      const src = ctx.createBufferSource(); src.buffer = buf; const an = ctx.createAnalyser(); an.fftSize = 2048; an.smoothingTimeConstant = 0.78;
      src.connect(an); an.connect(dest); src.connect(ctx.destination);
      const stream = new MediaStream([...canvas.captureStream(fps).getVideoTracks(), ...dest.stream.getAudioTracks()]);
      const mime = ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm'].find((m) => MediaRecorder.isTypeSupported(m)) || '';
      const rec = new MediaRecorder(stream, mime ? { mimeType: mime, videoBitsPerSecond: 6e6 } : undefined), chunks = [];
      rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      rec.onstop = () => { ctx.close(); resolve(new Blob(chunks, { type: 'video/webm' })); };
      const freq = new Uint8Array(an.frequencyBinCount), time = new Uint8Array(an.fftSize);
      let raf, t0; const dur = buf.duration;
      const loop = () => { const t = ctx.currentTime - t0; an.getByteFrequencyData(freq); an.getByteTimeDomainData(time); drawFrame(t, freq, time); onProgress && onProgress(Math.min(1, t / dur)); if (t < dur) raf = requestAnimationFrame(loop); };
      rec.start(250); t0 = ctx.currentTime + 0.05; src.start(t0); loop();
      src.onended = () => { cancelAnimationFrame(raf); setTimeout(() => rec.stop(), 300); };
    });
  }

  // ---------- dibujo de vídeo: portada, título y audio animado (barras, círculo, onda o partículas)
  function viz(x, W, H, o) {
    // o: { style, freq (Uint8Array), time (Uint8Array), t, dur, img, title, artist, colors: {bg1,bg2,fg,accent}, brand }
    const c = o.colors, u = Math.min(W, H) / 1080;
    const g = x.createLinearGradient(0, 0, W, H); g.addColorStop(0, c.bg1); g.addColorStop(1, c.bg2); x.fillStyle = g; x.fillRect(0, 0, W, H);
    const bass = o.freq ? o.freq.slice(1, 12).reduce((s, v) => s + v, 0) / (11 * 255) : 0;
    if (o.img) { // portada difuminada de fondo y portada nítida centrada
      x.save(); x.globalAlpha = 0.28; x.filter = 'blur(' + Math.round(40 * u) + 'px)'; const s = Math.max(W / o.img.width, H / o.img.height) * 1.1; x.drawImage(o.img, (W - o.img.width * s) / 2, (H - o.img.height * s) / 2, o.img.width * s, o.img.height * s); x.restore();
    }
    const portrait = H > W * 1.2, side = Math.min(W * (portrait ? 0.72 : 0.42), H * (portrait ? 0.42 : 0.55)) * (1 + bass * 0.04);
    const cx = W / 2, cy = portrait ? H * 0.38 : H * 0.44;
    if (o.style === 'circulo' && o.freq) {
      const R0 = side * 0.55, n = 120; x.save(); x.translate(cx, cy);
      for (let i = 0; i < n; i++) { const k = i < n / 2 ? i : n - i, v = o.freq[Math.floor(2 + k * 3.2)] / 255, a = (i / n) * Math.PI * 2 - Math.PI / 2, len = 12 * u + v * side * 0.35; x.strokeStyle = c.accent; x.globalAlpha = 0.35 + 0.65 * v; x.lineWidth = Math.max(2, side * 0.012); x.beginPath(); x.moveTo(Math.cos(a) * R0, Math.sin(a) * R0); x.lineTo(Math.cos(a) * (R0 + len), Math.sin(a) * (R0 + len)); x.stroke(); }
      x.restore(); x.globalAlpha = 1;
    }
    if (o.img) {
      x.save(); const r = o.style === 'circulo' ? side * 0.5 : 24 * u, s2 = o.style === 'circulo' ? side : side;
      x.beginPath(); if (o.style === 'circulo') x.arc(cx, cy, s2 / 2, 0, Math.PI * 2); else { const a = cx - s2 / 2, b = cy - s2 / 2; x.roundRect ? x.roundRect(a, b, s2, s2, r) : x.rect(a, b, s2, s2); }
      x.shadowColor = 'rgba(0,0,0,.45)'; x.shadowBlur = 50 * u; x.fillStyle = '#000'; x.fill(); x.shadowBlur = 0; x.clip();
      const s = Math.max(s2 / o.img.width, s2 / o.img.height); x.drawImage(o.img, cx - o.img.width * s / 2, cy - o.img.height * s / 2, o.img.width * s, o.img.height * s); x.restore();
    } else {
      x.fillStyle = c.accent; x.globalAlpha = 0.18 + bass * 0.3; x.beginPath(); x.arc(cx, cy, side * 0.42, 0, Math.PI * 2); x.fill(); x.globalAlpha = 1;
      x.fillStyle = c.fg; x.font = `800 ${Math.round(side * 0.14)}px Archivo, Arial, sans-serif`; x.textAlign = 'center'; x.textBaseline = 'middle'; fitText(x, (o.artist || 'Nexsound').toUpperCase(), cx, cy, side * 0.7);
    }
    // textos
    const ty = portrait ? cy + side * 0.5 + 110 * u : cy + side * 0.5 + 70 * u;
    x.textAlign = 'center'; x.textBaseline = 'alphabetic'; x.fillStyle = c.fg;
    x.font = `800 ${Math.round(72 * u)}px Archivo, Arial, sans-serif`; fitText(x, o.title || '', cx, ty, W * 0.86);
    x.globalAlpha = 0.75; x.font = `500 ${Math.round(40 * u)}px "IBM Plex Sans", Arial, sans-serif`; fitText(x, o.artist || '', cx, ty + 58 * u, W * 0.86); x.globalAlpha = 1;
    // audio
    const ay = portrait ? H * 0.8 : H * 0.86, aw = W * 0.84, ax = (W - aw) / 2, ah = (portrait ? H * 0.1 : H * 0.12);
    if ((o.style === 'barras' || o.style === 'circulo') && o.freq) {
      const n = o.style === 'circulo' ? 48 : 64, bw = aw / n;
      for (let i = 0; i < n; i++) { const idx = Math.floor(Math.pow(i / n, 1.7) * 300) + 2, v = o.freq[idx] / 255, hh = Math.max(4 * u, v * ah); x.fillStyle = c.accent; x.globalAlpha = 0.5 + 0.5 * v; x.fillRect(ax + i * bw + bw * 0.18, ay - hh / 2, bw * 0.64, hh); }
      x.globalAlpha = 1;
    } else if (o.style === 'onda' && o.time) {
      x.strokeStyle = c.accent; x.lineWidth = 5 * u; x.beginPath();
      for (let i = 0; i < o.time.length; i += 4) { const px = ax + (i / o.time.length) * aw, py = ay + ((o.time[i] - 128) / 128) * ah; i ? x.lineTo(px, py) : x.moveTo(px, py); } x.stroke();
    } else if (o.style === 'particulas' && o.freq) {
      const n = 90; for (let i = 0; i < n; i++) { const v = o.freq[2 + i * 3] / 255, a = i * 2.39996 + o.t * 0.2, rr = (0.15 + (i / n) * 0.85) * Math.min(W, H) * 0.48 * (1 + v * 0.25); x.fillStyle = c.accent; x.globalAlpha = 0.25 + v * 0.7; x.beginPath(); x.arc(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr, (3 + v * 9) * u, 0, Math.PI * 2); x.fill(); }
      x.globalAlpha = 1;
    }
    // progreso y marca
    if (o.dur) { const py = H - 70 * u; x.fillStyle = c.fg; x.globalAlpha = 0.18; x.fillRect(ax, py, aw, 6 * u); x.globalAlpha = 0.9; x.fillRect(ax, py, aw * Math.min(1, o.t / o.dur), 6 * u); x.globalAlpha = 0.7; x.font = `500 ${Math.round(26 * u)}px "IBM Plex Mono", monospace`; x.textAlign = 'left'; x.fillText(fmtTime(o.t), ax, py - 14 * u); x.textAlign = 'right'; x.fillText(fmtTime(o.dur), ax + aw, py - 14 * u); x.globalAlpha = 1; }
    x.textAlign = 'center'; x.globalAlpha = 0.6; x.fillStyle = c.fg; x.font = `600 ${Math.round(24 * u)}px "IBM Plex Mono", monospace`; x.fillText(o.brand ? o.brand : 'hecho con nexsound.es', cx, 60 * u + (portrait ? 30 * u : 0)); x.globalAlpha = 1;
  }
  function fitText(x, s, cx, y, maxW) { let t = s; while (t.length > 3 && x.measureText(t).width > maxW) t = t.slice(0, -2); if (t !== s) t = t.slice(0, -1) + '…'; x.fillText(t, cx, y); }
  // color dominante de una imagen (para el degradado de fondo)
  function imageColors(img) {
    const cv = document.createElement('canvas'); cv.width = cv.height = 32; const x = cv.getContext('2d'); x.drawImage(img, 0, 0, 32, 32);
    const d = x.getImageData(0, 0, 32, 32).data; let r = 0, g = 0, b = 0, best = null, bs = -1;
    for (let i = 0; i < d.length; i += 4) { r += d[i]; g += d[i + 1]; b += d[i + 2]; const mx = Math.max(d[i], d[i + 1], d[i + 2]), mn = Math.min(d[i], d[i + 1], d[i + 2]), sat = mx - mn; if (sat > bs && mx > 60) { bs = sat; best = [d[i], d[i + 1], d[i + 2]]; } }
    const n = d.length / 4, avg = [r / n, g / n, b / n], dark = (k) => `rgb(${avg.map((v) => Math.round(v * k)).join(',')})`;
    return { bg1: dark(0.55), bg2: dark(0.18), fg: '#ffffff', accent: best ? `rgb(${best.join(',')})` : '#43C19F' };
  }

  return { $, clamp, db, undb, css, esc, fmtTime, cleanName, decodeFile, dropzone, toast, save, zip, wav, player, playButton, ICON_PLAY, ICON_STOP, setupCanvas, drawWave, biquad, filt, loudness, spectrum, THIRDS, firFromCurve, convolve, limit, engineWorker, task, camelot, camelotCompatible, textPdf, recordCanvas, viz, imageColors, E };
})();
