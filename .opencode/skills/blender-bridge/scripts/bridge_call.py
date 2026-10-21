# -*- coding: utf-8 -*-
"""Send Python code to a running Blender bridge and print the response.

Usage:
    python bridge_call.py <code_file.py>
    python bridge_call.py -c "print(bpy.app.version_string)"

Environment:
    BLENDER_BRIDGE_HOST  default 127.0.0.1
    BLENDER_BRIDGE_PORT  default 9878
"""

import json
import os
import socket
import sys

HOST = os.environ.get("BLENDER_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("BLENDER_BRIDGE_PORT", "9878"))


def call(code, timeout=60):
    client = socket.create_connection((HOST, PORT), timeout=10)
    client.settimeout(timeout)
    client.sendall((json.dumps({"code": code}) + "\0").encode("utf-8"))

    buffer = b""
    while b"\0" not in buffer:
        chunk = client.recv(65536)
        if not chunk:
            break
        buffer += chunk
    client.close()

    raw = buffer.split(b"\0", 1)[0]
    if not raw:
        raise RuntimeError("No response from Blender bridge")
    return json.loads(raw.decode("utf-8"))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    if sys.argv[1] == "-c":
        code = " ".join(sys.argv[2:])
    else:
        with open(sys.argv[1], encoding="utf-8") as handle:
            code = handle.read()

    payload = call(code)
    print("OK:", payload.get("ok"))
    stdout = payload.get("stdout", "")
    if stdout:
        print("--- STDOUT ---")
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    error = payload.get("error", "")
    if error:
        print("--- ERRORE ---")
        print(error)
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
