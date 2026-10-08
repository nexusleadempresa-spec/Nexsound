# Máster: EQ que iguala el balance tonal del drop al del drop de PROMO (±6 dB, suavizado) + limitador.
import numpy as np, subprocess, sys
SR=44100; BAR=4*60/124
V3=sys.argv[1]
def ld(p): return np.fromfile(p,np.float32).reshape(-1,2).astype(np.float64)
mix=ld(V3+'conectate_v3_raw.f32'); p=ld(V3+'../audio/promo.f32'); d0=1.93721
a,b=int(77.4*SR),int((77.4+16*BAR)*SR); pd=p[int((d0+47*BAR)*SR):int((d0+63*BAR)*SR)]
def spec(x):
    N=8192; w=np.hanning(N); acc=np.zeros(N//2+1)
    for i in range(0,len(x)-N,N//2): acc+=np.abs(np.fft.rfft(x[i:i+N].mean(1)*w))**2
    return acc
f=np.fft.rfftfreq(8192,1/SR); A=spec(mix[a:b]); B=spec(pd)
cent=np.geomspace(25,18000,60); g=[]
for c in cent:
    m=(f>c/2**(1/6))&(f<c*2**(1/6)); g.append(10*np.log10((B[m].sum()+1e-12)/(A[m].sum()+1e-12)))
g=np.array(g); g-=np.median(g); g=np.clip(g,-6,6); g=np.convolve(np.pad(g,2,mode='edge'),np.ones(5)/5,'valid')
print('EQ (Hz:dB):',' '.join('%d:%+.1f'%(c,v) for c,v in zip(cent[::6],g[::6])))
Nf=1<<int(np.ceil(np.log2(len(mix)))); F=np.fft.rfftfreq(Nf,1/SR)
G=10**(np.interp(np.log(np.maximum(F,1)),np.log(cent),g)/20)
out=np.fft.irfft(np.fft.rfft(mix,Nf,axis=0)*G[:,None],Nf,axis=0)[:len(mix)]
out.astype(np.float32).tofile(V3+'conectate_v3_eq.f32')
