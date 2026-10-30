"""Đưa hình thành phần / thứ tự nét và các kanji bổ sung vào Anki qua AnkiConnect.

Cách dùng: py anki_update.py <bước...>
  backup <thư mục>   sao lưu collection.anki2 (dùng sqlite backup, an toàn khi Anki đang mở)
  fields             thêm trường "Hình" và "Nét viết" vào kiểu ghi chú KLL
  media              tải mọi kll_*.svg trong _build/media vào thư mục media của Anki
  fill               điền 2 trường hình cho các ghi chú KLL đã có
  extra              thêm các kanji Minna không có trong KLL (đọc tools/extra_vi_*.txt)
  template           đổi mặt sau thẻ thành bố cục giống trang sách
"""
import glob, gzip, html, json, os, re, sqlite3, sys, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
MEDIA = os.path.join(ROOT, "_build", "media")
MODEL = "Kanji Look and Learn - Kanji (VN)"
PRESET = 1789638944497  # "KLL --Bài con": học hết bài, giống các bài KLL khác
DECK = "Kanji Look and Learn::4. Bổ sung từ Minna::Bài {:02d}"


def call(action, **params):
    req = urllib.request.Request("http://127.0.0.1:8765", json.dumps({"action": action, "version": 6, "params": params}).encode())
    res = json.loads(urllib.request.urlopen(req, timeout=600).read())
    if res.get("error"):
        raise RuntimeError(f"{action}: {res['error']}")
    return res["result"]


def multi(actions, size=200):
    out = []
    for i in range(0, len(actions), size):
        for r in call("multi", actions=actions[i:i + size]):
            if isinstance(r, dict) and r.get("error"):
                raise RuntimeError(r["error"])
            out.append(r.get("result") if isinstance(r, dict) else r)
    return out


def img_fields(ch):
    cp = f"{ord(ch):05x}"
    return {"Hình": f'<img src="kll_comp_{cp}.svg">', "Nét viết": f'<img src="kll_stroke_{cp}.svg">'}


def backup(dest):
    src = os.path.join(os.environ["APPDATA"], "Anki2", "Người dùng 1", "collection.anki2")
    os.makedirs(dest, exist_ok=True)
    out = os.path.join(dest, "collection-truoc-khi-them-hinh.anki2")
    s = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    d = sqlite3.connect(out)
    s.backup(d)
    d.close(), s.close()
    print("đã sao lưu:", out, os.path.getsize(out), "byte")


def fields():
    have = call("modelFieldNames", modelName=MODEL)
    for name in ("Hình", "Nét viết"):
        if name not in have:
            call("modelFieldAdd", modelName=MODEL, fieldName=name, index=len(have))
            have.append(name)
    print("trường:", have)


def media():
    files = sorted(glob.glob(os.path.join(MEDIA, "kll_*.svg")))
    multi([{"action": "storeMediaFile", "params": {"filename": os.path.basename(f), "path": os.path.abspath(f)}} for f in files], 100)
    print("đã lưu", len(files), "tệp")


def fill():
    ids = call("findNotes", query=f'"note:{MODEL}"')
    info = call("notesInfo", notes=ids)
    acts = [{"action": "updateNoteFields", "params": {"note": {"id": n["noteId"], "fields": img_fields(n["fields"]["Kanji"]["value"])}}}
            for n in info if os.path.exists(os.path.join(MEDIA, f"kll_comp_{ord(n['fields']['Kanji']['value'][0]):05x}.svg"))]
    multi(acts)
    print("đã điền hình cho", len(acts), "/", len(info), "ghi chú")


def kana_h(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def uniq(xs):
    return list(dict.fromkeys(x for x in xs if x))


def extra():
    rows = {}
    for p in sorted(glob.glob(os.path.join(HERE, "extra_vi_*.txt"))):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#"):
                k, hv, nghia, nho = line.split("|", 3)
                rows[k] = (hv, nghia, nho)
    src = {r["k"]: r for r in json.load(open(os.path.join(HERE, "extra_source.json"), encoding="utf-8"))}
    labels = json.load(open(os.path.join(MEDIA, "_labels.json"), encoding="utf-8"))
    app = open(os.path.join(ROOT, "app", "data", "app-data.js"), encoding="utf-8").read()
    data = json.loads(app[app.index("=") + 1:app.rindex(";")])
    kll = {x["k"] for x in data["kll"]}

    # Âm đọc đầy đủ từ KANJIDIC2 (extra_source chỉ giữ vài âm đầu).
    kd = {}
    xml = gzip.open(os.path.join(ROOT, "_dl", "kanjidic", "kanjidic2.xml.gz"), "rt", encoding="utf-8").read()
    for m in re.finditer(r"<character>(.*?)</character>", xml, re.S):
        b = m.group(1)
        c = re.search(r"<literal>(.)</literal>", b).group(1)
        if c in rows:
            kd[c] = (re.findall(r'<reading r_type="ja_on">([^<]+)</reading>', b), re.findall(r'<reading r_type="ja_kun">([^<]+)</reading>', b))

    # Từ Minna chứa chữ, theo thứ tự bài; từ đầu tiên là "từ cần nhớ" như ô tô xám trong sách.
    words = {}
    for w in sorted(data["minna"], key=lambda w: w[3]):
        for c in set(w[0]):
            if c in rows and len(words.setdefault(c, [])) < 6 and w[0] not in [x[0] for x in words[c]]:
                words[c].append(w)

    have = {n["fields"]["Kanji"]["value"] for n in call("notesInfo", notes=call("findNotes", query=f'"note:{MODEL}"'))}
    order = sorted((src[k]["bai"], k) for k in rows if k not in kll)
    notes, decks = [], set()
    for i, (bai, k) in enumerate(order, 1):
        if k in have:
            continue
        hv, nghia, nho = rows[k]
        on, kun = kd.get(k, ([], []))
        ex = "".join(f'<tr><td class="{"core" if j == 0 else ""}">{html.escape(w[0])}</td><td>{html.escape(w[1])}</td><td>{html.escape(w[2])}</td></tr>'
                     for j, w in enumerate(words.get(k, [])))
        deck = DECK.format(bai)
        decks.add(deck)
        f = {"Số": f"+{i}", "Kanji": k, "Nghĩa": nghia, "Hán Việt": hv,
             "Onyomi": "、".join(uniq(kana_h(x) for x in on)[:4]),
             "Kunyomi": "、".join(uniq(re.sub(r"\..*", "", x).strip("-") for x in kun)[:4]),
             "Số nét": str(src[k]["net"]), "Cách nhớ": nho,
             "Liên quan": "Liên quan: " + "、".join(uniq(labels.get(k, []))) if labels.get(k) else "",
             "Từ ví dụ": f'<table class="ex">{ex}</table>' if ex else "", "Bài": f"Minna {bai}"}
        f.update(img_fields(k))
        notes.append({"deckName": deck, "modelName": MODEL, "fields": f, "tags": ["KLL_BoSung", f"Minna_Bai{bai:02d}"],
                      "options": {"allowDuplicate": False}})
    for d in sorted(decks):
        call("createDeck", deck=d)
    if decks:
        call("setDeckConfigId", decks=sorted(decks) + [DECK.split("::Bài")[0]], configId=PRESET)
    ids = call("addNotes", notes=notes) if notes else []
    bad = [n["fields"]["Kanji"] for n, i in zip(notes, ids) if not i]
    print("đã thêm", len([i for i in ids if i]), "ghi chú; lỗi:", "".join(bad))
    # Như các thẻ KLL sẵn có: tạm ngưng chiều "Nghĩa → Kanji".
    rev = call("findCards", query='tag:KLL_BoSung card:2')
    if rev:
        call("suspend", cards=rev)
    print("tạm ngưng", len(rev), "thẻ Nghĩa → Kanji")


FRONT = '<div class="small">#{{Số}} · Bài {{Bài}}</div><div class="kanji">{{Kanji}}</div>'
BACK = """<div id="answer"></div>
<div class="pg">
  <div class="pg-top">
    <div class="pg-head">
      <div class="pg-no">{{Số}}</div>
      <div class="pg-k">{{Kanji}}</div>
      <div class="pg-mean">{{Nghĩa}}</div>
      <div class="hv">{{Hán Việt}}</div>
    </div>
    <div class="pg-img">{{Hình}}</div>
  </div>
  <div class="pg-mid">
    <div class="pg-nho">{{Cách nhớ}}</div>
    {{#Liên quan}}<div class="pg-lq">{{Liên quan}}</div>{{/Liên quan}}
  </div>
  <div class="pg-bot">
    <div class="pg-reads">
      <div><span class="pg-tag">音</span> <span class="kana">{{Onyomi}}</span></div>
      <div><span class="pg-tag pg-kun">訓</span> <span class="kana">{{Kunyomi}}</span></div>
      <div class="small">{{Số nét}} nét · Bài {{Bài}}</div>
    </div>
    <div class="pg-ex">{{Từ ví dụ}}</div>
  </div>
  {{#Nét viết}}<div class="pg-strokes">{{Nét viết}}</div>{{/Nét viết}}
</div>"""
BACK2 = """{{FrontSide}}<hr id=answer><div class="kanji">{{Kanji}}</div>
{{#Hình}}<div class="pg-img">{{Hình}}</div>{{/Hình}}
<div>音: <span class="kana">{{Onyomi}}</span> · 訓: <span class="kana">{{Kunyomi}}</span></div>{{Từ ví dụ}}
{{#Nét viết}}<div class="pg-strokes">{{Nét viết}}</div>{{/Nét viết}}"""
CSS = """
/* Bố cục trang sách (thêm bởi tra-kanji) */
.pg{max-width:760px;margin:0 auto;text-align:left;border:2px solid #333;border-radius:6px;background:#fff;color:#222;overflow:hidden}
.pg-top{display:flex;align-items:center;gap:8px;border-bottom:1px solid #999;padding:8px}
.pg-head{flex:0 0 auto;min-width:130px;text-align:center}
.pg-no{display:inline-block;font-size:14px;background:#333;color:#fff;border-radius:3px;padding:0 6px}
.pg-k{font-size:96px;line-height:1.05;font-family:"Yu Mincho","MS Mincho",serif}
.pg-mean{font-size:20px;font-weight:bold}
.pg-img{flex:1;text-align:center}.pg-img img{max-width:100%;height:auto}
.pg-mid{padding:8px 12px;border-bottom:1px solid #999;font-size:18px}
.pg-nho:before{content:"💡 "}.pg-lq{font-size:15px;color:#777;margin-top:4px}
.pg-bot{display:flex;flex-wrap:wrap}
.pg-reads{flex:0 0 200px;padding:8px 12px;border-right:1px solid #999;font-size:18px}
.pg-tag{display:inline-block;width:22px;text-align:center;border:1px solid #333;border-radius:3px;font-size:14px}
.pg-kun{background:#333;color:#fff}
.pg-ex{flex:1;min-width:260px}.pg-ex table.ex{margin:0;width:100%}
.pg-ex td.core{background:#e3e3e3}
.pg-strokes{border-top:1px solid #999;padding:6px;text-align:center}.pg-strokes img{max-width:100%;height:auto}
@media (max-width:520px){.pg-top{flex-direction:column}.pg-reads{flex-basis:100%;border-right:0;border-bottom:1px solid #999}}
.nightMode .pg,.night_mode .pg{background:#262626;color:#eee;border-color:#888}
.nightMode .pg-ex td.core,.night_mode .pg-ex td.core{background:#3a3a3a}
.nightMode .pg-kun,.night_mode .pg-kun,.nightMode .pg-no,.night_mode .pg-no{background:#ddd;color:#111}
.nightMode .pg-tag,.night_mode .pg-tag{border-color:#ddd}
"""


def template():
    call("updateModelTemplates", model={"name": MODEL, "templates": {
        "Kanji → Nghĩa/Âm": {"Front": FRONT, "Back": BACK},
        "Nghĩa → Kanji": {"Front": call("modelTemplates", modelName=MODEL)["Nghĩa → Kanji"]["Front"], "Back": BACK2}}})
    css = call("modelStyling", modelName=MODEL)["css"]
    css = css.split("\n/* Bố cục trang sách")[0] + CSS
    call("updateModelStyling", model={"name": MODEL, "css": css})
    print("đã cập nhật mẫu thẻ")


args = sys.argv[1:]
while args:
    step = args.pop(0)
    if step == "backup":
        backup(args.pop(0))
    else:
        globals()[step]()
