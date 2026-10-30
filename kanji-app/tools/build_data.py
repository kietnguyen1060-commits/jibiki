"""Trích dữ liệu cho app tra kanji từ bộ sưu tập Anki (bản sao) và KanjiVG.

Cách dùng: py build_data.py <collection.anki2> <kanjivg.xml.gz> <ref-patterns.js>
Ghi ra ../app/data/app-data.js và ../app/data/strokes.js
"""
import gzip, html, json, os, re, sqlite3, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "app", "data")
col_path, kvg_path, ref_path = sys.argv[1:4]

# Mã kiểu ghi chú trong bộ sưu tập của người học.
MID = {"kll": 1760100002, "kllw": 1760100003, "klls": 1760100004, "minna1": 1607392319, "minna2": 1760100001}

con = sqlite3.connect(col_path)
con.create_collation("unicase", lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower()))


def notes(mid):
    return [(nid, flds.split("\x1f")) for nid, flds in con.execute("select id, flds from notes where mid=? order by id", (mid,))]


def sound(s):
    m = re.search(r"\[sound:([^\]]+)\]", s or "")
    return m.group(1) if m else ""


def ex_rows(table):
    """Bảng ví dụ KLL → [[từ, cách đọc, nghĩa, là từ cần nhớ]]."""
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", table, re.S):
        tds = re.findall(r'<td(?: class="([^"]*)")?>(.*?)</td>', tr, re.S)
        if len(tds) >= 3:
            rows.append([html.unescape(re.sub("<[^>]+>", "", tds[i][1])).strip() for i in range(3)] + [1 if tds[0][0] == "core" else 0])
    return rows


kll = []
for nid, f in notes(MID["kll"]):
    # Chữ bổ sung từ Minna có số "+N" → 1000 + N, chữ sách N3–N2 có số "N3·N" → 2000 + N,
    # để vẫn sắp xếp và lật trang được.
    num = 1000 + int(f[0][1:]) if f[0].startswith("+") else 2000 + int(f[0][3:]) if f[0].startswith("N3·") else int(f[0])
    img = re.search(r'src="([^"]+)"', f[11]) if len(f) > 11 else None
    kll.append({"n": num, "img": img.group(1) if img else "", "k": f[1], "nghia": f[2], "hv": f[3], "on": f[4], "kun": f[5], "net": f[6],
                "nho": f[7], "lq": re.sub(r"^Liên quan:\s*", "", f[8]), "ex": ex_rows(f[9]), "bai": f[10], "nid": nid})
kll.sort(key=lambda x: x["n"])

words = []
for nid, f in notes(MID["kllw"]):
    words.append([f[1], f[2], f[3], f[4], f[5], f[6], f[7], sound(f[8]), nid])

sents = []
for nid, f in notes(MID["klls"]):
    sents.append([f[1], f[2], f[3], f[4], f[5], sound(f[6]), sound(f[7]), nid])

minna = []
for nid, f in notes(MID["minna1"]):
    minna.append([f[1], f[0], f[2], int(f[3]), nid])
for nid, f in notes(MID["minna2"]):
    minna.append([f[2], f[1], f[3], int(f[7]), nid])

# Danh sách chữ KanjiCanvas nhận diện được.
ref = open(ref_path, encoding="utf-8").read()
recog = set(re.findall(r'\["(.)",\s*\d+,', ref))

# Nét viết KanjiVG: chỉ giữ chữ nhận diện được, chữ KLL và chữ có trong từ vựng.
need = recog | {x["k"] for x in kll} | {c for w in minna for c in w[0] if "一" <= c <= "鿿"}
strokes = {}
xml = gzip.open(kvg_path, "rt", encoding="utf-8").read()
for block in re.finditer(r'<kanji id="kvg:kanji_([0-9a-f]+)">(.*?)</kanji>', xml, re.S):
    ch = chr(int(block.group(1), 16))
    if ch not in need:
        continue
    paths = re.findall(r'<path id="kvg:[0-9a-f]+(?:-[^"]*)?-s(\d+)"[^>]*\sd="([^"]+)"', block.group(2))
    paths.sort(key=lambda p: int(p[0]))
    strokes[ch] = [d for _, d in paths]

os.makedirs(OUT, exist_ok=True)
data = {"kll": kll, "words": words, "sents": sents, "minna": minna, "recog": "".join(sorted(recog))}
with open(os.path.join(OUT, "app-data.js"), "w", encoding="utf-8") as fh:
    fh.write("window.APPDATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")
with open(os.path.join(OUT, "strokes.js"), "w", encoding="utf-8") as fh:
    fh.write("/* Dữ liệu nét viết từ KanjiVG (http://kanjivg.tagaini.net), Ulrich Apel, CC BY-SA 3.0 */\n")
    fh.write("window.STROKES=" + json.dumps(strokes, ensure_ascii=False, separators=(",", ":")) + ";\n")
print(f"kll {len(kll)} | từ ghép {len(words)} | câu {len(sents)} | minna {len(minna)} | nhận diện {len(recog)} | nét {len(strokes)}")
print("thiếu nét cho KLL:", "".join(x["k"] for x in kll if x["k"] not in strokes))
print("KLL không nhận diện được:", "".join(x["k"] for x in kll if x["k"] not in recog))
