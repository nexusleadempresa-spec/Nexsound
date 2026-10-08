# Separa un tema en stems que suman exactamente el original (mismas muestras, mismo inicio):
#   voz  = centro estéreo x armónico x banda vocal
#   bateria = percusivo (HPSS) del resto
#   bajo = armónico < ~140 Hz del resto
#   musica = armónico > ~140 Hz del resto (acordes, melodías, sintes)
import numpy as np, sys
from numpy.lib.stride_tricks import sliding_window_view as swv
SR = 44100; N = 4096; H = 512
src, prefix = sys.argv[1], sys.argv[2]
x = np.fromfile(src, dtype=np.float32).reshape(-1, 2)
n0 = len(x)
pad = np.zeros((N, 2), np.float32); x = np.vstack([pad, x, pad])
w = np.hanning(N).astype(np.float32)
fr = 1 + (len(x) - N) // H
def stft(c):
    return np.vstack([np.fft.rfft(c[np.arange(N)[None, :] + H * np.arange(i, min(fr, i + 1000))[:, None]] * w, axis=1).astype(np.complex64)
                      for i in range(0, fr, 1000)])
L = stft(x[:, 0]); R = stft(x[:, 1])
aL, aR = np.abs(L), np.abs(R); eps = 1e-9
psi = 2 * np.abs(L * np.conj(R)) / (aL ** 2 + aR ** 2 + eps)
delta = np.abs(aL - aR) / (aL + aR + eps)
center = np.clip((psi - 0.80) / 0.15, 0, 1) * np.clip(1 - delta / 0.3, 0, 1)
del psi, delta
M = (aL + aR) / 2
def medf(A, k, axis):
    p = k // 2
    Ap = np.pad(A, ((p, p), (0, 0)) if axis == 0 else ((0, 0), (p, p)), mode='edge')
    out = np.empty_like(A)
    for i in range(0, A.shape[0], 400):
        blk = Ap[i:i + 400 + 2 * p] if axis == 0 else Ap[i:i + 400]
        out[i:i + 400] = np.median(swv(blk, k, axis=axis), axis=-1)
    return out
Hm = medf(M, 23, 0); Pm = medf(M, 23, 1)
harm = Hm ** 2 / (Hm ** 2 + Pm ** 2 + eps); perc = 1 - harm
del Hm, Pm, M
f = np.fft.rfftfreq(N, 1 / SR)
band = np.clip((f - 170) / 110, 0, 1) * np.interp(f, [0, 7000, 12000, 22050], [1, 1, 0.5, 0.5])
V = center * harm * band[None, :]
V = (V + np.roll(V, 1, 0) + np.roll(V, -1, 0)) / 3 * 0.97
low = (1 / np.sqrt(1 + (f / 140.0) ** 8))[None, :]
rest = 1 - V
masks = {
    'voz': V,
    'bateria': rest * perc,
    'bajo': rest * harm * low,
    'musica': rest * harm * (1 - low),
}
def istft(X):
    y = np.zeros(len(x), np.float32); ws = np.zeros(len(x), np.float32)
    for i in range(0, fr, 1000):
        blk = np.fft.irfft(X[i:i + 1000], n=N, axis=1).astype(np.float32) * w
        for j in range(blk.shape[0]):
            s = (i + j) * H; y[s:s + N] += blk[j]; ws[s:s + N] += w ** 2
    return y / np.maximum(ws, 1e-3)
tot = np.zeros((n0, 2), np.float32)
for name, m in masks.items():
    m = m.astype(np.float32)
    y = np.stack([istft(L * m), istft(R * m)], 1)[N:N + n0]
    y.tofile(f'{prefix}_{name}.f32'); tot += y
    print(name, 'energía %.1f%%' % (100 * (y ** 2).sum() / (x[N:N + n0] ** 2).sum()))
print('error de reconstrucción %.2e' % np.abs(tot - x[N:N + n0]).max())
