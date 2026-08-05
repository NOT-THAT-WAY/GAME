"""Deterministic tutorial-video preparation for Blender Studio.

The module deliberately stops before semantic AI analysis: it creates stable evidence
(probe, frames, audio, transcript and an analysis brief) that an approved agent can
inspect without ever mutating the source media.
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slugify(value: str) -> str:
    value = value.casefold().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:64] or "tutorial"


def _run(command: list[str], timeout: int = 3600) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        detail = (result.stderr or result.stdout or "commande externe en échec").strip()
        raise RuntimeError(f"{Path(command[0]).name}: {detail[-3000:]}")
    return result


def probe_video(source: Path) -> dict[str, Any]:
    result = _run([
        "ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(source)
    ], timeout=120)
    return json.loads(result.stdout)


def _duration(probe: dict[str, Any]) -> float:
    try:
        return float(probe.get("format", {}).get("duration", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _has_stream(probe: dict[str, Any], kind: str) -> bool:
    return any(stream.get("codec_type") == kind for stream in probe.get("streams", []))


def _seconds(value: str) -> float:
    value = value.strip().replace(",", ".")
    parts = value.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalize_transcript(path: Path, duration: float) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower()
    segments: list[dict[str, Any]] = []
    if suffix in {".srt", ".vtt"}:
        pattern = re.compile(
            r"(?:(?:^|\n)\s*\d+\s*\n)?\s*(\d{1,2}:\d{2}(?::\d{2})?[,.]\d+)\s*-->\s*"
            r"(\d{1,2}:\d{2}(?::\d{2})?[,.]\d+)[^\n]*\n(.*?)(?=\n\s*\n|\Z)",
            re.S,
        )
        for start, end, body in pattern.findall(text):
            clean = re.sub(r"<[^>]+>", "", body).replace("\n", " ").strip()
            if clean:
                segments.append({"start": _seconds(start), "end": _seconds(end), "text": clean})
    if not segments and text.strip():
        clean = re.sub(r"\s+", " ", text).strip()
        segments = [{"start": 0.0, "end": duration, "text": clean}]
    language = "unknown"
    sidecar = path.with_suffix(".json")
    if sidecar.exists() and sidecar != path:
        try:
            whisper_data = json.loads(sidecar.read_text(encoding="utf-8"))
            language = whisper_data.get("result", {}).get("language") or whisper_data.get("language") or language
        except Exception:
            pass
    return {
        "source": path.name,
        "format": suffix.lstrip("."),
        "language": language,
        "segments": segments,
        "text": " ".join(segment["text"] for segment in segments),
    }


def _relative(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def _write_brief(folder: Path, root: Path, manifest: dict[str, Any], transcript: dict[str, Any] | None) -> None:
    evidence = manifest["evidence"]
    text = f"""# Brief d’analyse — {manifest['title']}

## Principe

Séparer strictement ce qui est observé de ce qui est inféré. Chaque conclusion doit citer
un timecode, une frame ou un passage du transcript. Ne jamais transformer une préférence
du formateur en règle universelle sans le signaler.

## Sources préparées

- Vidéo originale: `{evidence['source']}`
- Probe technique: `{evidence['probe']}`
- Frames régulières: `{evidence['frames_dir']}`
- Changements de plan: `{evidence['scenes_dir']}`
- Contact sheet: `{evidence.get('contact_sheet') or 'absent'}`
- Audio: `{evidence.get('audio') or 'absent'}`
- Transcript normalisé: `{evidence.get('transcript') or 'à produire'}`

## Analyse attendue

1. Résumer l’objectif final et le niveau requis.
2. Découper le tutoriel en chapitres avec `start`, `end`, objectif et preuve.
3. Extraire les opérations Blender exactes: espace de travail, outil/opérateur, réglages,
   raccourcis, ordre, préconditions et résultat observable.
4. Identifier les techniques caméra: rig, contrainte, focale, distance, composition,
   timing, F-Curves, easing et risques de dérive.
5. Identifier géométrie, modifiers, Geometry Nodes, shading, textures, lumière, couleur,
   compositing, rendu et export.
6. Distinguer assets réutilisables, dépendances externes et éléments spécifiques au projet.
7. Produire une recette reproductible avec paramètres, gate visuel et rollback.
8. Noter les ambiguïtés, versions Blender, addons et affirmations à vérifier.

## Contrat de sortie `analysis.json`

```json
{{
  "schema_version": 1,
  "model": "agent utilisé",
  "summary": "résumé",
  "confidence": 0.0,
  "chapters": [{{"start": 0, "end": 0, "title": "", "evidence": []}}],
  "techniques": [{{"domain": "camera", "name": "", "steps": [], "evidence": []}}],
  "reusable_assets": [],
  "workflow_recipe": {{"inputs": [], "steps": [], "gates": [], "outputs": []}},
  "risks": [],
  "open_questions": []
}}
```

Transcript disponible: **{'oui' if transcript else 'non'}**.
"""
    (folder / "ANALYSIS_BRIEF.md").write_text(text, encoding="utf-8")


def prepare_tutorial(root: Path, folder: Path, *, frame_interval: float, scene_threshold: float) -> dict[str, Any]:
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = folder / manifest["source_name"]
    manifest.update({"status": "processing", "updated": iso_now()})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    probe = probe_video(source)
    duration = _duration(probe)
    effective_interval = max(float(frame_interval), duration / 480 if duration else float(frame_interval))
    probe_path = folder / "probe.json"
    probe_path.write_text(json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8")

    frames = folder / "frames" / "regular"
    scenes = folder / "frames" / "scenes"
    frames.mkdir(parents=True, exist_ok=True)
    scenes.mkdir(parents=True, exist_ok=True)
    scale = "scale=min(1280\\,iw):-2"
    _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-vf", f"fps=1/{effective_interval:.6f},{scale}", "-strict", "unofficial", "-q:v", "3", "-frames:v", "480",
        str(frames / "frame_%05d.jpg"),
    ])
    _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-vf", f"select=gt(scene\\,{scene_threshold:.4f}),{scale}", "-fps_mode", "vfr", "-strict", "unofficial",
        "-q:v", "3", "-frames:v", "300", str(scenes / "scene_%05d.jpg"),
    ])

    contact = folder / "contact-sheet.jpg"
    contact_rate = 16.0 / max(duration, 1.0)
    _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-vf", f"fps={contact_rate:.8f},scale=320:-2,tile=4x4", "-frames:v", "1", "-strict", "unofficial", "-q:v", "3", str(contact),
    ])

    audio_path: Path | None = None
    if _has_stream(probe, "audio"):
        audio_path = folder / "audio.wav"
        _run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source), "-vn", "-ac", "1",
            "-ar", "16000", "-c:a", "pcm_s16le", str(audio_path),
        ])

    transcript_source = next((p for p in folder.glob("transcript-source.*") if p.is_file()), None)
    transcript: dict[str, Any] | None = None
    transcript_json: Path | None = None
    if transcript_source:
        transcript = normalize_transcript(transcript_source, duration)
        transcript_json = folder / "transcript.json"
        transcript_json.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")

    regular = sorted(frames.glob("*.jpg"))
    detected = sorted(scenes.glob("*.jpg"))
    manifest.update({
        "status": "ready_for_ai" if transcript else "needs_transcript",
        "updated": iso_now(),
        "technical": {
            "duration": duration,
            "frame_interval_requested": float(frame_interval),
            "frame_interval_effective": effective_interval,
            "scene_threshold": float(scene_threshold),
            "regular_frame_count": len(regular),
            "scene_frame_count": len(detected),
            "has_video": _has_stream(probe, "video"),
            "has_audio": _has_stream(probe, "audio"),
        },
        "evidence": {
            "source": _relative(source, root),
            "probe": _relative(probe_path, root),
            "frames_dir": _relative(frames, root),
            "scenes_dir": _relative(scenes, root),
            "contact_sheet": _relative(contact, root),
            "audio": _relative(audio_path, root) if audio_path else None,
            "transcript": _relative(transcript_json, root) if transcript_json else None,
        },
    })
    _write_brief(folder, root, manifest, transcript)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def attach_transcript(root: Path, folder: Path, transcript_source: Path) -> dict[str, Any]:
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    duration = float(manifest.get("technical", {}).get("duration", 0) or 0)
    transcript = normalize_transcript(transcript_source, duration)
    transcript_json = folder / "transcript.json"
    transcript_json.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest.setdefault("evidence", {})["transcript"] = _relative(transcript_json, root)
    manifest.update({"status": "ready_for_ai", "updated": iso_now()})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_brief(folder, root, manifest, transcript)
    return manifest


def scan_tutorials(root: Path) -> list[dict[str, Any]]:
    base = root / "knowledge" / "tutorials"
    items: list[dict[str, Any]] = []
    if not base.exists():
        return items
    for folder in sorted(base.iterdir()):
        if not folder.is_dir():
            continue
        manifest_path = folder / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            item = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        item["path"] = _relative(folder, root)
        source = folder / item.get("source_name", "")
        if source.is_file():
            item["source"] = {"name": source.name, "path": _relative(source, root), "url": "/media/" + _relative(source, root), "kind": "video"}
        contact = folder / "contact-sheet.jpg"
        if contact.exists():
            item["contact_sheet"] = "/media/" + _relative(contact, root)
        frames = sorted((folder / "frames" / "regular").glob("*.jpg")) if (folder / "frames" / "regular").exists() else []
        item["frames"] = [{"name": p.name, "url": "/media/" + _relative(p, root), "kind": "image"} for p in frames[:48]]
        transcript = folder / "transcript.json"
        if transcript.exists():
            data = json.loads(transcript.read_text(encoding="utf-8"))
            item["transcript_excerpt"] = data.get("text", "")[:1600]
        analysis = folder / "analysis.json"
        if analysis.exists():
            item["analysis"] = json.loads(analysis.read_text(encoding="utf-8"))
        items.append(item)
    return sorted(items, key=lambda item: item.get("updated", item.get("created", "")), reverse=True)
