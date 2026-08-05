"""Assemble the validated Blender/tutoriel resources into one Pulsed product master reel."""
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[2]
output = Path(sys.argv[1]).resolve()
output.mkdir(parents=True, exist_ok=False)
segments = output / "segments"
overlays = output / "overlays"
segments.mkdir()
overlays.mkdir()

capabilities_clean = root / "renders/capabilities-video-2026-07-19_151134/UNRECORDED-Blender-Agent-Demo-Clean.mp4"
if not capabilities_clean.exists():
    subprocess.run([
        "ffmpeg", "-y", "-framerate", "24", "-i",
        str(root / "renders/capabilities-video-2026-07-19_151134/frames/frame_%04d.png"),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(capabilities_clean),
    ], check=True)

sources = {
    "capabilities": capabilities_clean,
    "flroom": root / "library/blender-choreography/runs/flroom-scene-2026-07-14/hover_10s_v2.mp4",
    "seedance": root / "library/reel-blender/test-001-mouvement-camera/runs/2026-07-13_9x16_v4_job-c4157c99/output.mp4",
    "semantic": root / "projects/fl-studio-box-semantic-template/semantic-floating-preview-v6-drumboii-color-with-audio.mp4",
    "tutorial": root / "projects/tutorial-synthesis-lab-2026-07-19/final-preview.mp4",
}
for name, path in sources.items():
    if not path.exists():
        raise FileNotFoundError(f"Source manquante {name}: {path}")


def run(args):
    subprocess.run(args, check=True)


def normalize(name, source, start, duration, filter_graph):
    target = segments / f"{name}.mp4"
    run([
        "ffmpeg", "-y", "-ss", str(start), "-t", str(duration), "-i", str(source),
        "-vf", filter_graph, "-an", "-r", "24", "-c:v", "libx264", "-preset", "fast",
        "-crf", "18", "-pix_fmt", "yuv420p", str(target),
    ])
    return target


standard = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
vertical = (
    "split[bg][fg];"
    "[bg]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,boxblur=22:10[blur];"
    "[fg]scale=-2:720[front];[blur][front]overlay=(W-w)/2:0,setsar=1"
)
clips = [
    normalize("01-identity", sources["capabilities"], 0, 4, standard),
    normalize("02-camera-mass", sources["flroom"], 1, 6, standard),
    normalize("03-material-style", sources["seedance"], 0, 6, vertical),
    normalize("04-plugin-situation", sources["semantic"], 2, 6, standard),
    normalize("05-systems", sources["tutorial"], 3, 6, standard),
    normalize("06-final-gate", sources["capabilities"], 4, 2, standard),
]

clean = output / "pulsed-master-clean.mp4"
xfade = (
    "[0:v][1:v]xfade=transition=smoothleft:duration=0.5:offset=3.5[x1];"
    "[x1][2:v]xfade=transition=fade:duration=0.5:offset=9.0[x2];"
    "[x2][3:v]xfade=transition=slideup:duration=0.5:offset=14.5[x3];"
    "[x3][4:v]xfade=transition=fadeblack:duration=0.5:offset=20.0[x4];"
    "[x4][5:v]xfade=transition=smoothright:duration=0.5:offset=25.5[v]"
)
cmd = ["ffmpeg", "-y"]
for clip in clips:
    cmd.extend(["-i", str(clip)])
cmd.extend(["-filter_complex", xfade, "-map", "[v]", "-an", "-r", "24", "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p", str(clean)])
run(cmd)

font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
top_font = ImageFont.truetype(font_path, 31)
phase_font = ImageFont.truetype(font_path, 43)
sub_font = ImageFont.truetype(font_path, 22)
acts = [
    ("01  FORM / IDENTITY", "canonical model  •  spatial grounding"),
    ("02  CAMERA / MASS / FOCUS", "anticipation  •  travel  •  recovery"),
    ("03  MATERIAL / STYLE TRANSFER", "transparent shell  •  controlled reflections"),
    ("04  PLUGIN IN SITUATION", "Pulsed controlling a living FL Studio scene"),
    ("05  MECHANICS / ENVIRONMENT / SYSTEMS", "assembly  •  conveyor  •  world building"),
    ("06  GATED FINAL", "inspect  •  render  •  correct  •  human approval"),
]
for index, (title, subtitle) in enumerate(acts, 1):
    image = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    top = "UNRECORDED  /  PULSED  /  END-TO-END PRODUCT FILM"
    top_box = draw.textbbox((0, 0), top, font=top_font)
    draw.rounded_rectangle((31, 25, top_box[2] + 61, 79), 10, fill=(0, 0, 0, 158))
    draw.text((45, 35), top, font=top_font, fill=(255, 255, 255, 255))
    title_box = draw.textbbox((0, 0), title, font=phase_font)
    width = title_box[2]
    x = (1280 - width) // 2
    draw.rounded_rectangle((x - 25, 592, x + width + 25, 679), 12, fill=(0, 0, 0, 175))
    draw.text((x, 602), title, font=phase_font, fill=(255, 255, 255, 255))
    sub_box = draw.textbbox((0, 0), subtitle, font=sub_font)
    draw.text(((1280 - sub_box[2]) // 2, 652), subtitle, font=sub_font, fill=(195, 231, 238, 255))
    image.save(overlays / f"act-{index}.png")

final = output / "PULSED-End-to-End-Master-Film.mp4"
cmd = ["ffmpeg", "-y", "-i", str(clean)]
for index in range(1, 7):
    cmd.extend(["-loop", "1", "-i", str(overlays / f"act-{index}.png")])
cmd.extend(["-stream_loop", "-1", "-i", str(sources["semantic"])])
overlay_filter = (
    "[0:v][1:v]overlay=enable='between(t,0,4)'[v1];"
    "[v1][2:v]overlay=enable='between(t,3.5,9.5)'[v2];"
    "[v2][3:v]overlay=enable='between(t,9,15)'[v3];"
    "[v3][4:v]overlay=enable='between(t,14.5,20.5)'[v4];"
    "[v4][5:v]overlay=enable='between(t,20,26)'[v5];"
    "[v5][6:v]overlay=enable='between(t,25.5,27.5)'[v];"
    "[7:a]atrim=0:27.5,asetpts=PTS-STARTPTS,volume=0.72,afade=t=in:st=0:d=0.6,afade=t=out:st=26.2:d=1.3[a]"
)
cmd.extend([
    "-filter_complex", overlay_filter, "-map", "[v]", "-map", "[a]", "-t", "27.5", "-r", "24",
    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final),
])
run(cmd)

manifest = {
    "schema_version": 1,
    "output": str(final),
    "duration": 27.5,
    "fps": 24,
    "resolution": [1280, 720],
    "sources": {name: str(path.relative_to(root)) for name, path in sources.items()},
    "tutorial_knowledge": [
        "beginner lookdev, UV, lighting and DOF",
        "Drumboii four-key camera language, target lag and focus",
        "Ray-Ban reverse-built assembly reveal",
        "Factory linear mechanical loop and separation of transport/impact curves",
        "Quick Animation environment-first blocking",
        "Wireless Pods hierarchy, causal choreography and local/global controls",
    ],
    "acts": [{"title": title, "subtitle": subtitle} for title, subtitle in acts],
    "safety": {"source_blends_saved": False, "uses_validated_existing_renders": True},
}
(output / "master-film-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(final)
