"""Lập bảng nguồn cho các kanji có trong từ vựng Minna nhưng không có trong Kanji Look and Learn.

Ghi ra tools/extra_source.json (dùng để soạn nghĩa/cách nhớ tiếng Việt) và in bảng tóm tắt.
Cách dùng: py prep_extra.py
"""
import gzip, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DL = os.path.join(ROOT, "_dl")

src = open(os.path.join(ROOT, "app", "data", "app-data.js"), encoding="utf-8").read()
data = json.loads(src[src.index("=") + 1:src.rindex(";")])
kll = {x["k"] for x in data["kll"]}

order, words = [], {}
for w in data["minna"]:
    for c in w[0]:
        if "一" <= c <= "鿿" and c not in kll:
            if c not in words:
                order.append((w[3], c))
                words[c] = []
            words[c].append(f"{w[0]}({w[1]})={w[2][:18]}")
order.sort()

# KANJIDIC2: nghĩa tiếng Anh, âm on/kun, số nét, cấp JLPT cũ, bộ thủ.
kd = {}
xml = gzip.open(os.path.join(DL, "kanjidic", "kanjidic2.xml.gz"), "rt", encoding="utf-8").read()
for m in re.finditer(r"<character>(.*?)</character>", xml, re.S):
    b = m.group(1)
    c = re.search(r"<literal>(.)</literal>", b).group(1)
    if c not in words:
        continue
    kd[c] = {
        "en": [x for x in re.findall(r"<meaning>([^<]+)</meaning>", b)][:4],
        "on": re.findall(r'<reading r_type="ja_on">([^<]+)</reading>', b),
        "kun": re.findall(r'<reading r_type="ja_kun">([^<]+)</reading>', b),
        "net": int((re.search(r"<stroke_count>(\d+)</stroke_count>", b) or [0, 0])[1]),
        "jlpt": int((re.search(r"<jlpt>(\d)</jlpt>", b) or [0, 0])[1]),
    }

# Unihan kVietnamese (chỉ để đối chiếu âm Hán Việt).
viet = {}
for line in open(os.path.join(DL, "unihan", "Unihan_Readings.txt"), encoding="utf-8"):
    if "\tkVietnamese\t" in line:
        cp, _, val = line.rstrip("\n").split("\t")
        viet[chr(int(cp[2:], 16))] = val

# Thành phần cấp một trong KanjiVG.
comp = {}
kvg = gzip.open(os.path.join(DL, "kanjivg", "kanjivg.xml.gz"), "rt", encoding="utf-8").read()
for blk in re.finditer(r'<kanji id="kvg:kanji_([0-9a-f]+)">(.*?)</kanji>', kvg, re.S):
    ch = chr(int(blk.group(1), 16))
    if ch not in words:
        continue
    body = blk.group(2)
    depth, parts = 0, []
    for t in re.finditer(r"<g\b([^>]*)>|</g>", body):
        if t.group(0) == "</g>":
            depth -= 1
            continue
        depth += 1
        if depth == 2:
            el = re.search(r'kvg:element="([^"]+)"', t.group(1))
            parts.append(el.group(1) if el else "?")
    comp[ch] = parts

rows = []
for bai, c in order:
    k = kd.get(c, {})
    rows.append({"k": c, "bai": bai, "en": k.get("en", []), "on": k.get("on", []), "kun": k.get("kun", []),
                 "net": k.get("net", 0), "jlpt": k.get("jlpt", 0), "vi": viet.get(c, ""), "parts": comp.get(c, []),
                 "words": words[c][:3]})
json.dump(rows, open(os.path.join(HERE, "extra_source.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
lo, hi = (int(a) for a in (sys.argv[1:3] if len(sys.argv) > 2 else (0, len(rows))))
for i, r in enumerate(rows[lo:hi], lo):
    print(f"{i}|{r['k']}|B{r['bai']}|{r['vi']}|{'/'.join(r['en'][:3])}|{'+'.join(r['parts'])}|{' '.join(r['words'][:2])}")
print(len(rows), "chữ")
