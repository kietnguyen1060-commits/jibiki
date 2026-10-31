"""Server chạy trên máy cho app 字引 (Jibiki).

- Phục vụ thư mục app/ tại http://localhost:8780
- /media/<tên file> lấy âm thanh trực tiếp từ thư mục collection.media của Anki
- /api/notes: ghi chú theo ngày, mỗi ngày một file notes/YYYY-MM-DD.md (chỉ trên máy, không đưa lên repo)
Cách dùng: py server.py   (hoặc bấm đúp start.bat)
"""
import http.server, json, os, re, socketserver, sys, urllib.parse, webbrowser

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
NOTES = os.path.join(HERE, "notes")
DAY = re.compile(r"^/api/notes/(\d{4}-\d{2}-\d{2})$")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=APP, **kw)

    def send_body(self, code, body, ctype):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def notes_get(self, path):
        if path == "/api/notes":
            # Danh sách ngày có ghi chú, mới nhất trước, kèm vài chữ đầu để xem nhanh.
            items = []
            if os.path.isdir(NOTES):
                for name in sorted(os.listdir(NOTES), reverse=True):
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.md", name):
                        text = open(os.path.join(NOTES, name), encoding="utf-8").read()
                        items.append({"date": name[:10], "text": text})
            return self.send_body(200, json.dumps(items, ensure_ascii=False), "application/json; charset=utf-8")
        m = DAY.match(path)
        if not m:
            return self.send_error(404)
        full = os.path.join(NOTES, m.group(1) + ".md")
        text = open(full, encoding="utf-8").read() if os.path.isfile(full) else ""
        self.send_body(200, text, "text/plain; charset=utf-8")

    def do_PUT(self):
        # Chỉ nhận PUT từ chính app (trình duyệt chặn PUT khác nguồn vì server không trả CORS).
        m = DAY.match(urllib.parse.urlparse(self.path).path)
        length = int(self.headers.get("Content-Length") or 0)
        if not m or length > 2_000_000:
            return self.send_error(400)
        text = self.rfile.read(length).decode("utf-8")
        full = os.path.join(NOTES, m.group(1) + ".md")
        if text.strip():
            os.makedirs(NOTES, exist_ok=True)
            with open(full, "w", encoding="utf-8") as fh:
                fh.write(text)
        elif os.path.isfile(full):
            os.remove(full)  # ghi chú trống thì bỏ file của ngày đó
        self.send_body(200, "ok", "text/plain; charset=utf-8")

    def do_GET(self):
        path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        if path.startswith("/api/notes"):
            return self.notes_get(path)
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
        print(f"字引 Jibiki đang chạy tại {url}")
        print("Âm thanh Anki:", MEDIA or "không tìm thấy thư mục collection.media")
        print("Nhấn Ctrl+C để dừng.")
        if "--no-browser" not in sys.argv:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
