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
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SESSION_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
UTC_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ROSTER_PATTERN = re.compile(r"\[GAME-CONNECTION\]\s+Roster updated \((\d+) participant\(s\)\)\.")
AUTH_PATTERN = re.compile(r"\[GAME-CONNECTION\]\s+Authenticated as .+ on [^.]+\.")
BUILD_IDENTITY_PATTERN = re.compile(
    r"\[GAME-BUILD\]\s+schema=(?P<schema>\d+)"
    r"\s+buildId=(?P<build_id>[0-9a-f]{64})"
    r"\s+buildSetId=(?P<build_set_id>[0-9a-f]{64})"
    r"\s+commit=(?P<commit>[0-9a-f]{40}|unknown)"
    r"\s+dirty=(?P<dirty>true|false)"
    r"\s+profile=(?P<profile>[a-z0-9]+(?:-[a-z0-9]+)*)"
    r"\s+platform=(?P<platform>macos|windows)"
    r"\s+unity=(?P<unity>\S+)"
    r"\s+startedAt=(?P<started_at>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"
)
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


@dataclass(frozen=True)
class BuildManifestSource:
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


def parse_manifest_source(raw: str) -> BuildManifestSource:
    parts = raw.split(":", 1)
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("--manifest attend PLATFORM:CHEMIN")
    platform, raw_path = parts
    platform = platform.lower()
    if platform not in {"macos", "windows"}:
        raise argparse.ArgumentTypeError("PLATFORM doit être macos ou windows")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return BuildManifestSource(platform=platform, path=path)


def extract_events(path: Path) -> tuple[list[dict[str, Any]], int, int, list[dict[str, Any]], int]:
    events: list[dict[str, Any]] = []
    identities: list[dict[str, Any]] = []
    identity_marker_count = 0
    fatal_count = 0
    error_count = 0
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    for line_number, line in enumerate(lines, start=1):
        event: dict[str, Any] | None = None
        if "[GAME-BUILD]" in line:
            identity_marker_count += 1
            identity_match = BUILD_IDENTITY_PATTERN.search(line)
            if identity_match:
                identity = {
                    "schemaVersion": int(identity_match.group("schema")),
                    "buildId": identity_match.group("build_id"),
                    "buildSetId": identity_match.group("build_set_id"),
                    "sourceGitCommit": identity_match.group("commit"),
                    "sourceDirtyWorktree": identity_match.group("dirty") == "true",
                    "profile": identity_match.group("profile"),
                    "platform": identity_match.group("platform"),
                    "unityVersion": identity_match.group("unity"),
                    "startedAtUtc": identity_match.group("started_at"),
                }
                identities.append(identity)
                events.append({"line": line_number, "event": "build_identity"})

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

    return events, fatal_count, error_count, identities, identity_marker_count


def reconnect_observed(events: list[dict[str, Any]]) -> bool:
    disconnected = False
    for event in events:
        if event["event"] == "remote_disconnected":
            disconnected = True
        elif disconnected and event["event"] == "remote_connected":
            return True
    return False


def validate_build_manifest(
    source: BuildManifestSource,
) -> tuple[dict[str, Any], dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    try:
        document = json.loads(source.path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}, None, ["json_invalid"]

    if not isinstance(document, dict):
        return {}, None, ["root_not_object"]

    def require(condition: bool, error: str) -> None:
        if not condition:
            errors.append(error)

    require(document.get("schemaVersion") == 2, "schema_version_2")
    require(document.get("kind") == "unity-player-build", "kind_invalid")
    require(document.get("platform") == source.platform, "platform_mismatch")
    require(document.get("result") == "passed", "result_not_passed")
    require(document.get("exitCode") == 0, "exit_code_nonzero")
    require(document.get("provenance") == "current-run", "provenance_invalid")
    require(isinstance(document.get("sourceDirtyWorktree"), bool), "dirty_flag_invalid")
    require(GIT_COMMIT_PATTERN.fullmatch(str(document.get("sourceGitCommit", ""))) is not None, "commit_invalid")
    require(SHA256_PATTERN.fullmatch(str(document.get("buildId", ""))) is not None, "build_id_invalid")
    require(SHA256_PATTERN.fullmatch(str(document.get("buildSetId", ""))) is not None, "build_set_id_invalid")
    require(SESSION_PATTERN.fullmatch(str(document.get("profile", ""))) is not None, "profile_invalid")
    unity_version = document.get("unityVersion")
    require(isinstance(unity_version, str) and bool(unity_version) and not any(
        character.isspace() for character in unity_version
    ), "unity_version_invalid")
    require(SHA256_PATTERN.fullmatch(str(document.get("binarySha256", ""))) is not None, "binary_hash_invalid")
    require(
        UTC_TIMESTAMP_PATTERN.fullmatch(str(document.get("startedAtUtc", ""))) is not None,
        "started_at_utc_invalid",
    )
    binary_size = document.get("binarySizeBytes")
    require(isinstance(binary_size, int) and not isinstance(binary_size, bool) and binary_size > 0,
            "binary_size_invalid")

    fingerprint = document.get("bundleFingerprint")
    fingerprint_summary: dict[str, Any] = {}
    if not isinstance(fingerprint, dict):
        errors.append("bundle_fingerprint_missing")
    else:
        require(fingerprint.get("schemaVersion") == 1, "bundle_schema_version_1")
        require(fingerprint.get("kind") == "unity-build-bundle-fingerprint", "bundle_kind_invalid")
        require(
            fingerprint.get("algorithm") == "sha256-relative-path-size-content-v1",
            "bundle_algorithm_invalid",
        )
        files = fingerprint.get("files")
        canonical_rows: list[tuple[str, int, str]] = []
        if not isinstance(files, list) or not files:
            errors.append("bundle_files_invalid")
        else:
            for entry in files:
                if not isinstance(entry, dict):
                    errors.append("bundle_file_entry_invalid")
                    continue
                relative_path = entry.get("relativePath")
                size = entry.get("sizeBytes")
                digest = entry.get("sha256")
                path_valid = (
                    isinstance(relative_path, str)
                    and bool(relative_path)
                    and not relative_path.startswith("/")
                    and "\\" not in relative_path
                    and all(part not in {"", ".", ".."} for part in relative_path.split("/"))
                )
                if not path_valid:
                    errors.append("bundle_relative_path_invalid")
                    continue
                if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                    errors.append("bundle_file_size_invalid")
                    continue
                if SHA256_PATTERN.fullmatch(str(digest)) is None:
                    errors.append("bundle_file_hash_invalid")
                    continue
                canonical_rows.append((relative_path, size, digest))

        sorted_rows = sorted(canonical_rows, key=lambda row: row[0])
        if canonical_rows != sorted_rows or len({row[0] for row in canonical_rows}) != len(canonical_rows):
            errors.append("bundle_file_order_or_uniqueness_invalid")
        canonical = "".join(f"{path}\t{size}\t{digest}\n" for path, size, digest in sorted_rows)
        calculated_manifest_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        declared_manifest_hash = fingerprint.get("bundleManifestSha256")
        require(declared_manifest_hash == calculated_manifest_hash, "bundle_manifest_hash_mismatch")
        require(fingerprint.get("fileCount") == len(sorted_rows), "bundle_file_count_mismatch")
        require(fingerprint.get("totalBytes") == sum(row[1] for row in sorted_rows), "bundle_total_bytes_mismatch")
        fingerprint_summary = {
            "bundleManifestSha256": declared_manifest_hash
            if SHA256_PATTERN.fullmatch(str(declared_manifest_hash)) else None,
            "fileCount": fingerprint.get("fileCount") if isinstance(fingerprint.get("fileCount"), int) else None,
            "totalBytes": fingerprint.get("totalBytes") if isinstance(fingerprint.get("totalBytes"), int) else None,
        }

    identity = None
    if all(
        (
            SHA256_PATTERN.fullmatch(str(document.get("buildId", ""))),
            SHA256_PATTERN.fullmatch(str(document.get("buildSetId", ""))),
            GIT_COMMIT_PATTERN.fullmatch(str(document.get("sourceGitCommit", ""))),
            isinstance(document.get("sourceDirtyWorktree"), bool),
            SESSION_PATTERN.fullmatch(str(document.get("profile", ""))),
            isinstance(unity_version, str),
            UTC_TIMESTAMP_PATTERN.fullmatch(str(document.get("startedAtUtc", ""))),
        )
    ):
        identity = {
            "buildId": document["buildId"],
            "buildSetId": document["buildSetId"],
            "sourceGitCommit": document["sourceGitCommit"],
            "sourceDirtyWorktree": document["sourceDirtyWorktree"],
            "profile": document["profile"],
            "platform": document.get("platform"),
            "unityVersion": document["unityVersion"],
            "startedAtUtc": document.get("startedAtUtc"),
        }

    return fingerprint_summary, identity, sorted(set(errors))


def analyse_sources(
    sources: list[Source],
    *,
    manifests: list[BuildManifestSource],
    commit: str,
    session_id: str,
    expected_participants: int,
    transport: str,
    require_reconnection: bool,
) -> dict[str, Any]:
    source_reports: list[dict[str, Any]] = []
    manifest_reports: list[dict[str, Any]] = []
    manifest_identities: dict[str, dict[str, Any]] = {}
    total_fatal = 0
    total_errors = 0
    max_roster = 0
    authenticated_logs = 0
    valid_identities: list[dict[str, Any]] = []

    for index, source in enumerate(sources, start=1):
        events, fatal_count, error_count, identities, marker_count = extract_events(source.path)
        total_fatal += fatal_count
        total_errors += error_count
        roster_counts = [event["participants"] for event in events if event["event"] == "roster_updated"]
        max_roster = max([max_roster, *roster_counts])
        authenticated = any(event["event"] == "authenticated" for event in events)
        authenticated_logs += int(authenticated)
        identity = identities[0] if marker_count == 1 and len(identities) == 1 else None
        if identity is not None:
            valid_identities.append(identity)
        source_reports.append(
            {
                "alias": f"LOG-{index:02d}",
                "role": source.role,
                "platform": source.platform,
                "rawSha256": file_sha256(source.path),
                "rawBytes": source.path.stat().st_size,
                "buildIdentityMarkerCount": marker_count,
                "buildIdentity": identity,
                "authenticated": authenticated,
                "fatalCount": fatal_count,
                "errorCount": error_count,
                "events": events,
            }
        )

    for index, manifest in enumerate(manifests, start=1):
        fingerprint_summary, identity, errors = validate_build_manifest(manifest)
        if identity is not None and manifest.platform not in manifest_identities:
            manifest_identities[manifest.platform] = identity
        manifest_reports.append(
            {
                "alias": f"BUILD-{index:02d}",
                "platform": manifest.platform,
                "rawSha256": file_sha256(manifest.path),
                "rawBytes": manifest.path.stat().st_size,
                "buildIdentity": identity,
                "bundleFingerprint": fingerprint_summary,
                "validationErrors": errors,
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
    if len(valid_identities) != len(sources):
        missing.append("build_identity_once_per_log")
    if any(identity["schemaVersion"] != 1 for identity in valid_identities):
        missing.append("build_identity_schema_1")
    if any(identity["sourceGitCommit"] != commit for identity in valid_identities):
        missing.append("source_commit_match")
    if any(identity["sourceDirtyWorktree"] for identity in valid_identities):
        missing.append("clean_build_per_log")
    if any(
        report["buildIdentity"] is not None and
        report["buildIdentity"]["platform"] != report["platform"]
        for report in source_reports
    ):
        missing.append("platform_identity_match")
    if len({identity["buildSetId"] for identity in valid_identities}) > 1:
        missing.append("shared_build_set")
    if len({identity["profile"] for identity in valid_identities}) > 1:
        missing.append("shared_build_profile")
    if len({identity["unityVersion"] for identity in valid_identities}) > 1:
        missing.append("shared_unity_version")
    build_ids_by_platform: dict[str, set[str]] = {}
    for identity in valid_identities:
        build_ids_by_platform.setdefault(identity["platform"], set()).add(identity["buildId"])
    if any(len(build_ids) > 1 for build_ids in build_ids_by_platform.values()):
        missing.append("consistent_build_per_platform")
    expected_platforms = {source.platform for source in sources}
    manifest_platforms = [manifest.platform for manifest in manifests]
    if (
        set(manifest_platforms) != expected_platforms
        or any(manifest_platforms.count(platform) != 1 for platform in expected_platforms)
    ):
        missing.append("one_build_manifest_per_platform")
    if len({manifest.path.resolve() for manifest in manifests}) != len(manifests):
        missing.append("distinct_build_manifest_sources")
    if any(report["validationErrors"] for report in manifest_reports):
        missing.append("valid_build_manifest_per_platform")
    if any(
        identity["sourceGitCommit"] != commit or identity["sourceDirtyWorktree"]
        for identity in manifest_identities.values()
    ):
        missing.append("clean_expected_commit_per_manifest")
    for source_report in source_reports:
        log_identity = source_report["buildIdentity"]
        manifest_identity = manifest_identities.get(source_report["platform"])
        if log_identity is None or manifest_identity is None:
            continue
        comparable_log_identity = {
            key: log_identity[key]
            for key in (
                "buildId",
                "buildSetId",
                "sourceGitCommit",
                "sourceDirtyWorktree",
                "profile",
                "platform",
                "unityVersion",
                "startedAtUtc",
            )
        }
        if comparable_log_identity != manifest_identity:
            missing.append("log_manifest_identity_match")
            break

    if total_fatal or total_errors:
        verdict = "FAIL"
    elif missing:
        verdict = "INCOMPLETE"
    else:
        verdict = "PASS"

    observed_commits = {identity["sourceGitCommit"] for identity in valid_identities}
    observed_build_sets = {identity["buildSetId"] for identity in valid_identities}
    observed_profiles = {identity["profile"] for identity in valid_identities}

    return {
        "schemaVersion": 2,
        "kind": "redacted-network-log-report",
        "generatedAtUtc": utc_now(),
        "sessionId": session_id,
        "expectedSourceGitCommit": commit,
        "sourceGitCommit": next(iter(observed_commits)) if len(observed_commits) == 1 else None,
        "buildSetId": next(iter(observed_build_sets)) if len(observed_build_sets) == 1 else None,
        "profile": next(iter(observed_profiles)) if len(observed_profiles) == 1 else None,
        "transport": transport,
        "expectedParticipants": expected_participants,
        "sourceCount": len(sources),
        "manifestCount": len(manifests),
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
        "manifests": manifest_reports,
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
        f"- Commit attendu : `{report['expectedSourceGitCommit']}`",
        f"- Commit observe : `{report['sourceGitCommit'] or 'non prouve'}`",
        f"- Build set : `{report['buildSetId'] or 'non prouve'}`",
        f"- Transport : `{report['transport']}`",
        f"- Logs analysés : {report['sourceCount']}",
        f"- Manifests de build : {report['manifestCount']}",
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
    parser.add_argument(
        "--manifest",
        action="append",
        type=parse_manifest_source,
        required=True,
        help="PLATFORM:CHEMIN vers le build-manifest.json réellement distribué",
    )
    parser.add_argument("--commit", required=True, help="commit Git attendu; les logs doivent le prouver")
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
        for manifest in args.manifest:
            if not manifest.path.is_file() or manifest.path.stat().st_size == 0:
                raise FileNotFoundError(f"manifest absent ou vide pour {manifest.platform}")
        output_directory = args.output_dir.expanduser()
        if not output_directory.is_absolute():
            output_directory = REPO_ROOT / output_directory
        report = analyse_sources(
            args.log,
            manifests=args.manifest,
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
