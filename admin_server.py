import http.server
import socketserver
import threading
import os
from pathlib import Path

ADMIN_PORT = 3334
BASE_DIR = Path(__file__).resolve().parent
ADMIN_DIR = BASE_DIR / "admin"

_server_thread = None

class AdminHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ADMIN_DIR), **kwargs)

    def translate_path(self, path):
        if path.startswith("/img/"):
            rel_path = path[5:]
            return str(BASE_DIR / "img" / rel_path)
        return super().translate_path(path)

    def log_message(self, format, *args):
        # Mute default logging to avoid terminal spam
        pass

def run_server():
    # Ensure the admin directory exists
    ADMIN_DIR.mkdir(exist_ok=True)
    
    # Optional: create a dummy index.html if empty
    index_file = ADMIN_DIR / "index.html"
    if not index_file.exists():
        index_file.write_text("<h1>Painel Administrativo</h1>")

    try:
        with socketserver.TCPServer(("", ADMIN_PORT), AdminHTTPRequestHandler) as httpd:
            print(f"[AdminServer] Serving on port {ADMIN_PORT}")
            httpd.serve_forever()
    except OSError as e:
        print(f"[AdminServer] Port {ADMIN_PORT} in use or error: {e}")

def start_admin_server() -> None:
    global _server_thread
    if _server_thread is not None and _server_thread.is_alive():
        return
    
    _server_thread = threading.Thread(target=run_server, daemon=True)
    _server_thread.start()
