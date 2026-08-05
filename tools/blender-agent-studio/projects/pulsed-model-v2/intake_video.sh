#!/usr/bin/env bash
# Intake d'une vidéo de référence Pulse -> frames + planche contact.
# Usage: ./intake_video.sh <video> <slug>
set -euo pipefail

VIDEO="${1:?usage: intake_video.sh <video> <slug>}"
SLUG="${2:?usage: intake_video.sh <video> <slug>}"
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/frames/$SLUG"

mkdir -p "$OUT"

ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate,nb_frames,duration \
  -show_entries format=duration,size \
  -of json "$VIDEO" > "$OUT/probe.json"

# 4 img/s : assez dense pour capter chaque angle d'un tour d'objet.
ffmpeg -v error -y -i "$VIDEO" -vf "fps=4,scale=1280:-2" -q:v 2 "$OUT/f_%04d.jpg"

# Planche contact 6 colonnes pour lecture rapide des angles disponibles.
COUNT=$(ls "$OUT"/f_*.jpg | wc -l | tr -d ' ')
ffmpeg -v error -y -pattern_type glob -i "$OUT/f_*.jpg" \
  -vf "scale=320:-2,tile=6x$(( (COUNT + 5) / 6 ))" -q:v 3 "$OUT/contact.jpg" 2>/dev/null || \
  echo "contact sheet trop grande, sautée"

echo "$COUNT frames -> $OUT"
