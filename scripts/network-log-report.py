#!/usr/bin/env python3
"""Create a minimal, allowlisted network-test report without copying identities or addresses."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
GIT_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SESSION_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ROSTER_PATTERN = re.compile(r"\[GAME-CONNECTION\]\s+Roster updated \((\d+) participant\(s\)\)\.")
AUTH_PATTERN = re.compile(r"\[GAME-CONNECTION\]\s+Authenticated as .+ on [^.]+\.")
EXCEPTION_PATTERN = re.compile(r"(?:^|\s)([A-Za-z_][\w.]*Exception):")
SENSITIVE_OUTPUT_PATTERNS = (
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"/(?:Users|home)/", re.IGNORECASE),
    re.compile(r"[A-Za-z]:\\Users\\", re.IGNORECASE),
    re.compile(r"\[IP\]", re.IGNORECASE),
)


@dataclass(frozen=True)
class Source:
    role: str
    platform: str
    path: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_source(raw: str) -> Source:
    parts = raw.split(":", 2)
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("--log attend ROLE:PLATFORM:CHEMIN")
    role, platform, raw_path = parts
    role = role.lower()
    platform = platform.lower()
    if role not in {"host", "client"}:
        raise argparse.ArgumentTypeError("ROLE doit être host ou client")
    if platform not in {"macos", "windows"}:
        raise argparse.ArgumentTypeError("PLATFORM doit être macos ou windows")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return Source(role=role, platform=platform, path=path)


def extract_events(path: Path) -> tuple[list[dict[str, Any]], int, int]:
    events: list[dict[str, Any]] = []
    fatal_count = 0
    error_count = 0
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    for line_number, line in enumerate(lines, start=1):
        event: dict[str, Any] | None = None
        if "Local server is started for Tugboat." in line:
            event = {"line": line_number, "event": "server_started"}
        elif "Local server is stopped for Tugboat." in line:
            event = {"line": line_number, "event": "server_stopped"}
        elif "Local client is started for Tugboat." in line:
            event = {"line": line_number, "event": "client_started"}
        elif "Local client is stopped for Tugboat." in line:
            event = {"line": line_number, "event": "client_stopped"}
        elif "Remote connection started for Id" in line:
            event = {"line": line_number, "event": "remote_connected"}
        elif "Remote connection stopped for Id" in line:
            event = {"line": line_number, "event": "remote_disconnected"}
        elif AUTH_PATTERN.search(line):
            event = {"line": line_number, "event": "authenticated"}
        else:
            roster = ROSTER_PATTERN.search(line)
            if roster:
                event = {
                    "line": line_number,
                    "event": "roster_updated",
                    "participants": int(roster.group(1)),
                }

        if event is not None:
            events.append(event)

        exception = EXCEPTION_PATTERN.search(line)
        if exception:
            fatal_count += 1
            events.append(
                {
                    "line": line_number,
                    "event": "fatal_exception",
                    "exceptionType": exception.group(1).split(".")[-1],
                }
            )
        elif re.search(r"\b(?:Crash!!!|Assertion failed)\b", line, re.IGNORECASE):
            fatal_count += 1
            events.append({"line": line_number, "event": "fatal_runtime_error"})
        elif "[GAME-CONNECTION] ERREUR:" in line:
            error_count += 1
            events.append({"line": line_number, "event": "game_connection_error"})
        elif "Tugboat" in line and re.search(r"\b(?:failed|failure|timed out|timeout)\b", line, re.IGNORECASE):
            error_count += 1
            events.append({"line": line_number, "event": "transport_error"})

    return events, fatal_count, error_count


def reconnect_observed(events: list[dict[str, Any]]) -> bool:
    disconnected = False
    for event in events:
        if event["event"] == "remote_disconnected":
            disconnected = True
        elif disconnected and event["event"] == "remote_connected":
            return True
    return False


def analyse_sources(
    sources: list[Source],
    *,
    commit: str,
    session_id: str,
    expected_participants: int,
    transport: str,
    require_reconnection: bool,
) -> dict[str, Any]:
    source_reports: list[dict[str, Any]] = []
    total_fatal = 0
    total_errors = 0
    max_roster = 0
    authenticated_logs = 0

    for index, source in enumerate(sources, start=1):
        events, fatal_count, error_count = extract_events(source.path)
        total_fatal += fatal_count
        total_errors += error_count
        roster_counts = [event["participants"] for event in events if event["event"] == "roster_updated"]
        max_roster = max([max_roster, *roster_counts])
        authenticated = any(event["event"] == "authenticated" for event in events)
        authenticated_logs += int(authenticated)
        source_reports.append(
            {
                "alias": f"LOG-{index:02d}",
                "role": source.role,
                "platform": source.platform,
                "rawSha256": file_sha256(source.path),
                "rawBytes": source.path.stat().st_size,
                "authenticated": authenticated,
                "fatalCount": fatal_count,
                "errorCount": error_count,
                "events": events,
            }
        )

    host_present = any(source.role == "host" for source in sources)
    all_authenticated = authenticated_logs == len(sources)
    did_reconnect = any(reconnect_observed(source["events"]) for source in source_reports)
    missing: list[str] = []
    if len(sources) < expected_participants:
        missing.append(f"log_count_{expected_participants}")
    if len({source.path.resolve() for source in sources}) != len(sources):
        missing.append("distinct_log_sources")
    if len({source["rawSha256"] for source in source_reports}) != len(source_reports):
        missing.append("distinct_log_content")
    if not host_present:
        missing.append("host_log")
    if not all_authenticated:
        missing.append("authentication_per_log")
    if max_roster < expected_participants:
        missing.append(f"roster_{expected_participants}")
    if require_reconnection and not did_reconnect:
        missing.append("reconnection")

    if total_fatal or total_errors:
        verdict = "FAIL"
    elif missing:
        verdict = "INCOMPLETE"
    else:
        verdict = "PASS"

    return {
        "schemaVersion": 1,
        "kind": "redacted-network-log-report",
        "generatedAtUtc": utc_now(),
        "sessionId": session_id,
        "sourceGitCommit": commit,
        "transport": transport,
        "expectedParticipants": expected_participants,
        "sourceCount": len(sources),
        "privacy": {
            "allowlistedEventsOnly": True,
            "participantNamesCollected": False,
            "networkAddressesCollected": False,
            "machineNamesCollected": False,
            "rawLogPathsCollected": False,
            "rawLogsEmbedded": False,
        },
        "summary": {
            "verdict": verdict,
            "authenticatedLogs": authenticated_logs,
            "maxRosterParticipants": max_roster,
            "fatalCount": total_fatal,
            "errorCount": total_errors,
            "reconnectionRequired": require_reconnection,
            "reconnectionObserved": did_reconnect,
            "missing": missing,
        },
        "sources": source_reports,
    }


def assert_redacted(report: dict[str, Any]) -> None:
    serialized = json.dumps(report, ensure_ascii=False)
    for pattern in SENSITIVE_OUTPUT_PATTERNS:
        if pattern.search(serialized):
            raise ValueError(f"sensitive output pattern detected: {pattern.pattern}")


def write_reports(output_directory: Path, report: dict[str, Any]) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    assert_redacted(report)
    (output_directory / "network-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = report["summary"]
    lines = [
        "# Rapport réseau expurgé",
        "",
        f"- Verdict : **{summary['verdict']}**",
        f"- Commit : `{report['sourceGitCommit']}`",
        f"- Transport : `{report['transport']}`",
        f"- Logs analysés : {report['sourceCount']}",
        f"- Logs authentifiés : {summary['authenticatedLogs']}",
        f"- Roster maximal : {summary['maxRosterParticipants']} / {report['expectedParticipants']}",
        f"- Erreurs/fatales : {summary['errorCount']} / {summary['fatalCount']}",
        f"- Reconnexion : {'observée' if summary['reconnectionObserved'] else 'non observée'}",
        f"- Preuves manquantes : {', '.join(summary['missing']) if summary['missing'] else 'aucune'}",
        "",
        "Cet extrait ne contient ni nom de participant, ni adresse réseau, ni nom de machine, ni chemin brut.",
        "Les logs sources restent privés et ne sont pas intégrés au rapport.",
    ]
    (output_directory / "network-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", action="append", type=parse_source, required=True, help="ROLE:PLATFORM:CHEMIN")
    parser.add_argument("--commit", required=True, help="commit Git exact joué")
    parser.add_argument("--session-id", required=True, help="slug anonyme de session")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-participants", type=int, default=3)
    parser.add_argument(
        "--transport",
        choices=("tugboat-loopback", "tugboat-tailscale"),
        default="tugboat-tailscale",
    )
    parser.add_argument("--require-reconnection", action="store_true")
    args = parser.parse_args()
    if not GIT_COMMIT_PATTERN.fullmatch(args.commit):
        parser.error("--commit doit être un SHA Git complet de 40 caractères")
    if not SESSION_PATTERN.fullmatch(args.session_id):
        parser.error("--session-id doit être un slug anonyme en minuscules")
    if not 1 <= args.expected_participants <= 12:
        parser.error("--expected-participants doit être compris entre 1 et 12")
    return args


def main() -> int:
    args = parse_args()
    try:
        for source in args.log:
            if not source.path.is_file() or source.path.stat().st_size == 0:
                raise FileNotFoundError(f"log absent ou vide pour {source.role}/{source.platform}")
        output_directory = args.output_dir.expanduser()
        if not output_directory.is_absolute():
            output_directory = REPO_ROOT / output_directory
        report = analyse_sources(
            args.log,
            commit=args.commit,
            session_id=args.session_id,
            expected_participants=args.expected_participants,
            transport=args.transport,
            require_reconnection=args.require_reconnection,
        )
        write_reports(output_directory, report)
    except (OSError, ValueError) as error:
        print(f"NETWORK REPORT ERROR: {error}", file=sys.stderr)
        return 2

    print(f"NETWORK {report['summary']['verdict']} — {output_directory / 'network-report.json'}")
    return {"PASS": 0, "INCOMPLETE": 1, "FAIL": 2}[report["summary"]["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
