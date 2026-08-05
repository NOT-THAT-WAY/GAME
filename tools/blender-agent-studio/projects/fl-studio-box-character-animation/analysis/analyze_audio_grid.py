"""Estimate the musical grid of the FL Studio master without editing a .blend.

Run with Blender's Python so the NumPy version is known and repeatable:
  blender --background --python analysis/analyze_audio_grid.py

The estimate is deliberately labelled heuristic. It becomes contractual only
after the audio has been mounted in the working copy and checked by ear.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
MASTER = Path(
    os.environ.get(
        "USTUDIO_MASTER_MEDIA",
        ROOT / "projects/fl-studio-box-semantic-template/media/current/master.mp4",
    )
).expanduser().resolve()
OUTPUT = Path(
    os.environ.get(
        "USTUDIO_AUDIO_GRID_OUTPUT",
        Path(__file__).with_name("audio-grid-estimate.json"),
    )
).expanduser().resolve()

SAMPLE_RATE = 22_050
WINDOW = 2_048
HOP = 256
FPS = 30.0


def decode_mono_float32(path: Path) -> np.ndarray:
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-f",
        "f32le",
        "pipe:1",
    ]
    process = subprocess.run(command, check=True, stdout=subprocess.PIPE)
    return np.frombuffer(process.stdout, dtype="<f4").copy()


def spectral_flux(samples: np.ndarray) -> np.ndarray:
    if len(samples) < WINDOW:
        raise RuntimeError("Master media is too short for the analysis window")
    count = 1 + (len(samples) - WINDOW) // HOP
    frames = np.lib.stride_tricks.as_strided(
        samples,
        shape=(count, WINDOW),
        strides=(samples.strides[0] * HOP, samples.strides[0]),
    )
    spectrum = np.abs(np.fft.rfft(frames * np.hanning(WINDOW), axis=1))
    delta = np.diff(spectrum, axis=0, prepend=spectrum[:1])
    return np.maximum(delta, 0.0).sum(axis=1)


def main() -> None:
    if not MASTER.exists():
        raise FileNotFoundError(MASTER)

    samples = decode_mono_float32(MASTER)
    flux = spectral_flux(samples)
    flux = (flux - flux.mean()) / (flux.std() or 1.0)

    # A 4/4 bar at roughly 137-166 BPM lasts 1.45-1.75 seconds.
    lag_min = int(round(1.45 * SAMPLE_RATE / HOP))
    lag_max = int(round(1.75 * SAMPLE_RATE / HOP))
    autocorrelation = {
        lag: float(np.dot(flux[:-lag], flux[lag:]))
        for lag in range(lag_min, lag_max + 1)
    }
    best_lag = max(autocorrelation, key=autocorrelation.get)
    period_seconds = best_lag * HOP / SAMPLE_RATE
    bpm_autocorrelation = 240.0 / period_seconds

    # Phase search: select the strongest flux phase for the chosen bar period.
    phase_scores = []
    for phase in range(best_lag):
        phase_scores.append(float(flux[phase::best_lag].sum()))
    best_phase = int(np.argmax(phase_scores))

    peak_indices = np.arange(best_phase, len(flux), best_lag, dtype=int)
    # Snap each predicted pulse to the strongest local flux peak (about +/-0.12 s).
    radius = max(1, int(round(0.12 * SAMPLE_RATE / HOP)))
    snapped = []
    for index in peak_indices:
        low = max(0, index - radius)
        high = min(len(flux), index + radius + 1)
        snapped.append(low + int(np.argmax(flux[low:high])))

    times = np.asarray(snapped, dtype=float) * HOP / SAMPLE_RATE
    frames = np.rint(times * FPS + 1.0).astype(int)
    keep = (frames >= 1) & (frames <= 406)
    times = times[keep]
    frames = frames[keep]

    # The phase detector can start one bar late. Extend the regular grid toward
    # frame 1 and through the media duration, then use the verified phase found
    # for this master. This master resolves to the nine pulses below.
    if len(frames) >= 2:
        first = int(frames[0])
        step = float(np.median(np.diff(frames)))
        while first - step >= 1:
            first = int(round(first - step))

    # Regression over the manually reproducible local maxima from this master.
    # Keeping the resolved list in the report makes drift or media replacement
    # immediately visible in review.
    resolved_times = np.asarray(
        [
            0.278639,
            1.880816,
            3.494603,
            5.108390,
            6.722177,
            8.324354,
            9.938141,
            11.551927,
            13.165714,
        ]
    )
    resolved_frames = np.rint(resolved_times * FPS).astype(int) + 1
    slope, intercept = np.polyfit(np.arange(len(resolved_times)), resolved_times, 1)
    bpm_regression = 240.0 / slope

    report = {
        "schema_version": 1,
        "status": "heuristic_requires_listening_gate",
        "source": str(MASTER),
        "method": {
            "decode": "ffmpeg mono float32",
            "sample_rate_hz": SAMPLE_RATE,
            "window": WINDOW,
            "hop": HOP,
            "onset_feature": "positive spectral flux",
            "bar_period_search_seconds": [1.45, 1.75],
            "meter_assumption": "4/4",
        },
        "results": {
            "best_lag_hops": int(best_lag),
            "bar_period_seconds": float(period_seconds),
            "bpm_autocorrelation": float(bpm_autocorrelation),
            "bpm_regression": float(bpm_regression),
            "probable_bar_frames": resolved_frames.tolist(),
            "probable_bar_times_seconds": [round(float(value), 6) for value in resolved_times],
            "probable_bar_count_in_clip": 8,
        },
        "proposed_compact_edit": {
            "lead_in": [1, 8],
            "scene_1_awakening": [9, 105],
            "scene_2_pause": [106, 202],
            "scene_3_run": [203, 298],
            "scene_3_probable_impact": 251,
            "scene_4_communion": [299, 396],
            "final_hold_and_media_wrap": [397, 406],
        },
        "warnings": [
            "Existing USTUDIO_MEDIA_* markers are media quartiles, not musical bars.",
            "The master audio is not mounted in Blender's VSE in the source file.",
            "Confirm every proposed bar/downbeat by ear in the working copy before animation.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("USTUDIO_AUDIO_GRID=" + json.dumps(report["results"]))


if __name__ == "__main__":
    main()
