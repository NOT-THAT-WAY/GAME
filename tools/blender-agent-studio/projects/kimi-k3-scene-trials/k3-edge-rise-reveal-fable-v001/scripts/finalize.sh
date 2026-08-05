#!/bin/bash
# Mux the rendered frames with the project audio, extract the four key images,
# rebuild the contact sheet, and check for black frames.
set -e
cd "$(dirname "$0")/.."
SCRATCH="${1:-/tmp}"
MASTER=../../fl-studio-box-semantic-template/media/current/master.mp4

ffmpeg -hide_banner -loglevel error -y -ss 0 -t 12.0 -i "$MASTER" -vn -c:a aac -b:a 192k "$SCRATCH/edge_audio.m4a"
ffmpeg -hide_banner -loglevel error -y -framerate 30 -i renders/frames/f%04d.png -i "$SCRATCH/edge_audio.m4a" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -r 30 -c:a aac -b:a 192k -shortest renders/preview.mp4

cp renders/frames/f0020.png gates/key1-assis.png
cp renders/frames/f0085.png gates/key2-lever.png
cp renders/frames/f0175.png gates/key3-marche.png
cp renders/frames/f0345.png gates/key4-reveal.png
ffmpeg -hide_banner -loglevel error -y -pattern_type glob -i 'gates/key*.png' \
  -filter_complex "scale=480:270,tile=2x2:padding=4:color=black" -frames:v 1 -q:v 2 gates/contact-sheet.jpg

cp -p scene/trial.blend FL_Studio_Box_Edge_Rise_Reveal_Fable.blend
cp -p renders/preview.mp4 preview-edge-rise-reveal-fable.mp4

echo "--- probe"
ffprobe -v error -show_entries "format=duration:stream=codec_name,width,height,nb_frames" -of csv renders/preview.mp4
echo "--- blackdetect hits (0 expected)"
ffmpeg -hide_banner -i renders/preview.mp4 -vf "blackdetect=d=0.03:pix_th=0.10" -an -f null - 2>&1 | grep -c "black_start" || true
