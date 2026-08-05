"""Blender Studio: local catalogue and controlled Blender workflow runner."""
from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .tutorial_pipeline import attach_transcript, iso_now, prepare_tutorial, scan_tutorials, slugify

APP_DIR = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("BLENDER_ROOT", "/workspace")).resolve()
HOST_ROOT = Path(os.environ.get("BLENDER_ROOT_HOST", str(ROOT))).expanduser().resolve()
MCP_HOST = os.environ.get("BLENDER_MCP_HOST", "host.docker.internal")
MCP_PORT = int(os.environ.get("BLENDER_MCP_PORT", "9876"))
CACHE_TTL = float(os.environ.get("CATALOG_CACHE_TTL", "5"))
STUDIO_USER = os.environ.get("STUDIO_USER", "local-user").strip()[:120] or "local-user"
DEFAULT_BLEND_RELATIVE = os.environ.get("DEFAULT_BLEND_RELATIVE", "").strip()
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024 * 1024)))

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".exr", ".tif", ".tiff"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".m4v"}
AUDIO_EXT = {".wav", ".mp3", ".aiff", ".aif", ".flac", ".m4a", ".ogg"}
MEDIA_EXT = IMAGE_EXT | VIDEO_EXT | AUDIO_EXT
SKIP = {".git", ".DS_Store", "__pycache__", ".pytest_cache", "dist", "node_modules"}

app = FastAPI(title="Blender Team Studio", version="3.0.0")
_cache: dict[str, tuple[float, Any]] = {}
_jobs: dict[str, dict] = {}
_job_lock = threading.Lock()
_blender_job_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def safe_path(rel: str, *, must_exist: bool = True) -> Path:
    rel = rel.lstrip("/")
    path = (ROOT / rel).resolve()
    if path != ROOT and not str(path).startswith(str(ROOT) + os.sep):
        raise HTTPException(403, "Chemin hors du projet Blender")
    if must_exist and not path.exists():
        raise HTTPException(404, f"Introuvable: {rel}")
    return path


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def host_path(path: Path) -> str:
    return str(HOST_ROOT / path.resolve().relative_to(ROOT))


def json_file(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def cached(key: str, builder):
    at, value = _cache.get(key, (0.0, None))
    if value is None or time.monotonic() - at > CACHE_TTL:
        value = builder()
        _cache[key] = (time.monotonic(), value)
    return value


def walk_files(base: Path):
    if not base.exists():
        return
    for current, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        for name in sorted(files):
            if name not in SKIP:
                yield Path(current) / name


def media_kind(path: Path) -> str:
    if path.suffix.lower() in VIDEO_EXT:
        return "video"
    if path.suffix.lower() in AUDIO_EXT:
        return "audio"
    return "image"


def media_item(path: Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "path": rel(path),
        "url": "/media/" + rel(path),
        "kind": media_kind(path),
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
    }


def scan_projects() -> list[dict]:
    manifest = json_file(ROOT / "data" / "projects.json")
    known = {item.get("path"): item for item in manifest.get("projects", [])}
    projects = []
    for path in walk_files(ROOT):
        if path.suffix.lower() not in {".blend", ".blend1"}:
            continue
        if path.is_relative_to(ROOT / "asset_library"):
            continue
        stat = path.stat()
        item = {
            "name": path.name,
            "path": rel(path),
            "host_path": host_path(path),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
            "backup": path.suffix.lower() == ".blend1" or "backup" in path.name.lower(),
            "available": True,
            "catalog_only": False,
            "contract_only": False,
        }
        item.update(known.get(item["path"], {}))
        projects.append(item)

    # Versioned project contracts remain useful even when all production binaries are local-only.
    for contract in sorted((ROOT / "projects" / "team").glob("*/project.json")):
        document = json_file(contract)
        if not document.get("project_id"):
            continue
        workspace = ROOT / document.get("local_work_root", f"local_work/{document['project_id']}")
        projects.append({
            "name": document["project_id"],
            "path": rel(contract.parent),
            "host_path": host_path(workspace) if workspace.exists() else None,
            "size": 0,
            "modified": document.get("created_at", ""),
            "backup": False,
            "available": workspace.exists(),
            "catalog_only": False,
            "contract_only": True,
            "project_type": document.get("project_type"),
            "status": document.get("status"),
            "target": document.get("target"),
        })

    # The compact clone indexes historical Blender scenes without embedding them.
    present = {item["path"] for item in projects if not item.get("contract_only")}
    scenes = json_file(ROOT / "catalog" / "blender-scenes.json").get("blender_scenes", [])
    for scene in scenes:
        path_value = scene.get("path", "")
        if not path_value or path_value in present:
            continue
        audit = scene.get("audit", {})
        projects.append({
            "name": Path(path_value).name,
            "path": path_value,
            "host_path": None,
            "size": scene.get("bytes", 0),
            "modified": "",
            "backup": Path(path_value).suffix.lower() == ".blend1" or "backup" in Path(path_value).name.lower(),
            "available": False,
            "catalog_only": True,
            "contract_only": False,
            "asset_id": scene.get("asset_id"),
            "scene": audit.get("scene"),
            "objects": audit.get("objects"),
            "frames": [audit.get("frame_start"), audit.get("frame_end")],
            "blender_version": audit.get("blender"),
            "audit_status": audit.get("status"),
        })
    return sorted(projects, key=lambda x: (x["backup"], x["name"].lower()))


def scan_assets() -> list[dict]:
    assets = []
    roots = [ROOT / "local_assets", ROOT / "assets_blender", ROOT / "library" / "blender-choreography" / "refs"]
    for base in roots:
        for path in walk_files(base):
            if path.suffix.lower() not in MEDIA_EXT:
                continue
            item = media_item(path)
            lower = str(path).lower()
            item.update({
                "canonical": "canonical" in lower or re.match(r"^(0[0-9])[_-]|^closeup-", path.name.lower()) is not None,
                "rejected": any(word in lower for word in ("ecarte", "rejected", "_ko_", "iteration")),
                "group": "storyboard" if "storyboard" in lower else ("close-up" if "close-up" in lower or "closeup" in lower else "reference"),
                "available": True,
                "catalog_only": False,
            })
            assets.append(item)
    unique = {item["path"]: item for item in assets}
    catalog = json_file(ROOT / "catalog" / "assets.json")
    for asset in catalog.get("assets", []):
        if asset.get("kind") not in {"image", "video", "audio"}:
            continue
        paths = asset.get("paths", [])
        if not paths or any(path in unique or (ROOT / "local_assets" / path).is_file() for path in paths):
            continue
        primary = paths[0]
        lower = " ".join(paths).lower()
        roles = asset.get("roles", [])
        group = "tutorial" if "tutorial_evidence" in roles else ("storyboard" if "storyboard" in lower else ("close-up" if "close-up" in lower or "closeup" in lower else "reference"))
        unique[primary] = {
            "name": Path(primary).name,
            "path": primary,
            "url": None,
            "kind": asset.get("kind"),
            "size": asset.get("bytes", 0),
            "modified": "",
            "canonical": "canonical" in lower or any(re.match(r"^(0[0-9])[_-]|^closeup-", Path(path).name.lower()) for path in paths),
            "rejected": any(word in lower for word in ("ecarte", "rejected", "_ko_", "iteration")),
            "group": group,
            "available": False,
            "catalog_only": True,
            "asset_id": asset.get("asset_id"),
            "path_count": asset.get("path_count", len(paths)),
            "metadata": asset.get("metadata", {}),
            "roles": roles,
            "redistribution_statuses": asset.get("redistribution_statuses", []),
        }
    return sorted(unique.values(), key=lambda x: (not x["canonical"], x["rejected"], x["name"].lower()))


def scan_blender_assets() -> list[dict]:
    """List reusable Blender containers separately from visual references."""
    base = ROOT / "asset_library"
    items = []
    for path in walk_files(base):
        if path.suffix.lower() != ".blend":
            continue
        stat = path.stat()
        sidecar = path.with_suffix(".manifest.json")
        manifest = json_file(sidecar)
        if not manifest:
            manifest = json_file(path.parent / "manifest.json")
        items.append({
            "name": path.name,
            "path": rel(path),
            "host_path": host_path(path),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
            "kind": "blend-library",
            "assets": manifest.get("assets", []),
            "asset_count": len(manifest.get("assets", [])),
            "version": manifest.get("version"),
            "manifest": manifest,
            "available": True,
            "catalog_only": False,
        })
    present = {item["path"] for item in items}
    scenes = json_file(ROOT / "catalog" / "blender-scenes.json").get("blender_scenes", [])
    for scene in scenes:
        path_value = scene.get("path", "")
        if not path_value.startswith("asset_library/") or not path_value.endswith(".blend") or path_value in present:
            continue
        virtual_path = ROOT / path_value
        manifest = json_file(virtual_path.with_suffix(".manifest.json"))
        if not manifest:
            manifest = json_file(virtual_path.parent / "manifest.json")
        audit = scene.get("audit", {})
        items.append({
            "name": Path(path_value).name,
            "path": path_value,
            "host_path": None,
            "size": scene.get("bytes", 0),
            "modified": "",
            "kind": "blend-library",
            "assets": manifest.get("assets", []),
            "asset_count": len(manifest.get("assets", [])),
            "version": manifest.get("version"),
            "manifest": manifest,
            "audit": audit,
            "asset_id": scene.get("asset_id"),
            "available": False,
            "catalog_only": True,
        })
    return sorted(items, key=lambda item: item["name"].lower())


def run_roots():
    for current, dirs, _files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        here = Path(current)
        if here.name == "runs":
            for child in sorted(here.iterdir()):
                if child.is_dir() and not child.is_symlink():
                    yield child


def scan_runs() -> list[dict]:
    runs = []
    for run in run_roots():
        media = [p for p in walk_files(run) if p.suffix.lower() in MEDIA_EXT]
        media.sort(key=lambda p: (0 if p.suffix.lower() in VIDEO_EXT else 1, "preview" not in p.name.lower(), str(p)))
        gate = json_file(run / "gate.json")
        liked = json_file(run / "like.json").get("liked", False)
        metadata = json_file(run / "metadata.json")
        notes_path = run / "notes.md"
        notes = notes_path.read_text(encoding="utf-8", errors="replace")[:1200] if notes_path.exists() else ""
        path_lower = rel(run).lower()
        status = gate.get("verdict", "pending")
        if "rejected" in path_lower or "_ko_" in path_lower:
            status = "rejected"
        stat = run.stat()
        runs.append({
            "name": run.name,
            "path": rel(run),
            "lane": "choreography" if "blender-choreography" in path_lower else ("seedance" if "reel-blender" in path_lower else "asset-generation"),
            "status": status,
            "liked": bool(liked),
            "gate": gate,
            "metadata": metadata,
            "notes": notes,
            "media_count": len(media),
            "media": [media_item(p) for p in media[:40]],
            "modified": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
        })
    return sorted(runs, key=lambda x: x["modified"], reverse=True)


def scan_workflows() -> list[dict]:
    items = []
    catalog = ROOT / "workflows" / "catalog"
    if catalog.exists():
        for path in sorted(catalog.glob("*.json")):
            item = json_file(path)
            if item.get("id"):
                item["catalog_path"] = rel(path)
                items.append(item)
    return items


def scan_docs() -> list[dict]:
    docs = []
    roots = [*sorted(ROOT.glob("*.md")), ROOT / "audits", ROOT / "library", ROOT / "knowledge"]
    paths: list[Path] = []
    for base in roots:
        if base.is_file():
            paths.append(base)
        elif base.exists():
            paths.extend(p for p in walk_files(base) if p.suffix.lower() == ".md")
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        title = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")), path.stem)
        docs.append({"title": title, "path": rel(path), "excerpt": re.sub(r"[#*_>`]", "", text)[:300]})
    return sorted({d["path"]: d for d in docs}.values(), key=lambda x: x["title"].lower())


def mcp_command(command: str, params: dict | None = None, timeout: int = 20) -> dict:
    payload = json.dumps({"type": command, "params": params or {}}).encode()
    try:
        with socket.create_connection((MCP_HOST, MCP_PORT), timeout=min(timeout, 5)) as client:
            client.settimeout(timeout)
            client.sendall(payload)
            chunks = bytearray()
            while True:
                chunk = client.recv(65536)
                if not chunk:
                    break
                chunks.extend(chunk)
                try:
                    return json.loads(chunks.decode())
                except json.JSONDecodeError:
                    continue
    except (OSError, TimeoutError) as exc:
        raise RuntimeError(f"Blender MCP indisponible sur {MCP_HOST}:{MCP_PORT}: {exc}") from exc
    raise RuntimeError("Réponse Blender MCP vide ou invalide")


def save_job(job: dict):
    data = ROOT / "data"
    data.mkdir(parents=True, exist_ok=True)
    with (data / "jobs.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(job, ensure_ascii=False) + "\n")


def public_job(job: dict) -> dict:
    return {k: v for k, v in job.items() if k != "_task"}


def update_job(job_id: str, **updates):
    with _job_lock:
        job = _jobs[job_id]
        job.update(updates)
        job["updated"] = now()
        save_job(public_job(job))


def validate_params(spec: dict, supplied: dict) -> dict:
    result = {}
    for field in spec.get("fields", []):
        key = field["id"]
        value = supplied.get(key, field.get("default"))
        kind = field.get("type", "text")
        if field.get("required") and (value is None or value == ""):
            raise HTTPException(422, f"{key} est requis")
        try:
            if kind == "number":
                value = float(value)
                if "min" in field and value < field["min"]:
                    raise HTTPException(422, f"{key} doit être ≥ {field['min']}")
                if "max" in field and value > field["max"]:
                    raise HTTPException(422, f"{key} doit être ≤ {field['max']}")
            elif kind == "integer":
                value = int(value)
                if "min" in field and value < field["min"]:
                    raise HTTPException(422, f"{key} doit être ≥ {field['min']}")
                if "max" in field and value > field["max"]:
                    raise HTTPException(422, f"{key} doit être ≤ {field['max']}")
        except (TypeError, ValueError) as exc:
            raise HTTPException(422, f"Valeur numérique invalide pour {key}") from exc
        if kind == "boolean":
            if not isinstance(value, bool):
                raise HTTPException(422, f"{key} doit être un booléen JSON")
        elif kind in {"file", "directory"}:
            candidate = safe_path(str(value))
            if kind == "file" and not candidate.is_file():
                raise HTTPException(422, f"{key} doit pointer vers un fichier du workspace")
            if kind == "directory" and not candidate.is_dir():
                raise HTTPException(422, f"{key} doit pointer vers un dossier du workspace")
            value = host_path(candidate)
        elif kind == "text":
            value = str(value or "")
            if len(value) > int(field.get("max_length", 4096)):
                raise HTTPException(422, f"{key} est trop long")
        elif kind == "select" and value not in field.get("options", []):
            raise HTTPException(422, f"Valeur invalide pour {key}")
        result[key] = value
    return result


def copy_upload_limited(upload: UploadFile, destination: Path, maximum: int) -> int:
    written = 0
    try:
        with destination.open("wb") as handle:
            while chunk := upload.file.read(1024 * 1024):
                written += len(chunk)
                if written > maximum:
                    raise HTTPException(413, f"Fichier trop volumineux (maximum {maximum} octets)")
                handle.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return written


def execute_workflow(job_id: str, workflow: dict, params: dict):
    with _blender_job_lock:
        update_job(job_id, status="running", progress=10)
        try:
            script = safe_path(workflow["script"])
            scripts_root = (ROOT / "workflows" / "scripts").resolve()
            if not str(script).startswith(str(scripts_root) + os.sep):
                raise RuntimeError("Script hors de la liste contrôlée")
            stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            output = None
            if workflow.get("produces_output", True):
                output = ROOT / "renders" / f"{workflow['id']}-{stamp}-{job_id[:8]}"
                output.mkdir(parents=True, exist_ok=False)
                params["output_dir"] = host_path(output)
            params["job_id"] = job_id
            code = "STUDIO_PARAMS = " + repr(params) + "\nUNRECORDED_PARAMS = STUDIO_PARAMS\n" + script.read_text(encoding="utf-8")
            update_job(job_id, progress=20, output=rel(output) if output else None)
            response = mcp_command("execute_code", {"code": code}, timeout=int(workflow.get("timeout", 1800)))
            if response.get("status") != "success":
                raise RuntimeError(response.get("message", "Erreur Blender inconnue"))
            result = response.get("result", {})
            update_job(job_id, status="completed", progress=100, result=result)
            _cache.clear()
        except Exception as exc:
            update_job(job_id, status="failed", progress=100, error=str(exc))


def execute_tutorial_ingest(job_id: str, folder: Path, frame_interval: float, scene_threshold: float):
    update_job(job_id, status="running", progress=15, output=rel(folder))
    try:
        result = prepare_tutorial(ROOT, folder, frame_interval=frame_interval, scene_threshold=scene_threshold)
        update_job(job_id, status="completed", progress=100, result={"tutorial_id": result["id"], "status": result["status"]})
        _cache.clear()
    except Exception as exc:
        manifest = json_file(folder / "manifest.json")
        manifest.update({"status": "failed", "error": str(exc), "updated": now()})
        (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        update_job(job_id, status="failed", progress=100, error=str(exc))


@app.get("/api/health")
def api_health():
    return {"ok": True, "root": str(ROOT), "host_root": str(HOST_ROOT), "version": app.version}


@app.get("/api/summary")
def api_summary():
    projects = cached("projects", scan_projects)
    assets = cached("assets", scan_assets)
    runs = cached("runs", scan_runs)
    workflows = cached("workflows", scan_workflows)
    tutorials = cached("tutorials", lambda: scan_tutorials(ROOT))
    blender_assets = cached("blender_assets", scan_blender_assets)
    return {
        "projects": len(projects), "assets": len(assets), "runs": len(runs), "workflows": len(workflows),
        "tutorials": len(tutorials), "blender_assets": len(blender_assets),
        "validated": sum(r["status"] == "validated" for r in runs),
        "rejected": sum(r["status"] == "rejected" for r in runs),
        "liked": sum(r["liked"] for r in runs),
    }


@app.get("/api/projects")
def api_projects():
    return cached("projects", scan_projects)


@app.get("/api/assets")
def api_assets(q: str = "", group: str = "", canonical: bool = False, rejected: bool | None = None, sort: str = "name"):
    items = list(cached("assets", scan_assets))
    query = q.casefold().strip()
    if query:
        items = [x for x in items if query in (x["name"] + " " + x["path"]).casefold()]
    if group:
        items = [x for x in items if x["group"] == group]
    if canonical:
        items = [x for x in items if x["canonical"]]
    if rejected is not None:
        items = [x for x in items if x["rejected"] == rejected]
    if sort == "newest":
        items.sort(key=lambda x: x["modified"], reverse=True)
    elif sort == "largest":
        items.sort(key=lambda x: x["size"], reverse=True)
    return items


@app.get("/api/blender-assets")
def api_blender_assets():
    return cached("blender_assets", scan_blender_assets)


@app.get("/api/tutorials")
def api_tutorials():
    return cached("tutorials", lambda: scan_tutorials(ROOT))


@app.post("/api/tutorials/ingest")
async def api_tutorial_ingest(
    video: UploadFile = File(...),
    title: str = Form(""),
    frame_interval: float = Form(10.0),
    scene_threshold: float = Form(0.32),
    transcript: UploadFile | None = File(None),
):
    source_suffix = Path(video.filename or "").suffix.lower()
    if source_suffix not in VIDEO_EXT:
        raise HTTPException(415, "Vidéo attendue (.mp4, .mov, .webm ou .m4v)")
    if not 1 <= frame_interval <= 120:
        raise HTTPException(422, "L’intervalle de frames doit être compris entre 1 et 120 secondes")
    if not 0.05 <= scene_threshold <= 0.95:
        raise HTTPException(422, "Le seuil de changement de plan doit être compris entre 0.05 et 0.95")
    transcript_suffix = Path(transcript.filename or "").suffix.lower() if transcript else ""
    if transcript and transcript_suffix not in {".txt", ".md", ".srt", ".vtt"}:
        raise HTTPException(415, "Transcript attendu (.txt, .md, .srt ou .vtt)")

    tutorial_id = uuid.uuid4().hex
    clean_title = title.strip()[:160] or Path(video.filename or "Tutoriel").stem
    folder = ROOT / "knowledge" / "tutorials" / f"{slugify(clean_title)}-{tutorial_id[:8]}"
    folder.mkdir(parents=True, exist_ok=False)
    source = folder / ("source" + source_suffix)
    try:
        copy_upload_limited(video, source, MAX_UPLOAD_BYTES)
        if transcript:
            copy_upload_limited(transcript, folder / ("transcript-source" + transcript_suffix), min(MAX_UPLOAD_BYTES, 50 * 1024 * 1024))
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise

    manifest = {
        "schema_version": 1,
        "id": tutorial_id,
        "title": clean_title,
        "status": "queued",
        "source_name": source.name,
        "original_filename": video.filename,
        "created": iso_now(),
        "updated": iso_now(),
        "analysis_status": "not_started",
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    job_id = uuid.uuid4().hex
    job = {
        "id": job_id,
        "kind": "tutorial-ingest",
        "workflow_id": "tutorial-ingest",
        "workflow": f"Préparer le tutoriel · {clean_title}",
        "status": "queued",
        "progress": 0,
        "params": {"frame_interval": frame_interval, "scene_threshold": scene_threshold},
        "created": now(),
        "updated": now(),
        "output": rel(folder),
    }
    _jobs[job_id] = job
    save_job(job)
    asyncio.create_task(asyncio.to_thread(execute_tutorial_ingest, job_id, folder, frame_interval, scene_threshold))
    return {"job": public_job(job), "tutorial": manifest}


@app.post("/api/tutorials/{tutorial_id}/analysis")
async def api_tutorial_analysis(tutorial_id: str, request: Request):
    tutorial = next((item for item in scan_tutorials(ROOT) if item.get("id") == tutorial_id), None)
    if not tutorial:
        raise HTTPException(404, "Tutoriel inconnu")
    body = await request.json()
    encoded = json.dumps(body, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > 5_000_000:
        raise HTTPException(413, "Analyse trop volumineuse")
    required = {"summary", "chapters", "techniques", "workflow_recipe"}
    if not required.issubset(body):
        raise HTTPException(422, "Analyse incomplète: summary, chapters, techniques et workflow_recipe sont requis")
    folder = safe_path(tutorial["path"])
    analysis = {"schema_version": 1, **body, "tutorial_id": tutorial_id, "analyzed_at": now()}
    (folder / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    chapter_lines = "\n".join(
        f"- `{chapter.get('start', 0)}–{chapter.get('end', 0)}s` — {chapter.get('title', 'Chapitre')}"
        for chapter in analysis.get("chapters", [])
    )
    technique_lines = "\n".join(
        f"- **{item.get('domain', 'Blender')}** — {item.get('name', 'Technique')}"
        for item in analysis.get("techniques", [])
    )
    markdown = f"# Analyse — {tutorial['title']}\n\n{analysis.get('summary', '')}\n\n## Chapitres\n\n{chapter_lines or '- Aucun'}\n\n## Techniques\n\n{technique_lines or '- Aucune'}\n"
    (folder / "ANALYSIS.md").write_text(markdown, encoding="utf-8")
    manifest = json_file(folder / "manifest.json")
    manifest.update({"analysis_status": "completed", "updated": now()})
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _cache.clear()
    return analysis


@app.post("/api/tutorials/{tutorial_id}/transcript")
async def api_tutorial_transcript(tutorial_id: str, transcript: UploadFile = File(...)):
    tutorial = next((item for item in scan_tutorials(ROOT) if item.get("id") == tutorial_id), None)
    if not tutorial:
        raise HTTPException(404, "Tutoriel inconnu")
    suffix = Path(transcript.filename or "").suffix.lower()
    if suffix not in {".txt", ".md", ".srt", ".vtt"}:
        raise HTTPException(415, "Transcript attendu (.txt, .md, .srt ou .vtt)")
    folder = safe_path(tutorial["path"])
    destination = folder / ("transcript-source" + suffix)
    copy_upload_limited(transcript, destination, min(MAX_UPLOAD_BYTES, 50 * 1024 * 1024))
    result = attach_transcript(ROOT, folder, destination)
    _cache.clear()
    return {"tutorial_id": tutorial_id, "status": result["status"], "transcript": result["evidence"]["transcript"]}


@app.get("/api/runs")
def api_runs(q: str = "", lane: str = "", status: str = "", liked: bool = False, sort: str = "newest"):
    items = list(cached("runs", scan_runs))
    query = q.casefold().strip()
    if query:
        items = [x for x in items if query in (x["name"] + " " + x["path"] + " " + x["notes"]).casefold()]
    if lane:
        items = [x for x in items if x["lane"] == lane]
    if status:
        items = [x for x in items if x["status"] == status]
    if liked:
        items = [x for x in items if x["liked"]]
    if sort == "oldest":
        items.sort(key=lambda x: x["modified"])
    elif sort == "name":
        items.sort(key=lambda x: x["name"].lower())
    elif sort == "status":
        order = {"validated": 0, "pending": 1, "rejected": 2}
        items.sort(key=lambda x: (order.get(x["status"], 3), x["name"].lower()))
    return items


@app.post("/api/runs/gate")
async def api_gate(request: Request):
    body = await request.json()
    run = safe_path(body.get("path", ""))
    if not run.is_dir() or run.parent.name != "runs":
        raise HTTPException(403, "Ce chemin n’est pas un run")
    verdict = body.get("verdict")
    if verdict not in {"validated", "rejected", "pending"}:
        raise HTTPException(422, "Verdict invalide")
    payload = {"verdict": verdict, "comment": str(body.get("comment", ""))[:2000], "by": STUDIO_USER, "date": now(), "via": "blender-team-studio"}
    (run / "gate.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _cache.pop("runs", None)
    return payload


@app.get("/api/workflows")
def api_workflows():
    return cached("workflows", scan_workflows)


@app.post("/api/workflows/{workflow_id}/run")
async def api_workflow_run(workflow_id: str, request: Request):
    workflow = next((w for w in cached("workflows", scan_workflows) if w["id"] == workflow_id), None)
    if not workflow:
        raise HTTPException(404, "Workflow inconnu")
    body = await request.json()
    if workflow.get("execution") != "mcp":
        raise HTTPException(409, "Ce workflow exige une exécution batch isolée et ne peut pas être injecté via MCP")
    if workflow.get("enabled_in_app") is not True:
        raise HTTPException(409, "Ce workflow est désactivé dans l’application")
    if workflow.get("requires_confirmation") and body.get("confirmation") != workflow_id:
        raise HTTPException(409, "Confirmation explicite du workflow requise")
    params = validate_params(workflow, body.get("params", {}))
    job_id = uuid.uuid4().hex
    job = {"id": job_id, "workflow_id": workflow_id, "workflow": workflow["name"], "status": "queued", "progress": 0, "params": params, "created": now(), "updated": now()}
    _jobs[job_id] = job
    save_job(job)
    asyncio.create_task(asyncio.to_thread(execute_workflow, job_id, workflow, params))
    return public_job(job)


@app.get("/api/jobs")
def api_jobs():
    history: dict[str, dict] = {}
    path = ROOT / "data" / "jobs.jsonl"
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
                history[item["id"]] = item
            except Exception:
                continue
    history.update({k: public_job(v) for k, v in _jobs.items()})
    return sorted(history.values(), key=lambda x: x.get("updated", x.get("created", "")), reverse=True)


@app.get("/api/mcp/status")
def api_mcp_status():
    try:
        response = mcp_command("get_scene_info", timeout=6)
        return {"connected": response.get("status") == "success", "host": MCP_HOST, "port": MCP_PORT, "scene": response.get("result"), "raw": response}
    except Exception as exc:
        return {"connected": False, "host": MCP_HOST, "port": MCP_PORT, "error": str(exc)}


@app.post("/api/mcp/screenshot")
def api_mcp_screenshot():
    output = ROOT / "renders" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)
    path = output / (datetime.now().strftime("viewport-%Y%m%d-%H%M%S") + ".png")
    response = mcp_command("get_viewport_screenshot", {"max_size": 1400, "filepath": host_path(path), "format": "png"}, timeout=60)
    if response.get("status") != "success":
        raise HTTPException(502, response.get("message", "Capture impossible"))
    _cache.clear()
    return {"path": rel(path), "url": "/media/" + rel(path), "response": response}


@app.get("/api/docs")
def api_docs():
    return cached("docs", scan_docs)


@app.get("/api/doc")
def api_doc(path: str):
    file = safe_path(path)
    if file.suffix.lower() != ".md":
        raise HTTPException(415, "Document Markdown attendu")
    return {"path": rel(file), "content": file.read_text(encoding="utf-8", errors="replace")}


@app.get("/api/native-config")
def api_native_config():
    default_blend = None
    if DEFAULT_BLEND_RELATIVE:
        candidate = safe_path(DEFAULT_BLEND_RELATIVE)
        if candidate.is_file() and candidate.suffix.lower() == ".blend":
            default_blend = host_path(candidate)
    return {"root": str(HOST_ROOT), "default_blend": default_blend, "vscode": str(HOST_ROOT)}


@app.get("/media/{path:path}")
def media(path: str):
    file = safe_path(path)
    if not file.is_file():
        raise HTTPException(404)
    mime, _ = mimetypes.guess_type(file.name)
    return FileResponse(file, media_type=mime or "application/octet-stream", filename=None)


@app.exception_handler(Exception)
async def unhandled(_request: Request, exc: Exception):
    return Response(content=json.dumps({"detail": str(exc)}, ensure_ascii=False), status_code=500, media_type="application/json")


app.mount("/", StaticFiles(directory=APP_DIR / "static", html=True), name="static")
