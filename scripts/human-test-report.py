#!/usr/bin/env python3
"""Produit le verdict minimal HT-00 depuis les marqueurs du log Unity."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SESSIONS_ROOT = REPO_ROOT / "Logs" / "HumanTest"
REQUIRED_EVENTS = ("ready", "look", "movement", "jump", "punch", "bot_hit")
MAZE_EVENTS = ("pivot_turned", "wall_turned")
MAZE_DIAGNOSTIC_EVENTS = (
    "pivot_input",
    "pivot_target_miss",
    "pivot_contact",
    "pivot_rejected_local",
    "pivot_request",
    "pivot_rejected_server",
    "wall_contact",
    "wall_request",
    "wall_rejected_server",
    "wall_push_started",
    "wall_punch_contact",
    "wall_turn_rejected",
)
EVENT_PATTERN = re.compile(r"\[GAME-SMOKE\]\s+([a-z0-9_]+)(?:\s+(.*))?")
FATAL_PATTERNS = (
    re.compile(r"(?:^|\s)(?:[A-Za-z_][\w.]*Exception):"),
    re.compile(r"\bCrash!!!\b", re.IGNORECASE),
    re.compile(r"\bAssertion failed\b", re.IGNORECASE),
    re.compile(r"\[GAME-SMOKE\]\s+fatal\b", re.IGNORECASE),
)


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def resolve_session(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    if path.parts[:2] == ("Logs", "HumanTest"):
        return REPO_ROOT / path
    return SESSIONS_ROOT / path


def newest_completed_session() -> Path:
    if not SESSIONS_ROOT.is_dir():
        raise FileNotFoundError(f"aucun dossier de session sous {display_path(SESSIONS_ROOT)}")

    candidates = [
        directory
        for directory in SESSIONS_ROOT.iterdir()
        if directory.is_dir()
        and (directory / "host.log").is_file()
        and (directory / "host.log").stat().st_size > 0
    ]
    if not candidates:
        raise FileNotFoundError("aucune session avec un host.log non vide")
    return max(candidates, key=lambda directory: (directory / "host.log").stat().st_mtime)


def analyse_log(log_path: Path) -> dict:
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    events: dict[str, list[dict[str, object]]] = {}
    fatal_errors: list[dict[str, object]] = []

    for line_number, line in enumerate(lines, start=1):
        event_match = EVENT_PATTERN.search(line)
        if event_match:
            name = event_match.group(1)
            events.setdefault(name, []).append(
                {"line": line_number, "details": (event_match.group(2) or "").strip()}
            )

        if any(pattern.search(line) for pattern in FATAL_PATTERNS):
            fatal_errors.append({"line": line_number, "message": line.strip()[:500]})

    missing = [event for event in REQUIRED_EVENTS if event not in events]
    if not any(event in events for event in MAZE_EVENTS):
        missing.append("pivot_turned|wall_turned")
    maze_diagnostics = [event for event in MAZE_DIAGNOSTIC_EVENTS if event in events]

    if fatal_errors:
        verdict = "FAIL"
    elif missing:
        verdict = "INCOMPLETE"
    else:
        verdict = "PASS"

    return {
        "schemaVersion": 1,
        "checkedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "log": display_path(log_path),
        "verdict": verdict,
        "events": events,
        "missing": missing,
        "mazeDiagnostics": maze_diagnostics,
        "fatalErrors": fatal_errors,
    }


def write_reports(session_path: Path, result: dict) -> None:
    (session_path / "report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    event_names = sorted(result["events"])
    lines = [
        "# Rapport HT-00",
        "",
        f"- Verdict : **{result['verdict']}**",
        f"- Log : `{result['log']}`",
        f"- Marqueurs vus : {', '.join(event_names) if event_names else 'aucun'}",
        f"- Actions manquantes : {', '.join(result['missing']) if result['missing'] else 'aucune'}",
        f"- Étapes de diagnostic labyrinthe : {', '.join(result['mazeDiagnostics']) if result['mazeDiagnostics'] else 'aucune'}",
        f"- Erreurs fatales : {len(result['fatalErrors'])}",
        "",
        "`PASS` signifie uniquement que le smoke test local minimum a été parcouru sans erreur fatale détectée.",
    ]
    (session_path / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--session", help="ID ou chemin d'une session Logs/HumanTest")
    selection.add_argument("--log", type=Path, help="chemin explicite vers host.log")
    parser.add_argument("--no-write", action="store_true", help="ne pas écrire report.json/report.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.log:
            log_path = args.log.expanduser()
            if not log_path.is_absolute():
                log_path = REPO_ROOT / log_path
            session_path = log_path.parent
        else:
            session_path = resolve_session(args.session) if args.session else newest_completed_session()
            log_path = session_path / "host.log"

        if not log_path.is_file() or log_path.stat().st_size == 0:
            raise FileNotFoundError(f"log absent ou vide : {display_path(log_path)}")

        result = analyse_log(log_path)
        if not args.no_write:
            write_reports(session_path, result)
    except (FileNotFoundError, OSError) as error:
        print(f"HT-00 REPORT ERROR: {error}", file=sys.stderr)
        return 2

    print(f"HT-00 {result['verdict']} — {result['log']}")
    if result["missing"]:
        print(f"Actions manquantes: {', '.join(result['missing'])}")
    if "pivot_turned|wall_turned" in result["missing"]:
        diagnostics = ", ".join(result["mazeDiagnostics"]) if result["mazeDiagnostics"] else "aucune"
        print(f"Diagnostic labyrinthe observé: {diagnostics}")
    if result["fatalErrors"]:
        first = result["fatalErrors"][0]
        print(f"Première erreur fatale: ligne {first['line']} — {first['message']}")

    return {"PASS": 0, "INCOMPLETE": 1, "FAIL": 2}[result["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
