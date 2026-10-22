# -*- coding: utf-8 -*-
"""Local TCP bridge for Blender.

The bridge executes Python code in Blender's main thread. It works in both
modes:

* ``blender --background --python blender_bridge.py``: blocking server loop.
* ``blender --factory-startup --python blender_bridge.py``: GUI mode, where a
  timer executes queued requests in the main thread.

Protocol: JSON messages terminated by a NUL byte (``\\0``).
"""

import contextlib
import io
import json
import os
import queue
import socket
import threading
import traceback

import bpy

HOST = os.environ.get("BLENDER_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("BLENDER_BRIDGE_PORT", "9878"))

# Lo splash all'avvio coprirebbe la sidebar nelle catture: lo disattiviamo subito
# (vale solo per l'istanza di test, che gira con --factory-startup).
try:
    bpy.context.preferences.view.show_splash = False
except Exception:
    pass

_requests = queue.Queue()


def _execute(code):
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            exec(
                compile(code, "<bridge>", "exec"),
                {"bpy": bpy, "__name__": "__bridge__"},
            )
        return {"ok": True, "stdout": output.getvalue()}
    except Exception:
        return {
            "ok": False,
            "stdout": output.getvalue(),
            "error": traceback.format_exc(),
        }


def _send(conn, payload):
    try:
        conn.sendall((json.dumps(payload) + "\0").encode("utf-8"))
    except Exception:
        pass


def _messages(conn):
    buffer = b""
    while True:
        data = conn.recv(65536)
        if not data:
            return
        buffer += data
        while b"\0" in buffer:
            raw, buffer = buffer.split(b"\0", 1)
            try:
                yield json.loads(raw.decode("utf-8"))
            except Exception as exc:
                yield {"code": f"raise RuntimeError({str(exc)!r})"}


def _serve_blocking(conn):
    """Serve one connection in the current (main) thread."""
    try:
        for request in _messages(conn):
            _send(conn, _execute(request.get("code", "")))
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _serve_queued(conn):
    """Serve one connection from a worker thread (GUI mode)."""
    try:
        for request in _messages(conn):
            _requests.put((conn, request))
    except Exception:
        pass


def _make_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    return server


def _background_loop():
    server = _make_server()
    print(f"BRIDGE_LISTENING {HOST}:{PORT}", flush=True)
    print("BRIDGE_MODE background", flush=True)
    while True:
        conn, _addr = server.accept()
        _serve_blocking(conn)


def _timer():
    while True:
        try:
            conn, request = _requests.get_nowait()
        except queue.Empty:
            break
        _send(conn, _execute(request.get("code", "")))
    return 0.05


def _gui_loop():
    server = _make_server()
    print(f"BRIDGE_LISTENING {HOST}:{PORT}", flush=True)
    print("BRIDGE_MODE gui", flush=True)

    def accept_loop():
        while True:
            conn, _addr = server.accept()
            threading.Thread(
                target=_serve_queued, args=(conn,), daemon=True
            ).start()

    threading.Thread(target=accept_loop, daemon=True).start()
    bpy.app.timers.register(_timer, first_interval=0.1, persistent=True)


if bpy.app.background:
    _background_loop()
else:
    _gui_loop()
