# "Conéctate" v2: sólo sonidos originales de PROMO y EL REY (stems), sobre la rejilla exacta a 124 BPM en Do.
# En cada parte se elige UN origen por elemento (batería / bajo / música) — sin capas armónicas que choquen.
import numpy as np, os
SR = 44100; BAR = 4 * 60 / 124.0
ST = os.path.dirname(os.path.abspath(__file__)) + '/../stems/'
OUT = os.path.dirname(os.path.abspath(__file__)) + '/../out/'
def load(p): return np.fromfile(ST + p + '.f32', np.float32).reshape(-1, 2).astype(np.float64)
SRC = {
    'P': ({k: load('promo_' + k) for k in ('bateria', 'bajo', 'musica')}, 0.4856 + 3 * 60 / 124.0),
    'R': ({k: load('rey124_' + k) for k in ('bateria', 'bajo', 'musica')}, 0.2072 + 3 * 60 / 124.0),
}
TAIL = 60 / 124.0   # 1 tiempo de cola para que nada se corte en seco

def take(src, stem, bar0, nbars, tail=True):
    st, d0 = SRC[src]; a = int(round((d0 + bar0 * BAR) * SR)); n = int(round(nbars * BAR * SR))
    t = int(TAIL * SR)
    x = st[stem][a:a + n + t].copy()
    if len(x) < n + t: x = np.vstack([x, np.zeros((n + t - len(x), 2))])
    x[n:] *= (np.linspace(1, 0, t)[:, None] ** 2) if tail else 0.0
    return x

def rms(x): return np.sqrt((x ** 2).mean() + 1e-12)
REF = rms(sum(take('P', s, 15, 16, False) for s in ('bateria', 'bajo', 'musica')))   # nivel del groove de PROMO

# (nombre, compases, [(origen, stem, compás de inicio, ganancia dB)], nivel objetivo respecto al groove en dB, fundido de entrada s)
ARR = [
    ('Intro',      8,  [('R', 'musica', 2, 0), ('R', 'bajo', 2, 0), ('P', 'bateria', 7, -4)],               -5, 2.0),
    ('Subida',     8,  [('R', 'musica', 41, 0), ('R', 'bajo', 41, 0), ('P', 'bateria', 39, -2)],            -3, 0),
    ('Groove',     16, [('P', 'musica', 15, 0), ('P', 'bajo', 15, 0), ('P', 'bateria', 15, 0)],              0, 0),
    ('Break',      8,  [('R', 'musica', 64, 0), ('R', 'bajo', 64, 0), ('P', 'bateria', 31, -2)],            -3, 0),
    ('Subida 2',   8,  [('P', 'musica', 39, 0), ('P', 'bajo', 39, 0), ('P', 'bateria', 39, 0)],              None, 0),
    ('Drop',       16, [('P', 'musica', 47, 0), ('P', 'bajo', 47, 0), ('P', 'bateria', 47, 0)],              None, 0),
    ('Break 2',    8,  [('R', 'musica', 72, 0), ('R', 'bajo', 72, 0), ('P', 'bateria', 79, -2)],            -3, 0),
    ('Pre-drop',   8,  [('P', 'musica', 87, 0), ('P', 'bajo', 87, 0), ('P', 'bateria', 87, 0)],              None, 0),
    ('Drop final', 16, [('P', 'musica', 95, 0), ('P', 'bajo', 95, 0), ('P', 'bateria', 95, 0)],              None, 0),
    ('Outro',      8,  [('P', 'musica', 127, 0), ('P', 'bajo', 127, 0), ('P', 'bateria', 127, 0)],           None, 0),
]

total = int(round(sum(a[1] for a in ARR) * BAR * SR)) + int(TAIL * SR)
mix = np.zeros((total, 2)); pos = 0.0
for i, (name, nb, parts, target, fin) in enumerate(ARR):
    layers = []
    nxt = ARR[i + 1][2] if i + 1 < len(ARR) else []
    for src, stem, b0, g in parts:
        contiguo = any(s2 == src and st2 == stem and b2 == b0 + nb for s2, st2, b2, _ in nxt)
        layers.append(take(src, stem, b0, nb, tail=not contiguo) * 10 ** (g / 20))
    x = sum(layers)
    if target is not None:                       # igualar volumen de las partes de EL REY al de PROMO
        x *= REF * 10 ** (target / 20) / rms(x[:int(nb * BAR * SR)])
    if fin: m = int(fin * SR); x[:m] *= np.linspace(0, 1, m)[:, None] ** 2
    a = int(round(pos * SR)); mix[a:a + len(x)] += x[:total - a]
    print('%-11s %6.2fs  %2d compases  %s' % (name, pos, nb, ' + '.join('%s:%s' % (s, st) for s, st, *_ in parts)))
    pos += nb * BAR
fo = int(8 * BAR * SR); mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5   # outro en fundido
os.makedirs(OUT, exist_ok=True)
mix.astype(np.float32).tofile(OUT + 'conectate_v2_raw.f32')
print('duración %.1fs  pico %.2f' % (len(mix) / SR, np.abs(mix).max()))
