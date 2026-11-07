"""Compact kanji dictionary for text scan: every character with a school grade or JLPT level in KANJIDIC2.

Writes ../app/data/tu-dien.js: window.TUDIEN = {kanji: [Sino-Vietnamese reading (Unihan), English meaning, on reading, kun reading]}.
Characters in the learner's own cards (app-data.js) still use the Vietnamese meaning from the card; this file only fills in the rest.
Usage: py build_tudien.py
"""
import gzip, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
DL = os.path.join(HERE, "..", "_dl")
OUT = os.path.join(HERE, "..", "app", "data", "tu-dien.js")
hira = lambda s: "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)

viet = {}
for line in open(os.path.join(DL, "unihan", "Unihan_Readings.txt"), encoding="utf-8"):
    if "\tkVietnamese\t" in line:
        cp, _, val = line.rstrip("\n").split("\t")
        viet[chr(int(cp[2:], 16))] = val.split()[0].upper()

out = {}
xml = gzip.open(os.path.join(DL, "kanjidic", "kanjidic2.xml.gz"), "rt", encoding="utf-8").read()
for m in re.finditer(r"<character>(.*?)</character>", xml, re.S):
    b = m.group(1)
    if not re.search(r"<grade>|<jlpt>", b):
        continue
    c = re.search(r"<literal>(.)</literal>", b).group(1)
    en = re.findall(r"<meaning>([^<]+)</meaning>", b)[:3]
    on = [hira(x) for x in re.findall(r'<reading r_type="ja_on">([^<]+)</reading>', b)][:3]
    kun = re.findall(r'<reading r_type="ja_kun">([^<]+)</reading>', b)[:3]
    out[c] = [viet.get(c, ""), ", ".join(en), "、".join(on), "、".join(kun)]

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("/* Chữ Hán: KANJIDIC2 (EDRDG, CC BY-SA 4.0); âm Hán Việt tham khảo: Unihan kVietnamese (Unicode). */\n")
    fh.write("window.TUDIEN=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n")
print(len(out), "chữ,", os.path.getsize(OUT) // 1024, "KB")
