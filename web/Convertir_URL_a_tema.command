#!/bin/bash
# Nexsound · Convertidor de URLs a temas
# Doble clic en el Mac. Pega una o varias URLs (YouTube, SoundCloud, Bandcamp, Vimeo, enlaces directos a
# MP3/WAV/FLV/MP4…) y las guarda como tema en WAV 24 bits / 44,1 kHz y MP3 320 kbps en Música/Nexsound.
# Úsalo con música tuya o que tengas derecho a descargar.

set -u
DEST="${NEXSOUND_DEST:-$HOME/Music/Nexsound}"
mkdir -p "$DEST"
cd "$DEST" || exit 1

linea() { printf '%s\n' "────────────────────────────────────────────"; }
linea; echo " NEXSOUND · Convertidor de URLs a temas"; echo " Destino: $DEST"; linea

# ---------- herramientas: yt-dlp (descarga) y ffmpeg (conversión)
need_brew() {
  if ! command -v brew >/dev/null 2>&1; then
    echo "Hace falta Homebrew para instalar las herramientas. Instalándolo (te pedirá tu contraseña del Mac)…"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || return 1
    [ -x /opt/homebrew/bin/brew ] && eval "$(/opt/homebrew/bin/brew shellenv)"
    [ -x /usr/local/bin/brew ] && eval "$(/usr/local/bin/brew shellenv)"
  fi
}
for tool in yt-dlp ffmpeg; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    need_brew || { echo "No se pudo instalar Homebrew. Instala $tool a mano y vuelve a abrir el convertidor."; read -r -p "Pulsa Intro para salir"; exit 1; }
    echo "Instalando $tool…"; brew install "$tool" || { echo "No se pudo instalar $tool."; read -r -p "Pulsa Intro para salir"; exit 1; }
  fi
done
# yt-dlp se actualiza a menudo cuando cambian las webs; si falla una descarga, el script lo actualiza y reintenta
actualizar_ytdlp() { brew upgrade yt-dlp >/dev/null 2>&1 || yt-dlp -U >/dev/null 2>&1 || true; }

# ---------- conversión de un archivo ya descargado a WAV 24 bits + MP3 320
convertir() {
  local src="$1" base
  base="${src%.*}"
  ffmpeg -hide_banner -loglevel error -y -i "$src" -vn -ac 2 -ar 44100 -c:a pcm_s24le "$base.wav" &&
  ffmpeg -hide_banner -loglevel error -y -i "$base.wav" -c:a libmp3lame -b:a 320k "$base.mp3" &&
  { [ "$src" != "$base.wav" ] && [ "$src" != "$base.mp3" ] && rm -f "$src"; true; }
}

descargar() {
  local url="$1" intento log; log="$(mktemp)"
  echo; echo "▶ $url"
  for intento in 1 2; do
    # el mejor audio disponible; los nombres llevan título y se limpian de caracteres raros
    if yt-dlp --no-playlist --restrict-filenames -f "bestaudio/best" \
         -o "%(title).80s.%(ext)s" --print after_move:filepath --no-simulate --quiet --progress "$url" > "$log"; then
      local f; f="$(tail -n 1 "$log")"; rm -f "$log"
      if [ -f "$f" ] && convertir "$f"; then echo "  ✔ Guardado: ${f%.*}.wav y .mp3"; return 0; fi
    fi
    rm -f "$log"
    [ "$intento" = 1 ] && { echo "  Reintentando con yt-dlp actualizado…"; actualizar_ytdlp; }
  done
  # último recurso: enlace directo a un archivo de audio o vídeo (FLV, MP4, MP3, WAV…)
  local tmp="descarga_$(date +%s)"
  if curl -fsSL --retry 2 -o "$tmp" "$url" && ffprobe -v error "$tmp" >/dev/null 2>&1; then
    local nombre; nombre="$(basename "${url%%\?*}")"; nombre="${nombre%.*}"; [ -z "$nombre" ] && nombre="$tmp"
    mv "$tmp" "$nombre.src" && convertir "$nombre.src" && { echo "  ✔ Guardado: $nombre.wav y .mp3"; return 0; }
  fi
  rm -f "$tmp"; echo "  ✘ No se pudo convertir esta URL (¿es privada, necesita sesión o no existe?)."; return 1
}

# ---------- URLs: como argumentos, desde un .txt (una por línea) o pegadas aquí
URLS=()
if [ "$#" -gt 0 ]; then
  for a in "$@"; do if [ -f "$a" ]; then while IFS= read -r l; do [ -n "$l" ] && URLS+=("$l"); done < "$a"; else URLS+=("$a"); fi; done
else
  echo "Pega las URLs (una por línea). Deja una línea vacía y pulsa Intro para empezar:"
  while IFS= read -r l; do [ -z "$l" ] && break; URLS+=("$l"); done
fi
[ "${#URLS[@]}" -eq 0 ] && { echo "No hay URLs."; exit 0; }

ok=0; ko=0
for u in "${URLS[@]}"; do u="$(echo "$u" | xargs)"; [ -z "$u" ] && continue; if descargar "$u"; then ok=$((ok+1)); else ko=$((ko+1)); fi; done
linea; echo " Listo: $ok convertidas, $ko con error. Carpeta: $DEST"; linea
open "$DEST" 2>/dev/null || true
[ "$#" -eq 0 ] && read -r -p "Pulsa Intro para cerrar"
