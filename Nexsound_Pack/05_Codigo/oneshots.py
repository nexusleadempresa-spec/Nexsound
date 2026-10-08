# One-shots: para cada tipo de golpe se usa la banda que lo define (kick=graves, clap=medios, hat=agudos),
# se localiza el ataque exacto sobre la rejilla de semicorcheas y se eligen los golpes más limpios.
# Corte: muestra 0 = ataque (con 0,5 ms de entrada desde cero, sin clic), pico en los primeros ms.
import numpy as np, os, subprocess, shutil
SR = 44100
ST = os.path.dirname(os.path.abspath(__file__)) + '/../stems/'
OUT = os.path.dirname(os.path.abspath(__file__)) + '/../Nexsound_Pack/03_One_shots/'
TR = {'PROMO': ('promo', 124.0, 0.4856), 'EL_REY': ('rey', 108.9625, 0.2092)}
#        banda (Hz)    duración  posiciones permitidas (semicorchea dentro del compás)
CAT = {'kick':       ((30, 150),     0.45, (0, 4, 8, 12)),
       'clap_snare': ((900, 5000),   0.40, (4, 12)),
       'hat':        ((7000, 18000), 0.15, tuple(range(16))),
       'perc':       ((300, 2500),   0.25, (1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15))}
TOP = 5

def load(p): return np.fromfile(ST + p + '.f32', np.float32).reshape(-1, 2).astype(np.float64)
def wav(path, x):
    os.makedirs(os.path.dirname(path), exist_ok=True); t = path + '.f32'; x.astype(np.float32).tofile(t)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', t, '-c:a', 'pcm_s24le', path], check=True); os.remove(t)
def bandpass(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    g = 1 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 8) / np.sqrt(1 + (f / hi) ** 8)
    return np.fft.irfft(X * g, n=len(x))
def env(x, ms=1.0):
    k = max(1, int(SR * ms / 1000)); return np.sqrt(np.convolve(x ** 2, np.ones(k) / k, 'same'))

shutil.rmtree(OUT, ignore_errors=True)
for name, (pre, bpm, t0) in TR.items():
    bat = load(f'{pre}_bateria'); full = bat + load(f'{pre}_bajo')
    step = 60 / bpm / 4
    for cat, ((lo, hi), dur, slots) in CAT.items():
        src = full if cat == 'kick' else bat
        b = bandpass(src.mean(1), lo, hi); e = env(b, 1.0); eall = env(src.mean(1), 1.0)
        cands = []; n = 0
        while t0 + n * step < len(b) / SR - 1:
            if n % 16 in slots:
                c = int((t0 + n * step) * SR); w0 = c - int(0.012 * SR); seg = e[w0:c + int(0.012 * SR)]
                on = w0 + int(np.argmax(np.diff(seg)))
                pk = on + int(np.argmax(e[on:on + int(0.02 * SR)]))
                before = e[on - int(0.025 * SR):on - int(0.002 * SR)].mean() + 1e-9
                after_win = e[pk + int(0.6 * dur * SR):pk + int(dur * SR)].mean() + 1e-9   # cola: que no entre otro golpe
                ratio = e[pk] / before
                # pureza: que la banda domine el golpe completo
                purity = e[pk] / (eall[pk] + 1e-9)
                lim = 0.04 if cat == 'kick' else 0.025
                late = np.argmax(eall[on:on + int(dur * SR)]) > lim * SR      # el golpe más fuerte debe ser éste
                if pk - on < 0.012 * SR and ratio > 2 and not late:
                    cands.append((np.log(ratio) + 0.7 * np.log(e[pk] / after_win) + 2 * purity, on))
            n += 1
        cands.sort(reverse=True); chosen = []
        for sc, on in cands:
            if all(abs(on - o) > 3 * SR for o in chosen): chosen.append(on)
            if len(chosen) == TOP: break
        for i, on in enumerate(chosen, 1):
            a = on - int(0.0005 * SR)
            x = src[a:a + int(dur * SR)].copy()
            fi = int(0.0005 * SR); x[:fi] *= np.linspace(0, 1, fi)[:, None]
            fo = int(0.03 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
            x *= 10 ** (-0.3 / 20) / np.abs(x).max()
            wav(f'{OUT}{name}/{name}_{cat}_{i:02d}.wav', x)
        print(name, cat, 'candidatos', len(cands), 'exportados', len(chosen))
