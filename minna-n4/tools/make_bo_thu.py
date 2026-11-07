"""Build data/bo-thu.json {kanji: [radical, stroke count]} from KANJIDIC2 for the kanji in the Minna vocabulary.
Used to generate look-alike distractors in the kanji writing drills. Only needs to be rerun when the vocabulary changes.
Usage: py make_bo_thu.py (needs kanji-app/_dl/kanjidic/kanjidic2.xml*)."""
import glob, gzip, json, os, re, xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
KJ = re.compile(r"[一-鿿]")

used = set()
for f in ("minna-n4", "minna-n5"):
    for r in json.load(open(os.path.join(ROOT, f, "data", "vocab.json"), encoding="utf-8")):
        used.update(KJ.findall(r["kanji"]))

path = glob.glob(os.path.join(ROOT, "kanji-app", "_dl", "kanjidic", "**", "kanjidic2*"), recursive=True)[0]
raw = gzip.open(path, "rb").read() if path.endswith(".gz") else open(path, "rb").read()
out = {}
for c in ET.fromstring(raw).iter("character"):
    k = c.find("literal").text
    if k in used:
        rad = c.find("radical/rad_value[@rad_type='classical']")
        out[k] = [int(rad.text), int(c.find("misc/stroke_count").text)]
json.dump(out, open(os.path.join(HERE, "..", "data", "bo-thu.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
print(len(out), "kanji")
