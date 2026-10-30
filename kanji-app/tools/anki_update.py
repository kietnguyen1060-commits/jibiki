"""Đưa hình thành phần / thứ tự nét và các kanji bổ sung vào Anki qua AnkiConnect.

Cách dùng: py anki_update.py <bước...>
  backup <thư mục>   sao lưu collection.anki2 (dùng sqlite backup, an toàn khi Anki đang mở)
  fields             thêm trường "Hình" và "Nét viết" vào kiểu ghi chú KLL
  media              tải mọi kll_*.svg trong _build/media vào thư mục media của Anki
  media_tranh        chỉ tải tranh kll_pic_*.svg (sau khi chạy make_tranh.py)
  media_sach         tải tranh cắt từ sách kll_book_*.png (sau khi chạy cat_tranh_sach.py)
  media_n3, media_n3_hinh  tải tranh sách N3–N2 và hình thành phần/nét của chữ mới
  n3n2               thêm chữ của sách N3–N2 (sau khi chạy doc_n3n2.py)
  sua_the            áp các sửa đổi trong tools/sua_the.txt
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


SACH = os.path.join(ROOT, "_build", "sach")  # tranh cắt từ PDF sách của người học (cat_tranh_sach.py), không đưa lên repo
N3 = os.path.join(ROOT, "_build", "n3n2")    # dữ liệu + tranh sách N3–N2 tiếng Việt (doc_n3n2.py), không đưa lên repo
MEDIA_N3 = os.path.join(ROOT, "_build", "media_n3")  # hình thành phần / nét cho chữ mới của sách N3–N2
DECK_N3 = "Kanji Look and Learn::5. N3–N2 (sách tiếng Việt)::Phần {:02d}"


def img_fields(ch):
    # Tranh ở trên (sách KLL → sách N3–N2 → tranh OpenMoji), hình thành phần màu ở dưới.
    cp = f"{ord(ch):05x}"
    pic = next((f for d, f in ((SACH, f"kll_book_{cp}.png"), (N3, f"kll_n3_{cp}.png")) if os.path.exists(os.path.join(d, f))),
               f"kll_pic_{cp}.svg")
    return {"Hình": f'<img src="{pic}"><img src="kll_comp_{cp}.svg">', "Nét viết": f'<img src="kll_stroke_{cp}.svg">'}


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


def media(pattern="kll_*.svg", folder=MEDIA):
    files = sorted(glob.glob(os.path.join(folder, pattern)))
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


def n3n2():
    """Thêm các chữ của sách "Kanji Look and Learn N3 N2 (tiếng Việt)" (đọc bằng doc_n3n2.py).

    Chữ chưa có → ghi chú mới (số N3·n, deck theo phần 20 chữ của sách). Chữ bổ sung từ Minna đã có
    → lấy câu gợi nhớ và Hán Việt của sách. Chữ trong KLL giữ nguyên."""
    book = json.load(open(os.path.join(N3, "n3n2.json"), encoding="utf-8"))
    labels = json.load(open(os.path.join(MEDIA_N3, "_labels.json"), encoding="utf-8"))
    kd = {}
    xml = gzip.open(os.path.join(ROOT, "_dl", "kanjidic", "kanjidic2.xml.gz"), "rt", encoding="utf-8").read()
    for m in re.finditer(r"<character>(.*?)</character>", xml, re.S):
        b = m.group(1)
        kd[re.search(r"<literal>(.)</literal>", b).group(1)] = (
            [kana_h(x) for x in re.findall(r'<reading r_type="ja_on">([^<]+)</reading>', b)],
            [re.sub(r"\..*", "", x).strip("-") for x in re.findall(r'<reading r_type="ja_kun">([^<]+)</reading>', b)],
            re.search(r"<stroke_count>(\d+)</stroke_count>", b).group(1))
    have = {n["fields"]["Kanji"]["value"]: n for n in call("notesInfo", notes=call("findNotes", query=f'"note:{MODEL}"'))}
    notes, decks, upd = [], set(), []
    for e in book:
        k = e["k"]
        on_kd, kun_kd, net = kd.get(k, ([], [], ""))
        if k in have:
            f = have[k]["fields"]
            if f["Số"]["value"].startswith("+"):
                new = {"Cách nhớ": e["nho"]} if e["nho"] else {}
                if e["hv"] and e["hv"].split(",")[0].strip() != f["Hán Việt"]["value"]:
                    new["Hán Việt"] = e["hv"]
                if new:
                    upd.append({"action": "updateNoteFields", "params": {"note": {"id": have[k]["noteId"], "fields": new}}})
                upd.append({"action": "addTags", "params": {"notes": [have[k]["noteId"]], "tags": "KLL_N3N2"}})
            continue
        # Âm on của sách có khi lẫn lỗi OCR: chỉ giữ âm có trong KANJIDIC2.
        on = [r for r in uniq(x for s in e["on"] for x in s.split()) if r in on_kd] or on_kd[:3]
        kun = uniq(re.sub(r"\..*", "", x).strip("-") for x in e["kun"]) or kun_kd[:3]
        ex = "".join(f'<tr><td class="{"core" if j < 2 else ""}">{html.escape(w[0])}</td><td>{html.escape(w[1])}</td><td>{html.escape(w[3])}</td></tr>'
                     for j, w in enumerate(e["tu"][:10]))
        part = (e["n"] - 1) // 20 + 1
        deck = DECK_N3.format(part)
        decks.add(deck)
        f = {"Số": f"N3·{e['n']}", "Kanji": k, "Nghĩa": e["nghia"], "Hán Việt": e["hv"],
             "Onyomi": "、".join(on[:4]), "Kunyomi": "、".join(kun[:4]), "Số nét": net, "Cách nhớ": e["nho"],
             "Liên quan": "Liên quan: " + "、".join(uniq(labels.get(k, []))) if labels.get(k) else "",
             "Từ ví dụ": f'<table class="ex">{ex}</table>' if ex else "", "Bài": f"N3–N2 phần {part}"}
        f.update(img_fields(k))
        notes.append({"deckName": deck, "modelName": MODEL, "fields": f, "tags": ["KLL_N3N2", f"N3N2_Phan{part:02d}"],
                      "options": {"allowDuplicate": False}})
    if upd:
        multi(upd)
    for d in sorted(decks):
        call("createDeck", deck=d)
    if decks:
        call("setDeckConfigId", decks=sorted(decks) + [DECK_N3.split("::Phần")[0]], configId=PRESET)
    ids = call("addNotes", notes=notes) if notes else []
    print("đã thêm", len([i for i in ids if i]), "ghi chú mới; cập nhật", sum(1 for a in upd if a["action"] == "updateNoteFields"),
          "chữ bổ sung; lỗi:", "".join(n["fields"]["Kanji"] for n, i in zip(notes, ids) if not i))
    rev = call("findCards", query="tag:KLL_N3N2 card:2 -is:suspended")
    if rev:
        call("suspend", cards=rev)
    print("tạm ngưng", len(rev), "thẻ Nghĩa → Kanji")


def sua_the():
    """Áp các sửa đổi ghi trong tools/sua_the.txt (chữ|trường|giá trị) lên ghi chú kanji tương ứng."""
    rows = [l.rstrip("\n").split("|", 2) for l in open(os.path.join(HERE, "sua_the.txt"), encoding="utf-8")
            if l.strip() and not l.startswith("#")]
    have = {n["fields"]["Kanji"]["value"]: n["noteId"] for n in call("notesInfo", notes=call("findNotes", query=f'"note:{MODEL}"'))}
    acts = [{"action": "updateNoteFields", "params": {"note": {"id": have[k], "fields": {f: v}}}} for k, f, v in rows if k in have]
    multi(acts)
    print("đã sửa", len(acts), "/", len(rows), "mục; không tìm thấy chữ:", "".join(k for k, _, _ in rows if k not in have))


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
.pg-k{font-size:84px;line-height:1.05;font-family:"Yu Mincho","MS Mincho",serif}
.pg-mean{font-size:20px;font-weight:bold}
.pg-img{flex:1;display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:6px}.pg-img img{display:block;max-width:100%;max-height:130px;width:auto;height:auto;object-fit:contain}
.pg-mid{padding:8px 12px;border-bottom:1px solid #999;font-size:18px}
.pg-nho:before{content:"💡 "}.pg-lq{font-size:15px;color:#777;margin-top:4px}
.pg-bot{display:flex;flex-wrap:wrap}
.pg-reads{flex:0 0 200px;padding:8px 12px;border-right:1px solid #999;font-size:18px}
.pg-tag{display:inline-block;width:22px;text-align:center;border:1px solid #333;border-radius:3px;font-size:14px}
.pg-kun{background:#333;color:#fff}
.pg-ex{flex:1;min-width:260px}.pg-ex table.ex{margin:0;width:100%}
.pg-ex td.core{background:#e3e3e3}
.pg-strokes{border-top:1px solid #999;padding:6px;text-align:center}.pg-strokes img{max-width:100%;max-height:44px;height:auto}
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
        media("kll_pic_*.svg") if step == "media_tranh" else media("kll_book_*.png", SACH) if step == "media_sach" else media("kll_n3_*.png", N3) if step == "media_n3" else media("kll_*.svg", MEDIA_N3) if step == "media_n3_hinh" else globals()[step]()
