# Pack Nexsound: stems completos, loops y one-shots cortados en el golpe (muestra 0 = golpe / compás)
import numpy as np, os, subprocess, json
SR = 44100
ST = os.path.dirname(os.path.abspath(__file__)) + '/../stems/'
OUT = os.path.dirname(os.path.abspath(__file__)) + '/../Nexsound_Pack/'
STEMS = ('bateria', 'bajo', 'musica', 'voz')

TRACKS = {
    # nombre: (prefijo, bpm, primer downbeat en s, carpeta, secciones [(nombre, compás inicio, compás fin)])
    'PROMO': ('promo', 124.0, 0.4856 + 3 * 60 / 124.0, '124BPM_Do', [
        ('01_Intro', 0, 7), ('02_Intro_hats', 7, 15), ('03_Groove', 15, 31), ('04_Break_1', 31, 39),
        ('05_Subida_1', 39, 47), ('06_Drop_1', 47, 79), ('07_Break_2', 79, 95), ('08_Drop_2', 95, 127),
        ('09_Outro', 127, 143)]),
    'EL_REY': ('rey', 108.9625, 0.2092 + 3 * 60 / 108.9625, '109BPM_Re', [
        ('01_Intro', 0, 2), ('02_Tema', 2, 26), ('03_Bajo', 26, 41), ('04_Subida', 41, 64),
        ('05_Climax', 64, 91), ('06_Outro', 91, 106)]),
    'EL_REY_ajustado': ('rey124', 124.0, 0.2072 + 3 * 60 / 124.0, '124BPM_Do', [
        ('01_Intro', 0, 2), ('02_Tema', 2, 26), ('03_Bajo', 26, 41), ('04_Subida', 41, 64),
        ('05_Climax', 64, 91), ('06_Outro', 91, 106)]),
}

def load(p): return np.fromfile(ST + p + '.f32', np.float32).reshape(-1, 2).astype(np.float64)

def write_wav(path, x, bits=24):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.f32'; x.astype(np.float32).tofile(tmp)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', tmp,
                    '-c:a', 'pcm_s24le' if bits == 24 else 'pcm_s16le', path], check=True)
    os.remove(tmp)

def bar_start(name, bar):
    _, bpm, d0, *_ = TRACKS[name]; return d0 + bar * 4 * 60 / bpm

def align_to_bar(name, x):
    """Desplaza el audio para que la muestra 0 caiga justo en una línea de compás."""
    _, bpm, d0, *_ = TRACKS[name]; barlen = 4 * 60 / bpm
    first = d0 - np.floor(d0 / barlen) * barlen    # primer compás >= 0
    shift = first - barlen if first > 1e-4 else 0.0  # compás anterior (negativo => rellenar silencio)
    if shift < 0:
        pad = int(round(-shift * SR)); return np.vstack([np.zeros((pad, 2)), x]), -pad
    cut = int(round(first * SR)); return x[cut:], cut

def edge_fade(x, ms=2):
    m = int(SR * ms / 1000); x = x.copy()
    x[-m:] *= np.linspace(1, 0, m)[:, None]; return x

report = {}
for name, (pre, bpm, d0, tag, secs) in TRACKS.items():
    barlen = 4 * 60 / bpm
    data = {st: load(f'{pre}_{st}') for st in STEMS}
    data['instrumental'] = data['bateria'] + data['bajo'] + data['musica']
    # --- 1) stems completos, alineados a compás ---
    for st, x in data.items():
        y, off = align_to_bar(name, x)
        write_wav(f'{OUT}01_Stems/{name}_{tag}/{name}_{st}_{tag}.wav', y)
    report[name] = {'bpm': bpm, 'downbeat_s': round(d0, 5), 'compas_s': round(barlen, 6)}
    # --- 2) loops: cada sección (y un loop de 4 compases) cortados exactamente en el compás ---
    for sec, b0, b1 in secs:
        a = int(round(bar_start(name, b0) * SR)); b = int(round(bar_start(name, b1) * SR))
        l4 = int(round(bar_start(name, b0 + 4) * SR))
        for st in ('instrumental', 'bateria', 'bajo', 'musica'):
            x = data[st]
            if b1 - b0 >= 4:
                write_wav(f'{OUT}02_Loops_4compases/{name}_{tag}/{name}_{sec}_{st}_loop4.wav', edge_fade(x[a:l4]))
    print(name, 'listo')

with open(OUT + 'rejilla.json', 'w') as fh: json.dump(report, fh, indent=1)
