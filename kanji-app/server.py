"""Server chạy trên máy cho app 字引 (Jibiki).

- Phục vụ thư mục app/ tại http://localhost:8780
- /media/<tên file> lấy âm thanh trực tiếp từ thư mục collection.media của Anki
- /api/viet (POST): nhận diện chữ viết tay qua Google Input Tools cho bảng vẽ (dự phòng: KanjiCanvas trên máy)
- /api/dich?q=…: dịch máy cả câu Nhật → Việt (gửi câu tới Google Translate) cho khung quét chữ
- /api/notes: ghi chú theo ngày, mỗi ngày một file notes/YYYY-MM-DD.md (chỉ trên máy, không đưa lên repo)
Cách dùng: py server.py   (hoặc bấm đúp start.bat)
"""
import http.server, json, os, re, socketserver, sys, urllib.parse, urllib.request, webbrowser

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
CACHE = {}  # câu đã dịch trong phiên chạy server


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

    def do_POST(self):
        """/api/viet: nhận diện chữ viết tay qua Google Input Tools. Body: {"ink": [[[x…], [y…], [t…]], …]}
        (toạ độ trên khung 300×300, t là mili giây từ lúc đặt bút nét đầu). Trả về danh sách chữ gợi ý."""
        if urllib.parse.urlparse(self.path).path != "/api/viet":
            return self.send_error(404)
        length = int(self.headers.get("Content-Length") or 0)
        if not length or length > 500_000:
            return self.send_error(400)
        try:
            ink = json.loads(self.rfile.read(length).decode("utf-8"))["ink"]
            body = {"options": "enable_pre_space", "requests": [{
                "writing_guide": {"writing_area_width": 300, "writing_area_height": 300},
                "ink": ink, "language": "ja", "max_num_results": 12, "max_completions": 0}]}
            req = urllib.request.Request("https://inputtools.google.com/request?itc=ja-t-i0-handwrit&app=translate",
                                         json.dumps(body).encode("utf-8"),
                                         {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as r:
                data = json.loads(r.read().decode("utf-8"))
            cands = data[1][0][1] if data and data[0] == "SUCCESS" else []
        except Exception as e:  # mất mạng, Google đổi API…
            return self.send_body(502, json.dumps({"error": str(e)}, ensure_ascii=False), "application/json; charset=utf-8")
        self.send_body(200, json.dumps(cands, ensure_ascii=False), "application/json; charset=utf-8")

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

    def translate(self):
        """Dịch máy cả câu (Nhật → Việt) cho khung quét chữ, qua Google Translate; có bộ nhớ đệm trong phiên."""
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("q", [""])[0].strip()[:500]
        if not q:
            return self.send_error(400)
        if q not in CACHE:
            url = ("https://translate.googleapis.com/translate_a/single?client=gtx&sl=ja&tl=vi&dt=t&q="
                   + urllib.parse.quote(q))
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=8) as r:
                    data = json.loads(r.read().decode("utf-8"))
                CACHE[q] = "".join(seg[0] for seg in data[0] if seg and seg[0])
            except Exception as e:  # mất mạng, bị chặn…
                return self.send_body(502, json.dumps({"error": str(e)}, ensure_ascii=False), "application/json; charset=utf-8")
        self.send_body(200, json.dumps({"vi": CACHE[q]}, ensure_ascii=False), "application/json; charset=utf-8")

    def do_GET(self):
        path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        if path == "/api/dich":
            return self.translate()
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
