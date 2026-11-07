"""Draw Kanji Look and Learn style pictures: line drawing (OpenMoji, black and white) → the kanji (KanjiVG strokes).

Each line in tools/tranh.txt: `kanji|picture1 picture2…` (an emoji or OpenMoji hex code, for example 後|🚶).
Usage: py make_tranh.py <tranh.txt> <kanjivg.xml.gz> <openmoji/black> <output folder> [kanji…]
Writes kll_pic_<5-digit hex code of the kanji>.svg
"""
import gzip, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
map_path, kvg_path, om_dir, out_dir = sys.argv[1:5]
only = set("".join(sys.argv[5:]))
CREDIT = "<!-- Tranh: OpenMoji (openmoji.org), CC BY-SA 4.0. Nét chữ: KanjiVG (kanjivg.tagaini.net), Ulrich Apel, CC BY-SA 3.0 -->"

rows = {}
for line in open(map_path, encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#"):
        ch, pics = line.split("|")[:2]
        if not only or ch in only:
            rows[ch] = [p for p in re.split(r"[\s+]+", pics) if p]

strokes = {}
xml = gzip.open(kvg_path, "rt", encoding="utf-8").read()
for block in re.finditer(r'<kanji id="kvg:kanji_([0-9a-f]+)">(.*?)</kanji>', xml, re.S):
    ch = chr(int(block.group(1), 16))
    if ch in rows:
        ps = re.findall(r'<path id="kvg:[0-9a-f]+(?:-[^"]*)?-s(\d+)"[^>]*\sd="([^"]+)"', block.group(2))
        strokes[ch] = [d for _, d in sorted(ps, key=lambda p: int(p[0]))]


def picto(pic):
    """The inner part of an OpenMoji <svg>, without ids so they don't clash when combined.

    pic is an emoji (🚶) or a hex code (1F6B6). OpenMoji file names sometimes keep FE0F and sometimes drop it."""
    if re.fullmatch(r"[0-9A-Fa-f-]+", pic):
        names = [pic.upper()]
    else:
        full = "-".join(f"{ord(c):04X}" for c in pic)
        names = [full, "-".join(f"{ord(c):04X}" for c in pic if c != "️")]
    path = next((os.path.join(om_dir, f"{n}.svg") for n in names if os.path.exists(os.path.join(om_dir, f"{n}.svg"))), None)
    if not path:
        raise FileNotFoundError(names[0], pic)
    src = open(path, encoding="utf-8").read()
    body = src[src.index(">", src.index("<svg")) + 1:src.rindex("</svg>")]
    return re.sub(r'\sid="[^"]*"', "", body)


BOX, GAP, H = 104, 30, 120
os.makedirs(out_dir, exist_ok=True)
missing = []
for ch, codes in rows.items():
    try:
        pics = [picto(c) for c in codes]
    except FileNotFoundError as e:
        missing.append(f"{ch}:{e.args[-1]}")
        continue
    n = len(pics)
    width = n * BOX + (n - 1) * 18 + GAP + BOX + 16
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {H}" width="{width * 1.6:.0f}" height="{H * 1.6:.0f}">', CREDIT,
           f'<rect width="{width}" height="{H}" rx="10" fill="#ffffff"/>']
    x = 8
    for i, body in enumerate(pics):
        # OpenMoji draws on a 72×72 grid; scale it up to the BOX frame.
        out.append(f'<g transform="translate({x},{(H - BOX) / 2}) scale({BOX / 72:.4f})">{body}</g>')
        x += BOX
        if i < n - 1:
            out.append(f'<text x="{x + 9}" y="{H / 2 + 8}" font-size="22" text-anchor="middle" fill="#888" font-family="sans-serif">+</text>')
            x += 18
    out.append(f'<text x="{x + GAP / 2}" y="{H / 2 + 9}" font-size="26" text-anchor="middle" fill="#555" font-family="sans-serif">→</text>')
    x += GAP
    out.append(f'<g transform="translate({x},{(H - BOX) / 2}) scale({BOX / 109:.4f})">' +
               "".join(f'<path d="{d}" fill="none" stroke="#111" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>'
                       for d in strokes.get(ch, [])) + "</g>")
    out.append("</svg>")
    open(os.path.join(out_dir, f"kll_pic_{ord(ch):05x}.svg"), "w", encoding="utf-8").write("".join(out))
print("đã vẽ", len(rows) - len(missing), "chữ; thiếu tranh:", " ".join(missing))
