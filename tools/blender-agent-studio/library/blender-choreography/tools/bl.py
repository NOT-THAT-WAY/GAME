#!/usr/bin/env python3
"""Client Blender MCP addon (port 9876). Usage: bl.py <code.py> | bl.py --shot <out.png>"""
import socket, json, sys

def cmd(t, p=None, timeout=60):
    s = socket.create_connection(("localhost", 9876), timeout=timeout)
    s.sendall(json.dumps({"type": t, "params": p or {}}).encode())
    buf = b""
    while True:
        try:
            c = s.recv(65536)
        except socket.timeout:
            break
        if not c:
            break
        buf += c
        try:
            json.loads(buf.decode())
            break
        except Exception:
            continue
    return json.loads(buf.decode())

if __name__ == "__main__":
    if sys.argv[1] == "--shot":
        r = cmd("get_viewport_screenshot", {"max_size": 1200, "filepath": sys.argv[2], "format": "png"})
        print(json.dumps(r)[:300])
    else:
        code = open(sys.argv[1]).read()
        r = cmd("execute_code", {"code": code})
        if r.get("status") == "success":
            print(r["result"].get("result", ""))
        else:
            print("ERROR:", json.dumps(r)[:2000])
