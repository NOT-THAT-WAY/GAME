#!/usr/bin/env python3
"""Measure temporal defects in a rendered film and emit a reusable JSON report."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate", "-of", "json", args.video,
    ]))
    rate = probe["streams"][0]["r_frame_rate"].split("/")
    fps = float(rate[0]) / float(rate[1])
    frames = []
    previous = None
    with tempfile.TemporaryDirectory() as temp:
      subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", args.video,
                      "-vf", "scale=240:135", str(Path(temp) / "%05d.png")], check=True)
      paths = sorted(Path(temp).glob("*.png"))
      for index, path in enumerate(paths):
        rgb = Image.open(path).convert("RGB")
        gray = rgb.convert("L")
        pixels = list(gray.getdata())
        luma = float(sum(pixels) / len(pixels))
        black_ratio = sum(v < 12 for v in pixels) / len(pixels)
        clipped_ratio = sum(v > 250 for v in pixels) / len(pixels)
        saturation = float(ImageStat.Stat(rgb.convert("HSV").getchannel("S")).mean[0])
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_density = sum(v > 35 for v in edges.getdata()) / len(pixels)
        motion = 0.0
        motion_p95 = 0.0
        if previous is not None:
            diff_values = sorted(ImageChops.difference(gray, previous).getdata())
            motion = float(sum(diff_values) / len(diff_values))
            motion_p95 = float(diff_values[int(len(diff_values) * 0.95)])
        frames.append({
            "frame": index + 1,
            "time": round(index / fps, 5),
            "luma": round(luma, 4),
            "black_ratio": round(black_ratio, 6),
            "clipped_ratio": round(clipped_ratio, 6),
            "saturation": round(saturation, 4),
            "edge_density": round(edge_density, 6),
            "motion_mean": round(motion, 4),
            "motion_p95": round(motion_p95, 4),
        })
        previous = gray

    def percentile(values, fraction):
        ordered = sorted(values)
        return ordered[min(len(ordered) - 1, int(len(ordered) * fraction))]

    motion = [f["motion_mean"] for f in frames]
    luma = [f["luma"] for f in frames]
    black = [f["black_ratio"] for f in frames]
    clipped = [f["clipped_ratio"] for f in frames]
    cut_threshold = max(18.0, percentile(motion, 0.99))
    spikes = [f for f in frames if f["motion_mean"] >= cut_threshold]
    dark_runs = []
    start = None
    for i, value in enumerate(black):
        if value > 0.88 and start is None:
            start = i
        if start is not None and (value <= 0.88 or i == len(black) - 1):
            end = i if value <= 0.88 else i + 1
            if end - start >= max(2, round(fps * 0.08)):
                dark_runs.append({"start": round(start / fps, 3), "end": round(end / fps, 3)})
            start = None

    report = {
        "video": str(Path(args.video).resolve()),
        "fps": fps,
        "frame_count": len(frames),
        "duration": round(len(frames) / fps, 4),
        "summary": {
            "mean_luma": round(sum(luma) / len(luma), 4),
            "mean_black_ratio": round(sum(black) / len(black), 6),
            "mean_clipped_ratio": round(sum(clipped) / len(clipped), 6),
            "motion_mean": round(sum(motion) / len(motion), 4),
            "motion_p95": round(percentile(motion, 0.95), 4),
            "motion_p99": round(percentile(motion, 0.99), 4),
            "motion_spike_threshold": round(cut_threshold, 4),
            "motion_spikes": len(spikes),
            "dark_runs": dark_runs,
        },
        "largest_motion_spikes": sorted(spikes, key=lambda x: x["motion_mean"], reverse=True)[:20],
        "frames": frames,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
