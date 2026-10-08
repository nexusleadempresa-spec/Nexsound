# Extrae bombo, clap y hats de PROMO por promediado coherente sobre la rejilla exacta (124 BPM).
# Cada muestra empieza en la posición de rejilla, así que conserva el microtiming original de PROMO.
import numpy as np
SR=44100; bpm=124.0; beat=60/bpm; st=beat/4; bar=4*beat; d0=1.93721
x=np.fromfile('../audio/promo.f32',np.float32).reshape(-1,2).astype(np.float64)
BARS=list(range(15,31))+list(range(47,79))+list(range(95,127))
def avg(slots, dur):
    n=int(dur*SR); acc=np.zeros((n,2)); k=0
    for b in BARS:
        for q in slots:
            a=int(round((d0+b*bar+q*st)*SR)); acc+=x[a:a+n]; k+=1
    return acc/k, k
def filt(y, lo=None, hi=None):
    out=np.zeros_like(y)
    for c in range(2):
        X=np.fft.rfft(y[:,c],n=len(y)*4); f=np.fft.rfftfreq(len(y)*4,1/SR); g=np.ones_like(f)
        if lo: g*=1/np.sqrt(1+(lo/np.maximum(f,1))**8)
        if hi: g*=1/np.sqrt(1+(f/hi)**8)
        out[:,c]=np.fft.irfft(X*g,n=len(y)*4)[:len(y)]
    return out
def fade(y, fo):
    m=int(fo*SR); y=y.copy(); y[-m:]*=np.linspace(1,0,m)[:,None]**2; return y
k13,n1=avg((0,8),0.25); k24,_=avg((4,12),0.25)
kick=fade(k13,0.03)
clap=fade(filt(k24-k13,lo=250),0.04)
hA,_=avg((2,6,10,14),0.121); hB,_=avg((3,7,11,15),0.121)
hatA=fade(filt(hA,lo=4500),0.02); hatB=fade(filt(hB,lo=4500),0.02)
# bajo a contratiempo de PROMO (para referencia del patrón): golpe grave en las corcheas débiles
for name,y in (('kick',kick),('clap',clap),('hatA',hatA),('hatB',hatB)):
    y.astype(np.float32).tofile(f'promo_{name}.f32')
    e=np.sqrt(np.convolve(y.mean(1)**2,np.ones(44)/44,'same'))
    print('%-5s golpes promediados %d  pico %.3f en %.1f ms  dur %d ms'%(name,n1 if name=='kick' else n1,np.abs(y).max(),1000*np.argmax(e)/SR,1000*len(y)/SR))
