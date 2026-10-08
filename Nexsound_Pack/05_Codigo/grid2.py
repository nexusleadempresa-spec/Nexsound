import numpy as np, sys
SR=44100
src,bpm0,ph0=sys.argv[1],float(sys.argv[2]),float(sys.argv[3])
x=np.fromfile(src,dtype=np.float32).reshape(-1,2).mean(1).astype(np.float64)
e=np.convolve(x**2,np.ones(88)/88,'same'); e=np.log(e+1e-8)
on=np.maximum(0,np.diff(e,prepend=e[0])); on=np.convolve(on,np.ones(44),'same')
best=None
for bpm in np.arange(bpm0-0.03,bpm0+0.03,0.0025):
    per=60/bpm; nmax=int((len(x)/SR-ph0-0.1)/per)
    base=np.arange(nmax)*per
    for off in np.arange(ph0-0.06,ph0+0.06,0.0002):
        idx=((base+off)*SR).astype(int); sc=on[idx].sum()
        if best is None or sc>best[0]: best=(sc,bpm,off)
# residuos por beat
sc,bpm,off=best; per=60/bpm
res=[]
for n in range(int((len(x)/SR-off-0.1)/per)):
    c=int((off+n*per)*SR); seg=on[c-441:c+441]; res.append((np.argmax(seg)-441)/SR*1000)
res=np.array(res)
print('bpm=%.4f  t0=%.5fs  mediana desvío %.2f ms  |desvío|<5ms en %.0f%% de beats'%(bpm,off,np.median(res),100*np.mean(np.abs(res)<5)))
