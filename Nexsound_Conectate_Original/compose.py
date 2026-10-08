# NEXSOUND – "Conéctate" (original, compuesto de cero)
# Estilo de EL REY (épico, arpegios pulsantes, Re mayor) + bombo, clap, hats y ritmo exactos de PROMO (124 BPM).
import numpy as np, os, struct
SR = 44100; BPM = 124.0; BEAT = 60 / BPM; STEP = BEAT / 4; BAR = 4 * BEAT
HERE = os.path.dirname(os.path.abspath(__file__)); V3 = HERE + '/../v3/'
rng = np.random.default_rng(124)
def s(t): return int(round(t * SR))
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def db(v): return 10 ** (v / 20)

# ------------------------------------------------------------------ batería de PROMO
def ld(n): return np.fromfile(V3 + n + '.f32', np.float32).reshape(-1, 2).astype(np.float64)
KICK = ld('promo_kick'); CLAP = ld('promo_clap'); HATA = ld('promo_hatA'); HATB = ld('promo_hatB')
# cola del bombo: el promedio sólo es limpio hasta ~105 ms (después se mezcla con el bajo de PROMO);
# se continúa con la misma senoide (frecuencia y fase medidas) decayendo de forma natural.
def extend_kick(k, cut=0.105, tail=0.30):
    m = k.mean(1); a = s(0.045); b = s(cut)
    seg = m[a:b]; zc = np.where(np.diff(np.sign(seg)) != 0)[0]
    f0 = (len(zc) - 1) / 2 / ((zc[-1] - zc[0]) / SR)
    t = np.arange(len(seg)) / SR
    A = np.vstack([np.sin(2 * np.pi * f0 * t), np.cos(2 * np.pi * f0 * t)]).T
    c, *_ = np.linalg.lstsq(A, seg, rcond=None)
    amp = np.hypot(*c); ph = np.arctan2(c[1], c[0])
    n = b + s(tail); tt = np.arange(n - a) / SR
    cont = amp * np.sin(2 * np.pi * f0 * tt + ph) * np.exp(-np.maximum(0, tt - (b - a) / SR) / 0.11)
    out = np.zeros(n); out[:b] = m[:b]
    xf = s(0.012); w = np.linspace(0, 1, xf)
    out[b - xf:b] = m[b - xf:b] * (1 - w) + cont[b - xf - a:b - a] * w
    out[b:] = cont[b - a:]
    fo = s(0.04); out[-fo:] *= np.linspace(1, 0, fo) ** 2
    print('bombo PROMO: cuerpo %.1f Hz' % f0)
    return np.stack([out, out], 1)
KICK = extend_kick(KICK)
for _v in ('CLAP', 'HATA', 'HATB'):
    globals()[_v] = globals()[_v] * (0.9 / np.abs(globals()[_v]).max())

# ------------------------------------------------------------------ utilidades
def add(buf, x, t, g=1.0):
    a = s(t)
    if a >= len(buf): return
    m = min(len(x), len(buf) - a); buf[a:a + m] += x[:m] * g
def pan(x, p):  # x mono -> estéreo, ley de potencia constante
    return np.stack([x * np.cos((p + 1) * np.pi / 4), x * np.sin((p + 1) * np.pi / 4)], 1) * np.sqrt(2)
def fftfilt(x, lo=None, hi=None, order=2):
    n = len(x); N = 1 << int(np.ceil(np.log2(n + 1)))
    X = np.fft.rfft(x, N, axis=0); f = np.fft.rfftfreq(N, 1 / SR); g = np.ones_like(f)
    if lo: g *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    if hi: g *= 1 / np.sqrt(1 + (f / hi) ** (2 * order))
    return np.fft.irfft(X * (g[:, None] if x.ndim == 2 else g), N, axis=0)[:n]
def adsr(n, a, d, sl, r, hold=None):
    t = np.arange(n) / SR; e = np.ones(n) * sl
    e[t < a] = t[t < a] / max(a, 1e-4)
    m = (t >= a) & (t < a + d); e[m] = 1 - (1 - sl) * (t[m] - a) / max(d, 1e-4)
    if hold is not None:
        m = t >= hold; e[m] = e[m] * np.exp(-(t[m] - hold) / max(r, 1e-4))
    return e
def polyblep_saw(freq, n, phase0=0.0):
    dt = freq / SR; ph = (phase0 + dt * np.arange(n)) % 1.0
    y = 2 * ph - 1
    m = ph < dt; tt = ph[m] / dt; y[m] -= tt + tt - tt * tt - 1
    m = ph > 1 - dt; tt = (ph[m] - 1) / dt; y[m] -= tt * tt + tt + tt + 1
    return y

# ------------------------------------------------------------------ instrumentos (compuestos de cero)
def pluck(m, dur=0.45, bright=1.0):
    """Pluck aditivo tipo arpa/marimba de EL REY: armónicos con caída más rápida cuanto más agudos."""
    f = mtof(m); n = s(dur); t = np.arange(n) / SR; y = np.zeros(n)
    K = int(min(40, 14000 / f))
    for k in range(1, K + 1):
        fk = f * k * (1 + 0.0004 * k * k)
        y += (bright ** (k - 1)) / k ** 1.1 * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28)) * np.exp(-t / (0.55 / (1 + 0.45 * (k - 1))))
    y *= np.minimum(t / 0.002, 1); fo = s(0.03); y[-fo:] *= np.linspace(1, 0, fo)
    return y / (np.abs(y).max() + 1e-9)
def supersaw(m, dur, voices=7, detune=0.18, a=0.4, r=0.6, cutoff=3000, width=0.8):
    n = s(dur + r); out = np.zeros((n, 2)); f = mtof(m)
    for i in range(voices):
        d = (i - (voices - 1) / 2) / ((voices - 1) / 2)
        y = polyblep_saw(f * 2 ** (d * detune / 12), n, rng.uniform())
        out += pan(y, d * width) / voices
    env = adsr(n, a, 0.3, 0.85, r, hold=dur)
    out *= env[:, None]
    return fftfilt(out, hi=cutoff, order=2)
def bass(m, dur):
    n = s(dur + 0.02); t = np.arange(n) / SR; f = mtof(m)
    sub = np.sin(2 * np.pi * f * t)
    saw = fftfilt(polyblep_saw(f, n), hi=f * 8, order=2) * 0.6
    y = np.tanh(1.4 * (sub + saw)) * adsr(n, 0.004, 0.08, 0.8, 0.02, hold=dur)
    return pan(y, 0)
def lead(m, dur, vib=True):
    n = s(dur + 0.25); t = np.arange(n) / SR
    f = mtof(m) * (1 + (0.006 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.15) / 0.2, 0, 1) if vib else 0))
    ph = np.cumsum(f) / SR; out = np.zeros((n, 2))
    for i, d in enumerate((-0.12, -0.04, 0.04, 0.12)):
        y = 2 * ((ph * 2 ** (d / 12) + rng.uniform()) % 1) - 1
        out += pan(y, d * 6) / 4
    out = fftfilt(out, hi=4200, order=2)
    return out * adsr(n, 0.01, 0.15, 0.7, 0.12, hold=dur)[:, None]

import functools
pluck = functools.lru_cache(maxsize=None)(pluck)
supersaw = functools.lru_cache(maxsize=None)(supersaw)
bass = functools.lru_cache(maxsize=None)(bass)
lead = functools.lru_cache(maxsize=None)(lead)

# ------------------------------------------------------------------ armonía y melodía (Re mayor)
CH = {  # acordes: raíz grave, notas del pad
    'Bm': (35, [59, 62, 66, 71]), 'G': (31, [55, 59, 62, 67]), 'D': (38, [57, 62, 66, 69]),
    'A': (33, [57, 61, 64, 69]), 'Em': (40, [59, 64, 67, 71]), 'F#m': (42, [57, 61, 66, 69]),
}
PROG_DROP = ['Bm', 'G', 'D', 'A']        # vi – IV – I – V
PROG_VERSO = ['G', 'D', 'Em', 'A']       # IV – I – ii – V
ARP = [0, 2, 1, 3, 2, 4, 3, 1]           # dibujo de arpegio (pulsos de semicorchea como EL REY)
def arp_notes(ch):
    root, pad = CH[ch]; tones = sorted(set([p % 12 for p in pad]))
    notes = [mm for mm in range(62, 88) if mm % 12 in tones]
    return notes
HOOK = {   # (semicorchea de inicio, duración en semicorcheas, nota MIDI) — ritmo 3-3-2
    'Bm': [(0, 3, 78), (3, 3, 76), (6, 2, 74), (8, 4, 71), (12, 2, 74), (14, 2, 76)],
    'G':  [(0, 3, 74), (3, 3, 76), (6, 2, 78), (8, 6, 79), (14, 2, 78)],
    'D':  [(0, 3, 81), (3, 3, 78), (6, 2, 76), (8, 4, 74), (12, 4, 78)],
    'A':  [(0, 3, 76), (3, 3, 73), (6, 2, 76), (8, 8, 76)],
    'Em': [(0, 3, 79), (3, 3, 78), (6, 2, 76), (8, 4, 71), (12, 4, 74)],
}

# ------------------------------------------------------------------ arreglo
#        nombre,      compases, progresión, {elementos: nivel}
ARR = [
    ('Intro',      8, PROG_VERSO, dict(pad=1, pluck=0.6, hats=0.0, open_filter=True)),
    ('Groove',    16, PROG_VERSO, dict(pad=0.6, pluck=0.9, bass=1, kick=1, clap=1, hats=1)),
    ('Break',      8, PROG_DROP,  dict(pad=1, pluck=0.8, hookpluck=1)),
    ('Subida',     8, PROG_DROP,  dict(pad=0.9, pluck=0.9, kick=1, build=True, hats=0.7)),
    ('Drop',      16, PROG_DROP,  dict(pad=0.8, pluck=0.8, bass=1, kick=1, clap=1, hats=1, lead=1)),
    ('Break 2',    8, PROG_VERSO, dict(pad=1, pluck=0.7, hookpluck=0.8)),
    ('Subida 2',   8, PROG_DROP,  dict(pad=0.9, pluck=0.9, kick=1, build=True, hats=0.7)),
    ('Drop final',16, PROG_DROP,  dict(pad=1, pluck=0.8, bass=1, kick=1, clap=1, hats=1, lead=1, octave=True)),
    ('Outro',      8, PROG_VERSO, dict(pad=0.7, pluck=0.7, bass=1, kick=1, clap=0.8, hats=1, fadeout=True)),
]
TOTAL = sum(a[1] for a in ARR)
N = s(TOTAL * BAR + 4)
bus = {k: np.zeros((N, 2)) for k in ('kick', 'clap', 'hats', 'bass', 'pad', 'pluck', 'lead', 'fx')}
kicks = []; midi = {k: [] for k in ('acordes', 'bajo', 'arpegio', 'melodia')}

bar0 = 0
for name, nb, prog, el in ARR:
    for b in range(nb):
        tb = (bar0 + b) * BAR; ch = prog[b % 4]; root, padn = CH[ch]
        last_of_phrase = (b % 8 == 7); last_bar = b == nb - 1
        prog_pos = b / nb
        # ---- batería (patrón exacto de PROMO: bombo a negras, clap en 2 y 4, hats en semicorcheas 3-4 de cada tiempo)
        if el.get('kick'):
            if el.get('build') and b >= nb - 2:
                hits = [i * 2 for i in range(8)] if b == nb - 2 else list(range(16))   # redoble de bombo
                for q in hits:
                    add(bus['kick'], KICK, tb + q * STEP, 0.55 + 0.45 * q / 16); kicks.append(tb + q * STEP)
            else:
                for q in (0, 4, 8, 12):
                    if last_of_phrase and q == 12 and not el.get('build'): continue   # hueco antes de frase, como PROMO
                    add(bus['kick'], KICK, tb + q * STEP); kicks.append(tb + q * STEP)
        if el.get('clap'):
            for q in (4, 12): add(bus['clap'], CLAP, tb + q * STEP, el['clap'])
        if el.get('build') and b >= nb - 4:      # redoble de clap de PROMO en la subida
            step = 4 if b < nb - 2 else (2 if b == nb - 2 else 1)
            for q in range(0, 16, step): add(bus['clap'], CLAP, tb + q * STEP, 0.35 + 0.6 * ((b - (nb - 4)) * 16 + q) / 64)
        hv = el.get('hats', 0)
        if el.get('open_filter') and b >= nb - 4: hv = 0.6
        if hv:
            for beat in range(4):
                add(bus['hats'], HATA, tb + (beat * 4 + 2) * STEP, hv)
                add(bus['hats'], HATB, tb + (beat * 4 + 3) * STEP, hv)
        # ---- bajo a contratiempo (como PROMO): golpes en las corcheas débiles, hueco al final del compás
        if el.get('bass'):
            for q, ln in ((2, 1.6), (6, 1.6), (10, 1.6), (14, 1.2)):
                if last_of_phrase and q == 14: continue
                add(bus['bass'], bass(root, ln * STEP), tb + q * STEP)
                midi['bajo'].append((tb + q * STEP, ln * STEP, root))
        # ---- pad
        if el.get('pad'):
            for m in padn: add(bus['pad'], supersaw(m, BAR * 0.98, a=0.25, r=0.5, cutoff=2600), tb, el['pad'] * 0.22)
            midi['acordes'] += [(tb, BAR, m) for m in padn]
        # ---- arpegio pluck (pulso de semicorchea, el sello de EL REY)
        if el.get('pluck'):
            notes = arp_notes(ch)
            for q in range(16):
                m = notes[(ARP[q % 8] + (2 if q >= 8 else 0)) % len(notes)]
                vel = (1.0 if q % 4 == 0 else 0.7) * el['pluck']
                p = 0.35 if q % 2 else -0.35
                add(bus['pluck'], pan(pluck(m, 0.42, 0.8), p), tb + q * STEP, vel * 0.30)
                midi['arpegio'].append((tb + q * STEP, STEP, m))
        # ---- melodía (gancho)
        if el.get('lead'):
            for q, ln, m in HOOK[ch]:
                add(bus['lead'], lead(m, ln * STEP * 0.95), tb + q * STEP, 0.28)
                if el.get('octave'): add(bus['lead'], lead(m + 12, ln * STEP * 0.95), tb + q * STEP, 0.12)
                midi['melodia'].append((tb + q * STEP, ln * STEP, m))
        if el.get('hookpluck'):
            for q, ln, m in HOOK[ch]:
                add(bus['lead'], pan(pluck(m, 0.9, 0.9), 0), tb + q * STEP, 0.33 * el['hookpluck'])
                midi['melodia'].append((tb + q * STEP, ln * STEP, m))
    # ---- efectos de transición: barrido de ruido en las subidas
    if any(ARR[i][0] == name for i in range(len(ARR))) and dict(el).get('build'):
        n = s(nb * BAR); x = rng.standard_normal((n, 2)) * np.linspace(0, 1, n)[:, None] ** 3
        x = fftfilt(x, lo=800, hi=12000) * 0.25
        add(bus['fx'], x, bar0 * BAR)
    bar0 += nb

# ------------------------------------------------------------------ mezcla
def sidechain(n, hits, depth_db, rel=0.16, att=0.004):
    g = np.ones(n); d = 1 - db(-depth_db); L = s(0.45); tt = np.arange(L) / SR
    curve = 1 - d * np.minimum(tt / att, 1) * np.exp(-np.maximum(tt - att, 0) / rel)
    for k in hits:
        a = s(k); m = min(L, n - a)
        if m > 0: g[a:a + m] = np.minimum(g[a:a + m], curve[:m])
    return g[:, None]
def reverb(x, secs=2.4, mix=0.25, pre=0.02, hp=250):
    n = s(secs); t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-t / (secs / 6.9))[:, None]
    ir = fftfilt(ir, lo=hp, hi=9000); ir[:s(pre)] = 0; ir /= np.sqrt((ir ** 2).sum(0))
    Nf = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, Nf, axis=0) * np.fft.rfft(ir, Nf, axis=0), Nf, axis=0)[:len(x)]
    return x + wet * mix
def delay(x, t, fb=0.35, mix=0.25, taps=4):
    out = x.copy(); d = s(t)
    for i in range(1, taps + 1):
        sh = np.zeros_like(x); sh[d * i:] = x[:-d * i] if d * i < len(x) else 0
        if i % 2: sh = sh[:, ::-1]       # ping-pong
        out += sh * mix * fb ** (i - 1)
    return out

# filtro que se abre en la intro y en las subidas
def sweep(x, start_bar, nbars, f0, f1):
    a = s(start_bar * BAR); b = s((start_bar + nbars) * BAR); seg = x[a:b]
    Nw = 2048; H = 512; w = np.hanning(Nw); f = np.fft.rfftfreq(Nw, 1 / SR)
    pad_ = np.vstack([np.zeros((Nw, 2)), seg, np.zeros((Nw, 2))]); y = np.zeros_like(pad_); ws = np.zeros(len(pad_))
    for i in range(0, len(pad_) - Nw, H):
        p = min(1, max(0, (i - Nw) / len(seg))); fc = f0 * (f1 / f0) ** p
        g = 1 / np.sqrt(1 + (f / fc) ** 4)
        for c in range(2): y[i:i + Nw, c] += np.fft.irfft(np.fft.rfft(pad_[i:i + Nw, c] * w) * g) * w
        ws[i:i + Nw] += w ** 2
    x[a:b] = (y / np.maximum(ws, 1e-3)[:, None])[Nw:Nw + len(seg)]
starts = np.cumsum([0] + [a[1] for a in ARR])
for (name, nb, _, el), st in zip(ARR, starts):
    if el.get('open_filter'):
        for k in ('pad', 'pluck'): sweep(bus[k], st, nb, 400, 14000)
    if el.get('build'):
        for k in ('pad', 'pluck'): sweep(bus[k], st, nb, 900, 16000)

for k in ('pad', 'pluck', 'lead'): bus[k] = fftfilt(bus[k], lo=220, order=2)
n = N
bus['bass'] *= sidechain(n, kicks, 12, rel=0.12)
bus['pad'] = reverb(bus['pad'], 3.0, 0.35) * sidechain(n, kicks, 7)
bus['pluck'] = reverb(delay(bus['pluck'], 3 * STEP, 0.4, 0.22), 2.2, 0.25) * sidechain(n, kicks, 4)
bus['lead'] = reverb(delay(bus['lead'], 3 * STEP, 0.45, 0.25), 2.6, 0.3) * sidechain(n, kicks, 3)
bus['clap'] = reverb(bus['clap'], 1.2, 0.15, hp=500)
bus['fx'] = reverb(bus['fx'], 2.5, 0.3)
gains = dict(kick=0, clap=4, hats=-5, bass=-4, pad=-3, pluck=-6.5, lead=-1, fx=-12)
mix = sum(bus[k] * db(g) for k, g in gains.items())
# fundido final
fo = s(8 * BAR); mix[s((TOTAL - 8) * BAR):s(TOTAL * BAR)] *= np.linspace(1, 0, fo)[:, None] ** 1.3
mix = mix[:s(TOTAL * BAR + 2.5)]
os.makedirs(V3 + 'stems_conectate', exist_ok=True)
for k in bus: (bus[k][:len(mix)] * db(gains[k])).astype(np.float32).tofile(V3 + 'stems_conectate/%s.f32' % k)
mix.astype(np.float32).tofile(V3 + 'conectate_v3_raw.f32')
t = 0
for name, nb, prog, _ in ARR:
    print('%-11s %6.1fs  %2d compases  %s' % (name, t, nb, ' – '.join(prog))); t += nb * BAR
print('duración %.1fs  pico %.2f' % (len(mix) / SR, np.abs(mix).max()))

# ------------------------------------------------------------------ MIDI (para abrirlo en tu DAW)
def write_midi(path, tracks):
    tpq = 480
    def vlq(v):
        b = [v & 0x7F]; v >>= 7
        while v: b.insert(0, (v & 0x7F) | 0x80); v >>= 7
        return bytes(b)
    chunks = []
    tempo = struct.pack('>I', int(60e6 / BPM))[1:]
    chunks.append(b'MTrk' + struct.pack('>I', len(b'\x00\xff\x51\x03' + tempo + b'\x00\xff\x2f\x00')) + b'\x00\xff\x51\x03' + tempo + b'\x00\xff\x2f\x00')
    for ch, (name, notes) in enumerate(tracks.items()):
        ev = []
        for t0, d, m in notes:
            a = int(round(t0 / BEAT * tpq)); b = a + max(1, int(round(d / BEAT * tpq)))
            ev.append((a, 1, 0x90 | ch, m, 96)); ev.append((b, 0, 0x80 | ch, m, 0))
        ev.sort()
        data = b'\x00\xff\x03' + vlq(len(name.encode())) + name.encode(); last = 0
        for tk, _, st_, m, v in ev:
            data += vlq(tk - last) + bytes([st_, m, v]); last = tk
        data += b'\x00\xff\x2f\x00'
        chunks.append(b'MTrk' + struct.pack('>I', len(data)) + data)
    with open(path, 'wb') as fh:
        fh.write(b'MThd' + struct.pack('>IHHH', 6, 1, len(chunks), tpq) + b''.join(chunks))
write_midi(V3 + 'Nexsound_Conectate.mid', midi)
