"""Client for the live BlenderMCP session (addon socket, 127.0.0.1:9876).

This speaks the BlenderMCP addon protocol directly. It is the same interactive
GUI session, the same command set (`get_scene_info`, `get_object_info`,
`get_viewport_screenshot`, `execute_code`) and the same main-thread execution
that the `blender-mcp` stdio shim drives. It is NOT a batch `--background` run:
the scene stays open and is mutated in place.

Reason this client exists rather than the packaged shim: the Claude Code MCP
server named `blender` is registered under the project scope
a different local project directory, not under this repository, so its tools
are not bound in a session started from `JEU/GAME`. The transport underneath is
identical. Recorded as a declared deviation of client shim, never of mode.
"""
from __future__ import annotations

import json
import pathlib
import socket
from typing import Any

HOST = "127.0.0.1"
PORT = 9876

# The working copy this pole is allowed to mutate. Every mutating call asserts
# the live session still points here, so a session that silently became Kimi's
# master, the SB_Idle master or the runtime FBX aborts instead of being written.
_STUDIO = pathlib.Path(__file__).resolve().parents[4]
OWNED_FILE = str(
    _STUDIO / "local_work" / "sandbox-character-motion-object-claude-v001"
    / "work" / "sandbox_character_claude_motion_object_master.blend"
)

FORBIDDEN_SUBSTRINGS = (
    "sandbox-character-animation-v001",
    "sandbox_character_SB_Idle_master",
    "PersoBouleRigged",
    "kimi",
)


class McpError(RuntimeError):
    pass


def send(command_type: str, params: dict[str, Any] | None = None, timeout: float = 600.0) -> Any:
    """Send one command and return its `result`, raising on protocol errors."""
    payload = json.dumps({"type": command_type, "params": params or {}}).encode("utf-8")
    with socket.create_connection((HOST, PORT), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(payload)
        chunks: list[bytes] = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            try:
                # The addon answers with exactly one JSON document per command.
                return _unwrap(json.loads(b"".join(chunks).decode("utf-8")))
            except json.JSONDecodeError:
                continue  # partial frame, keep reading
    raise McpError(f"connection closed before a complete reply to {command_type}")


def _unwrap(response: dict[str, Any]) -> Any:
    if response.get("status") != "success":
        raise McpError(response.get("message", "unknown MCP error"))
    return response.get("result")


def run(code: str) -> str:
    """Execute Python inside the live session and return its captured stdout."""
    result = send("execute_code", {"code": code})
    if isinstance(result, dict):
        return str(result.get("result", result))
    return str(result)


def run_json(code: str) -> Any:
    """Execute code whose last action prints one JSON document; parse it.

    The addon returns everything the code printed, so the payload is delimited
    explicitly rather than assuming it is the only thing on stdout.
    """
    out = run(code)
    start = out.find("<<<JSON")
    end = out.find("JSON>>>")
    if start == -1 or end == -1:
        raise McpError(f"no delimited JSON payload in output:\n{out}")
    return json.loads(out[start + len("<<<JSON"): end])


def current_file() -> str:
    return run_json(
        "import bpy, json\n"
        "print('<<<JSON' + json.dumps(bpy.data.filepath) + 'JSON>>>')\n"
    )


def assert_owned_session() -> str:
    """Refuse to mutate unless the live session is this pole's working copy."""
    path = current_file()
    lowered = path.lower()
    for bad in FORBIDDEN_SUBSTRINGS:
        if bad in lowered:
            raise McpError(
                f"REFUS: la session MCP ouverte pointe vers un fichier interdit ({path})"
            )
    if path != OWNED_FILE:
        raise McpError(
            f"REFUS: la session MCP ouverte n'est pas la copie de travail Claude.\n"
            f"  ouverte : {path}\n  attendue: {OWNED_FILE}"
        )
    return path


if __name__ == "__main__":
    print("scene:", json.dumps(send("get_scene_info"), indent=2)[:600])
    print("owned session:", assert_owned_session())
