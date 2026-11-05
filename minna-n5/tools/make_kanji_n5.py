"""Tạo data/kanji-n5.json: kanji N5 theo bài Minna I đầu tiên có chữ đó.

Danh sách N5: KANJIDIC2 mức jlpt=4 (mức cũ trước 2010, gần đúng với N5 hiện nay).
Âm Hán Việt lấy từ kanji-app/app/data/tu-dien.js. Mười chữ không có trong cột kanji của từ vựng Minna I
(số đếm viết bằng chữ số, 南, 西) được gán bài và từ ví dụ ở bảng THEM.
Cách dùng: py make_kanji_n5.py (cần kanji-app/_dl/kanjidic/kanjidic2.xml*)."""
import glob, gzip, json, os, re, xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
THEM = {"二": ("二つ", "ふたつ", "2 cái", 11), "三": ("三つ", "みっつ", "3 cái", 11), "四": ("四つ", "よっつ", "4 cái", 11),
        "五": ("五つ", "いつつ", "5 cái", 11), "六": ("六つ", "むっつ", "6 cái", 11), "八": ("八つ", "やっつ", "8 cái", 11),
        "九": ("九つ", "ここのつ", "9 cái", 11), "十": ("十", "とお", "10 cái", 11), "南": ("南", "みなみ", "phía nam", 23),
        "西": ("西", "にし", "phía tây", 23)}

path = glob.glob(os.path.join(ROOT, "kanji-app", "_dl", "kanjidic", "**", "kanjidic2*"), recursive=True)[0]
raw = gzip.open(path, "rb").read() if path.endswith(".gz") else open(path, "rb").read()
n5 = []
for c in ET.fromstring(raw).iter("character"):
    j = c.find("misc/jlpt")
    if j is not None and j.text == "4":
        n5.append(c.find("literal").text)

s = open(os.path.join(ROOT, "kanji-app", "app", "data", "tu-dien.js"), encoding="utf-8").read()
td = json.loads(s[s.index("window.TUDIEN=") + 14:].rstrip().rstrip(";"))
vocab = json.load(open(os.path.join(HERE, "..", "data", "vocab.json"), encoding="utf-8"))

out = {}
for k in n5:
    bai = min((int(r["bai"]) for r in vocab if k in r["kanji"]), default=None)
    entry = {"k": k, "hv": (td.get(k) or [""])[0], "nghia": (td.get(k) or ["", ""])[1].split(",")[0]}
    if bai is None:
        word, kana, nghia, bai = THEM[k]
        entry["them"] = [word, kana, nghia]
    out.setdefault(str(bai), []).append(entry)
json.dump(dict(sorted(out.items(), key=lambda x: int(x[0]))), open(os.path.join(HERE, "..", "data", "kanji-n5.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(sum(len(v) for v in out.values()), "kanji,", {k: len(v) for k, v in sorted(out.items(), key=lambda x: int(x[0]))})
