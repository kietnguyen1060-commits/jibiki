"""Server chạy trên máy cho app Tra Kanji.

- Phục vụ thư mục app/ tại http://localhost:8780
- /media/<tên file> lấy âm thanh trực tiếp từ thư mục collection.media của Anki
Cách dùng: py server.py   (hoặc bấm đúp start.bat)
"""
import http.server, os, socketserver, sys, urllib.parse, webbrowser

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

PORT = 8780
HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app")


def find_media_dir():
    env = os.environ.get("ANKI_MEDIA_DIR")
    if env and os.path.isdir(env):
        return env
    root = os.path.join(os.environ.get("APPDATA", ""), "Anki2")
    if os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            d = os.path.join(root, name, "collection.media")
            if os.path.isdir(d):
                return d
    return None


MEDIA = find_media_dir()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=APP, **kw)

    def do_GET(self):
        path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        if path.startswith("/media/"):
            name = path[len("/media/"):]
            # Chỉ cho phép tên file trong đúng thư mục media, không đi ra ngoài.
            if not MEDIA or not name or "/" in name or "\\" in name or name.startswith("."):
                self.send_error(404)
                return
            full = os.path.join(MEDIA, name)
            if not os.path.isfile(full):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", self.guess_type(full))
            self.send_header("Content-Length", str(os.path.getsize(full)))
            self.send_header("Cache-Control", "max-age=86400")
            self.end_headers()
            with open(full, "rb") as fh:
                self.wfile.write(fh.read())
            return
        super().do_GET()

    def end_headers(self):
        if not self.path.startswith("/media/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, *args):
        pass


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    Handler.extensions_map.update({".js": "text/javascript; charset=utf-8", ".mp3": "audio/mpeg"})
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}/"
        print(f"Tra Kanji đang chạy tại {url}")
        print("Âm thanh Anki:", MEDIA or "không tìm thấy thư mục collection.media")
        print("Nhấn Ctrl+C để dừng.")
        if "--no-browser" not in sys.argv:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
