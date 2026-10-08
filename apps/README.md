# Nexsound · herramientas web

Cada herramienta es un único HTML autónomo en `web/` (lista para subir a nexsound.es tal cual).

- `apps/src/*.html` — cada herramienta (interfaz y lógica propia)
- `apps/shared/core.js` — utilidades comunes (audio, loudness EBU R128, filtros, limitador, descargas, vídeo)
- `apps/shared/style.css` — estilo común
- `app/engine.js` — motor de análisis y separación (Despiece)
- `python3 apps/build.py` — genera `web/*.html` y `apps/dist/*.html`

Herramientas: Despiece, Master, Sample Lab, BPM y Tono, Afinador de voz, Ritmos, Comparador, Clips,
Visualizador, Reparto y Radar. Página de inicio: `web/index.html`.
