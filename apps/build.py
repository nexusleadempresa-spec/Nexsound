# Construye cada herramienta como un único HTML autónomo (web/) y su versión para Claude (apps/dist/).
import pathlib, re
H = pathlib.Path(__file__).parent; ROOT = H.parent
eng = (ROOT / 'app/engine.js').read_text(); core = (H / 'shared/core.js').read_text(); css = (H / 'shared/style.css').read_text()
for s in (eng, core): assert '</script' not in s
TOOLS = [  # slug, nombre, descripción corta
    ('despiece', 'Despiece', 'Stems, golpes aislados, sonidos regenerados y MIDI'),
    ('master', 'Master', 'Masteriza tu tema en un clic, con o sin referencia'),
    ('samplelab', 'Sample Lab', 'De cualquier tema a un kit de samples'),
    ('bpm', 'BPM y Tono', 'Tempo, tonalidad, Camelot y acordes de tus temas'),
    ('afinador', 'Afinador de voz', 'Corrige la afinación de una voz grabada'),
    ('ritmos', 'Ritmos', 'Patrones de batería por estilo, con MIDI y WAV'),
    ('comparador', 'Comparador', 'Tu mezcla frente a una referencia, con consejos'),
    ('clips', 'Clips', 'El mejor fragmento de tu tema, listo para redes'),
    ('visualizador', 'Visualizador', 'Vídeo con tu portada y el audio animado'),
    ('splits', 'Reparto', 'Porcentajes, royalties y hoja de reparto'),
    ('radar', 'Radar', 'A qué se parece tu tema y dónde encaja'),
]
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,500..800&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">')
def nav(slug):
    return ('<div class="top"><a class="brand" href="index.html"><b>Nexsound</b> · Herramientas</a>'
            '<a class="btn small" href="index.html">Todas las herramientas</a></div>')
def foot():
    links = ' '.join(f'<a href="{s}.html">{n}</a>' for s, n, _ in TOOLS)
    return f'<footer class="nx"><span>Nexsound · todo se procesa en tu navegador</span>{links}</footer>'
LIBS = (f'<script type="text/plain" id="engine-src">{eng}</script><script type="text/plain" id="core-src">{core}</script>'
        f'<script>{eng}</script><script>{core}</script>')
web = ROOT / 'web'; dist = H / 'dist'; web.mkdir(exist_ok=True); dist.mkdir(exist_ok=True)
for src in sorted((H / 'src').glob('*.html')):
    slug = src.stem; page = src.read_text()
    page = (page.replace('<!--HEAD-->', FONTS + f'<style>{css}</style>').replace('<!--NAV-->', nav(slug))
                .replace('<!--FOOT-->', foot()).replace('<!--LIBS-->', LIBS)
                .replace('<!--TOOLS-->', '\n'.join(f'<a class="tool-card" href="{s}.html"><b>{n}</b><span>{d}</span></a>' for s, n, d in TOOLS)))
    (dist / f'{slug}.html').write_text(page)
    head_end = page.index('</style>', page.index(css[-40:])) + len('</style>')
    standalone = ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
                  '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
                  '<style>[hidden]{display:none!important}body{margin:0}img{max-width:100%}</style>'
                  + page[:head_end] + '</head><body>' + page[head_end:] + '</body></html>')
    (web / f'{slug}.html').write_text(standalone)
    print(f'{slug:14s} {len(standalone)//1024} KB')

# Despiece (app propia) y convertidor para Mac
import shutil, subprocess
subprocess.run(['python3', str(ROOT / 'app/build.py')], check=True)
d = (ROOT / 'app/Nexsound_Despiece.html').read_text().replace('<div class="brand">Nexsound · Laboratorio</div>', '<a class="brand" href="index.html" style="text-decoration:none">Nexsound · Herramientas</a>')
(web / 'despiece.html').write_text(d)
shutil.copy(ROOT / 'convertidor/Convertir_URL_a_tema.command', web / 'Convertir_URL_a_tema.command')
print('despiece + convertidor copiados')
