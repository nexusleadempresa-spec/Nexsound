# Inserta el motor en la interfaz y genera: la página para Claude (despiece.html) y la versión local completa.
import pathlib
here = pathlib.Path(__file__).parent
ui = (here / 'ui.html').read_text(); eng = (here / 'engine.js').read_text()
assert '</script' not in eng
page = ui.replace('/*ENGINE*/', eng)
(here / 'despiece.html').write_text(page)
head_end = page.index('</style>') + len('</style>')
standalone = ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
              '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
              '<style>[hidden]{display:none!important}body{margin:0}img{max-width:100%}</style>'
              + page[:head_end] + '</head><body>' + page[head_end:] + '</body></html>')
(here / 'Nexsound_Despiece.html').write_text(standalone)
print('ok', len(page) // 1024, 'KB')
