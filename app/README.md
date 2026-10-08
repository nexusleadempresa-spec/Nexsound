# Nexsound Despiece

App web que desmonta un tema pieza a pieza, entera en el navegador (el audio no sale del equipo).

- **Abrir en local:** doble clic en `Nexsound_Despiece.html` (Chrome o Safari).
- **Código:** `engine.js` (análisis, separación, regeneración, WAV/MIDI/ZIP) + `ui.html` (interfaz).
  `python3 build.py` los junta en `despiece.html` (página para Claude) y `Nexsound_Despiece.html` (local).

Qué saca: stems (batería, bajo, música, voz, instrumental) alineados al compás; bombo, caja/clap y hat
aislados por promediado de todos sus golpes; bombo, caja, hat, batería, bajo, acordes y melodía
regenerados desde cero; MIDI de 4 pistas; tempo, tonalidad, patrón de 16 pasos y acordes por compás.
