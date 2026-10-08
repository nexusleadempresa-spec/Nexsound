# Convertidor de URLs a temas (Mac)

1. Descarga `Convertir_URL_a_tema.command`.
2. La primera vez: clic derecho → Abrir (macOS pide confirmación porque no viene de la App Store).
   Si no se abre, en Terminal: `chmod +x ~/Downloads/Convertir_URL_a_tema.command`.
3. Pega las URLs (una por línea), deja una línea vacía y pulsa Intro.

Sale cada tema en **WAV 24 bits / 44,1 kHz** y **MP3 320 kbps** en `Música/Nexsound`, listo para
arrastrarlo a Nexsound Despiece. Acepta YouTube, SoundCloud, Bandcamp, Vimeo y enlaces directos a
MP3, WAV, FLV, MP4… La primera vez instala solo yt-dlp y ffmpeg (con Homebrew).

También se puede usar con una lista: `./Convertir_URL_a_tema.command lista.txt` (una URL por línea).

Úsalo con música propia o con permiso para descargarla.
