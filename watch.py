#!/usr/bin/env python3
"""
Watch src/ for changes, rebuild automatically, serve docs/ on localhost,
and trigger a browser reload via Server-Sent Events.

Usage:
    python watch.py

Requires:
    pip install watchdog
"""

import functools
import hashlib
import http.server
import os
import queue
import subprocess
import sys
import time
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

PORT = 8000

# Always resolve paths relative to this script, regardless of cwd.
ROOT = Path(__file__).parent.resolve()
SRC  = ROOT / "src"
DOCS = ROOT / "docs"

# One-line snippet injected into HTML responses by the dev server only.
# It opens an SSE connection and reloads the page when the server says so.
_RELOAD_SNIPPET = b'<script>new EventSource("/events").onmessage=()=>location.reload()</script>'

# SSE client queues — one per open browser tab.
_sse_clients: list[queue.Queue] = []
_sse_lock = threading.Lock()


def notify_reload():
    with _sse_lock:
        for q in list(_sse_clients):
            q.put("reload")


# ── Web server ─────────────────────────────────────────────────────────────────

class DevHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/events":
            self._handle_sse()
            return

        # For HTML files: inject the reload snippet before </body>.
        fs_path = Path(self.translate_path(self.path))
        if fs_path.is_dir():
            fs_path = fs_path / "index.html"

        if fs_path.suffix == ".html" and fs_path.is_file():
            content = fs_path.read_bytes()
            content = content.replace(b"</body>", _RELOAD_SNIPPET + b"\n</body>")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        else:
            super().do_GET()

    def _handle_sse(self):
        q: queue.Queue = queue.Queue()
        with _sse_lock:
            _sse_clients.append(q)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            while True:
                try:
                    msg = q.get(timeout=25)
                    self.wfile.write(f"data: {msg}\n\n".encode())
                    self.wfile.flush()
                except queue.Empty:
                    # Keep the connection alive.
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _sse_lock:
                _sse_clients.remove(q)

    def log_message(self, *_):
        pass


# ── File watcher ───────────────────────────────────────────────────────────────

def src_hash():
    h = hashlib.md5()
    config = ROOT / "config.toml"
    if config.is_file():
        h.update(config.read_bytes())
    for f in sorted(SRC.rglob("*")):
        if f.is_file():
            h.update(f.read_bytes())
    return h.hexdigest()


class RebuildHandler(FileSystemEventHandler):
    def __init__(self, initial_hash):
        self._last_hash = initial_hash
        self._timer = None
        self._lock = threading.Lock()

    def on_any_event(self, event):
        if event.is_directory:
            return
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(0.2, self._rebuild, args=[event.src_path])
            self._timer.start()

    def _rebuild(self, path):
        current = src_hash()
        if current == self._last_hash:
            return
        self._last_hash = current
        rel = Path(path).relative_to(ROOT) if Path(path).is_absolute() else path
        print(f"Changed: {rel}  →  rebuilding…")
        subprocess.run([sys.executable, str(ROOT / "build.py")], cwd=ROOT)
        notify_reload()
        print(f"Done.")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.chdir(ROOT)

    subprocess.run([sys.executable, str(ROOT / "build.py")], cwd=ROOT)

    handler = functools.partial(DevHandler, directory=str(DOCS))
    try:
        server = http.server.ThreadingHTTPServer(("", PORT), handler)
    except OSError:
        print(f"Port {PORT} is already in use. Change PORT in watch.py.")
        sys.exit(1)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Serving  http://localhost:{PORT}")

    rebuild_handler = RebuildHandler(initial_hash=src_hash())
    observer = Observer()
    observer.schedule(rebuild_handler, path=str(SRC), recursive=True)
    observer.schedule(rebuild_handler, path=str(ROOT), recursive=False)
    observer.start()
    print("Watching src/ and config.toml — press Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    observer.stop()
    observer.join()
    server.shutdown()
