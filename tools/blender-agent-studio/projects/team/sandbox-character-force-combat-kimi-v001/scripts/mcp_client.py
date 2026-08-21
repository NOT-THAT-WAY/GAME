#!/usr/bin/env python3
"""Minimal BlenderMCP socket client for the Kimi force/combat pole.

Talks to the BlenderMCP addon server (127.0.0.1:9876) running inside the OPEN
Blender GUI session. All scene mutations for this pole go through this client;
no batch process ever touches the open scene.

Protocol (from blender_mcp_addon.py): send one JSON object; the server parses
the whole buffer as a single command, executes it in the main thread via
bpy.app.timers and sends back one JSON response.

Usage:
  python3 mcp_client.py ping
  python3 mcp_client.py exec <code-file.py> [key=value ...]   # prints result
  python3 mcp_client.py scene                                 # get_scene_info

Inside the code file, set the variable RESULT (any JSON-serialisable value);
it is printed to stdout as JSON. @placeholders@ are NOT substituted; use
key=value args which replace literal tokens of the form %%key%%.
"""

import json
import os
import socket
import sys

HOST = "127.0.0.1"
PORT = int(os.environ.get("BAS_KIMI_MCP_PORT", "9880"))
TIMEOUT = 600.0


def send_command(cmd):
    payload = json.dumps(cmd).encode("utf-8")
    s = socket.create_connection((HOST, PORT), timeout=TIMEOUT)
    try:
        s.sendall(payload)
        buf = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
            try:
                return json.loads(buf.decode("utf-8"))
            except json.JSONDecodeError:
                continue
        raise RuntimeError("connection closed before a full JSON response arrived")
    finally:
        s.close()


def run_code(code):
    wrapped = (
        "import json as _json\n"
        "RESULT = None\n"
        + code
        + "\n___RESP___ = {'status': 'success', 'result': RESULT}\n"
    )
    # execute_code returns {'executed': True, 'result': ...} depending on addon;
    # we capture RESULT ourselves via a print-free protocol: the addon's
    # execute_code runs the code with exec() and returns nothing, so instead we
    # store RESULT on the scene as a custom property string.
    resp = send_command({"type": "execute_code", "params": {"code": code}})
    return resp


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mode = sys.argv[1]
    if mode == "ping":
        resp = send_command({"type": "get_scene_info", "params": {}})
        print(json.dumps(resp, indent=2)[:4000])
        return
    if mode == "scene":
        resp = send_command({"type": "get_scene_info", "params": {}})
        print(json.dumps(resp, indent=2))
        return
    if mode == "shot":
        # viewport screenshot -> saved to the path given as argv[2]
        path = sys.argv[2]
        resp = send_command({"type": "get_viewport_screenshot",
                             "params": {"filepath": path, "max_size": 960}})
        print(json.dumps(resp)[:2000])
        return
    if mode == "exec":
        path = sys.argv[2]
        code = open(path).read()
        for kv in sys.argv[3:]:
            k, _, v = kv.partition("=")
            code = code.replace("%%" + k + "%%", v)
        resp = run_code(code)
        print(json.dumps(resp, indent=2))
        return
    print("unknown mode", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
