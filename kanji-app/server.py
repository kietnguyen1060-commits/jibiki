"""Server chạy trên máy cho app 字引 (Jibiki).

- Phục vụ thư mục app/ tại http://localhost:8780
- /media/<tên file> lấy âm thanh trực tiếp từ thư mục collection.media của Anki
- /api/dich?q=…: dịch cả câu Nhật → Việt cho khung quét chữ: Claude (cần API key), dự phòng Google Translate
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

# ---------- Dịch câu bằng Claude ----------
# Key: biến môi trường ANTHROPIC_API_KEY, hoặc dán key vào file claude-key.txt cạnh server.py (không đưa lên repo).
# Tuỳ chỉnh trong dich.json (không bắt buộc): {"model": "claude-opus-5-5", "effort": "low"}.
KEY_FILE = os.path.join(HERE, "claude-key.txt")
if not os.environ.get("ANTHROPIC_API_KEY") and os.path.isfile(KEY_FILE):
    _key = open(KEY_FILE, encoding="utf-8").read().strip()
    if _key:
        os.environ["ANTHROPIC_API_KEY"] = _key
try:
    import anthropic
except ImportError:  # chưa cài: py -m pip install anthropic
    anthropic = None
DICH = {"model": "claude-opus-5-5", "effort": "low"}
if os.path.isfile(os.path.join(HERE, "dich.json")):
    DICH.update(json.load(open(os.path.join(HERE, "dich.json"), encoding="utf-8")))
CLAUDE = None

SYSTEM_DICH = """Bạn là giáo viên tiếng Nhật dạy người Việt. Người học bôi đen một câu hoặc cụm từ tiếng Nhật
trong tài liệu học (giáo trình Minna no Nihongo, Kanji Look and Learn, đề luyện JLPT) và cần hiểu thật đúng nghĩa.

Trả về:
- sat: bản dịch sát nghĩa, bám từng thành phần của câu tiếng Nhật, không thêm ý, không bỏ ý; có thể hơi cứng.
  Giữ đúng thì, thể (bị động, sai khiến, khả năng…), kính ngữ / khiêm nhường ngữ và sắc thái của trợ từ, vĩ tố.
- tu_nhien: câu tiếng Việt tự nhiên, đúng như người Việt sẽ nói, cùng nghĩa với câu gốc.
- giai_thich: 0 đến 3 ghi chú rất ngắn (mỗi ghi chú dưới 25 từ, tiếng Việt) về mẫu ngữ pháp, trợ từ hay sắc thái
  quyết định nghĩa của câu, ví dụ "～てしまいました: lỡ làm, tiếc nuối". Câu đơn giản thì để mảng rỗng.
Nếu đoạn bôi đen không trọn câu (một cụm từ, một vế), dịch đúng phần đó, không đoán thêm phần còn thiếu."""

SCHEMA_DICH = {
    "type": "object",
    "properties": {
        "sat": {"type": "string"},
        "tu_nhien": {"type": "string"},
        "giai_thich": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["sat", "tu_nhien", "giai_thich"],
    "additionalProperties": False,
}


def dich_claude(q):
    """→ (kết quả, lý do không dùng được). Kết quả: {"vi", "sat", "giai_thich", "nguon": "claude"}."""
    global CLAUDE
    if anthropic is None:
        return None, "chưa cài thư viện anthropic"
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None, "chưa có API key của Claude"
    if CLAUDE is None:
        CLAUDE = anthropic.Anthropic(timeout=40.0)
    try:
        # fallbacks="default": nếu bộ lọc an toàn từ chối, API tự chạy lại trên model dự phòng Anthropic khuyến nghị.
        r = CLAUDE.beta.messages.create(
            model=DICH["model"],
            max_tokens=4000,
            system=SYSTEM_DICH,
            output_config={"effort": DICH["effort"], "format": {"type": "json_schema", "schema": SCHEMA_DICH}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": q}],
        )
    except anthropic.AuthenticationError:
        return None, "API key của Claude không hợp lệ"
    except anthropic.PermissionDeniedError:
        return None, "API key không có quyền dùng model này"
    except anthropic.RateLimitError:
        return None, "Claude đang giới hạn tốc độ, thử lại sau"
    except anthropic.APIStatusError as e:
        return None, f"Claude báo lỗi {e.status_code}"
    except anthropic.APIConnectionError:
        return None, "không kết nối được Claude"
    if r.stop_reason == "refusal":
        return None, "Claude từ chối dịch câu này"
    text = next((b.text for b in r.content if b.type == "text"), "")
    try:
        d = json.loads(text)
    except ValueError:
        return None, "Claude trả về dữ liệu không đọc được"
    return {"vi": d["tu_nhien"], "sat": d["sat"], "giai_thich": d["giai_thich"][:3], "nguon": "claude"}, ""


def dich_google(q):
    url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=ja&tl=vi&dt=t&q=" + urllib.parse.quote(q)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=8) as r:
        data = json.loads(r.read().decode("utf-8"))
    return "".join(seg[0] for seg in data[0] if seg and seg[0])


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

    def translate(self):
        """Dịch cả câu Nhật → Việt cho khung quét chữ: Claude trước (sát nghĩa + tự nhiên + giải thích),
        Google Translate dự phòng khi chưa có key, mất mạng hoặc Claude từ chối. Có bộ nhớ đệm trong phiên."""
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("q", [""])[0].strip()[:500]
        if not q:
            return self.send_error(400)
        if q not in CACHE:
            res, why = dich_claude(q)
            if not res:
                try:
                    res = {"vi": dich_google(q), "nguon": "google", "ly_do": why}
                except Exception as e:  # mất mạng, bị chặn…
                    return self.send_body(502, json.dumps({"error": str(e), "ly_do": why}, ensure_ascii=False), "application/json; charset=utf-8")
            CACHE[q] = res
        self.send_body(200, json.dumps(CACHE[q], ensure_ascii=False), "application/json; charset=utf-8")

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
