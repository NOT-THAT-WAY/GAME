"""Drive one clip through the whole pole pipeline and record its verdict.

    author (MCP, live session)  ->  checkpoint
      -> key-pose contact sheet  -> physical measurement
      -> FBX export              -> independent Blender reimport
      -> playblast (+ x4 for loops)

The Unity gate is deliberately NOT here: it is run once for all candidates at
the end, because a Unity batch start costs far more than the import itself.
Until it has run, a clip's Unity gate stays PENDING and the clip cannot be
called PASS.

Usage:
    python3 run_clip.py <CLIP> [<CLIP> ...]
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import author_clip  # noqa: E402
import make_contract  # noqa: E402

PROJECT = SCRIPTS.parent
STUDIO = PROJECT.parent.parent.parent
LOCAL = STUDIO / "local_work" / "sandbox-character-motion-object-claude-v001"
EVIDENCE = PROJECT / "evidence"
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"

LOOPS = {"SB_Walk", "SB_Sprint", "SB_Airborne", "SB_CarryIdle", "SB_CarryWalk"}

# Reading poses per clip: the frames the brief names, which are the ones a human
# judges the clip on.
KEY_FRAMES = {
    "SB_Walk": [1, 8, 16, 23],
    "SB_Sprint": [1, 7, 13, 19],
    "SB_Airborne": [1, 7, 13, 19],
    "SB_JumpTakeoff": [1, 4, 8, 9, 12],
    "SB_Land": [1, 5, 8, 12],
    "SB_CarryIdle": [1, 15, 30, 45],
    "SB_CarryWalk": [1, 8, 16, 23],
    "SB_Pickup": [1, 8, 12, 20, 24],
    "SB_Throw": [1, 6, 11, 12, 17, 24],
    "SB_Drop": [1, 6, 9, 18],
    "SB_Deposit": [1, 10, 15, 22, 30],
}


def sh(args, label):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        tail = (result.stderr or result.stdout)[-2000:]
        raise SystemExit(f"ECHEC {label}:\n{tail}")
    return result.stdout


def latest_checkpoint(clip):
    found = sorted((LOCAL / "checkpoints").glob(f"{clip}_v*.blend"))
    if not found:
        raise SystemExit(f"aucun checkpoint pour {clip}")
    return found[-1]


def run(clip: str) -> dict:
    print(f"\n=== {clip} ===", flush=True)
    report = author_clip.author(clip)
    saved = author_clip.checkpoint(clip)
    checkpoint = pathlib.Path(saved["checkpoint"])
    print(f"  authored {report['range']} fcurves={report['fcurves']} -> {checkpoint.name}",
          flush=True)

    renders = LOCAL / "renders" / clip
    renders.mkdir(parents=True, exist_ok=True)
    sh([BLENDER, "-b", "--factory-startup", str(checkpoint),
        "--python", str(SCRIPTS / "render_poses.py"), "--",
        clip, str(renders)] + [str(f) for f in KEY_FRAMES[clip]], "render_poses")

    contract_path = EVIDENCE / f"{clip}-contract.json"
    contract_path.write_text(json.dumps(make_contract.CONTRACTS[clip](), indent=1))

    physical_path = EVIDENCE / f"{clip}-physical-validation.json"
    out = sh([BLENDER, "-b", "--factory-startup", str(checkpoint),
              "--python", str(SCRIPTS / "measure_clip.py"), "--",
              clip, str(contract_path), str(physical_path)], "measure_clip")
    physical_pass = "PHYSICAL_PASS True" in out
    print(f"  physical={physical_pass}", flush=True)

    continuity_path = EVIDENCE / f"{clip}-continuity.json"
    out = sh([BLENDER, "-b", "--factory-startup", str(checkpoint),
              "--python", str(SCRIPTS / "continuity_probe.py"), "--",
              clip, str(continuity_path)], "continuity_probe")
    continuity_pass = "CONTINUITY_PASS True" in out
    print(f"  continuity={continuity_pass}", flush=True)

    exports = LOCAL / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    fbx = exports / f"{clip}_candidate.fbx"
    sh([BLENDER, "-b", "--factory-startup", str(checkpoint),
        "--python", str(SCRIPTS / "export_clip.py"), "--", clip, str(fbx)],
       "export_clip")

    reimport_path = EVIDENCE / f"{clip}-reimport.json"
    out = sh([BLENDER, "-b", "--factory-startup",
              "--python", str(SCRIPTS / "reimport_clip.py"), "--",
              str(fbx), str(checkpoint), clip, str(reimport_path)], "reimport_clip")
    reimport_pass = "REIMPORT_PASS True" in out
    print(f"  reimport={reimport_pass}", flush=True)

    playblast_dir = LOCAL / "renders" / clip / "playblast"
    playblast_dir.mkdir(parents=True, exist_ok=True)
    sh([BLENDER, "-b", "--factory-startup", str(checkpoint),
        "--python", str(SCRIPTS / "playblast_clip.py"), "--", clip,
        str(playblast_dir)], "playblast_clip")

    media = LOCAL / "renders" / clip / f"{clip}-playblast.mp4"
    repeats = 4 if clip in LOOPS else 1
    frames = sorted(playblast_dir.glob(f"{clip}_*.png"))
    concat = playblast_dir / "concat.txt"
    concat.write_text("".join(
        f"file '{p.name}'\nduration 0.0333333\n" for _ in range(repeats) for p in frames
    ) + f"file '{frames[-1].name}'\n")
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "20",
        str(media)], "ffmpeg")

    probe = json.loads(sh(["ffprobe", "-v", "quiet", "-print_format", "json",
                           "-show_streams", "-show_format", str(media)], "ffprobe"))
    stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    media_probe = {
        "file": str(media.relative_to(STUDIO)),
        "width": stream["width"], "height": stream["height"],
        "nb_frames": int(stream.get("nb_frames", 0)),
        "avg_frame_rate": stream["avg_frame_rate"],
        "duration_s": float(probe["format"]["duration"]),
        "loop_repeats": repeats,
        "source_frames": len(frames),
    }
    (EVIDENCE / f"{clip}-playblast-probe.json").write_text(
        json.dumps(media_probe, indent=1))

    return {
        "clip": clip,
        "checkpoint": checkpoint.name,
        "fbx": str(fbx.relative_to(STUDIO)),
        "authored": report,
        "gate_contract": True,
        "gate_physical": physical_pass,
        "gate_continuity": continuity_pass,
        "gate_reimport": reimport_pass,
        "gate_unity": "PENDING",
        "media": media_probe,
    }


if __name__ == "__main__":
    results = []
    for name in sys.argv[1:]:
        results.append(run(name))
    summary = EVIDENCE / "run-summary.json"
    existing = json.loads(summary.read_text()) if summary.exists() else {}
    for entry in results:
        existing[entry["clip"]] = entry
    summary.write_text(json.dumps(existing, indent=1))
    print("\n" + json.dumps(
        {r["clip"]: {k: r[k] for k in
                     ("gate_physical", "gate_continuity", "gate_reimport",
                      "gate_unity")}
         for r in results}, indent=1))
