"""Vẽ hình cho thẻ kanji từ dữ liệu KanjiVG (CC BY-SA 3.0):

- kll_comp_<mã>.svg   hình tách bộ thành phần, mỗi bộ một màu: 彳 + … → 後
- kll_stroke_<mã>.svg dải thứ tự nét như hàng cuối trang sách Look and Learn

Cách dùng: py make_images.py <danh sách chữ> <thư mục ra>
"""
import gzip, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
KVG = os.path.join(HERE, "..", "_dl", "kanjivg", "kanjivg.xml.gz")
COLORS = ["#c0392b", "#1f6fb2", "#2e8b57", "#b8860b", "#8e44ad", "#d35400", "#16a085"]
INK, DONE, NEW = "#222222", "#9aa0a6", "#c0392b"
CREDIT = "<!-- Dựa trên KanjiVG (http://kanjivg.tagaini.net), Ulrich Apel, CC BY-SA 3.0 -->"


def components(block):
    """Chia nét theo nhóm cấp 2; mỗi lần mở nhóm cấp 2 mới là một thành phần mới."""
    comps, cur = [], None
    depth = 0
    for t in re.finditer(r'<g\b([^>]*)>|</g>|<path\b[^>]*\sid="kvg:[0-9a-f]+(?:-[^"]*)?-s(\d+)"[^>]*\sd="([^"]+)"', block):
        s = t.group(0)
        if s.startswith("</g"):
            depth -= 1
            if depth == 1:
                cur = None
        elif s.startswith("<g"):
            depth += 1
            if depth == 2:
                el = re.search(r'kvg:element="([^"]+)"', t.group(1) or "")
                cur = [el.group(1) if el else "", []]
                comps.append(cur)
        else:
            d = (int(t.group(2)), t.group(3))
            if cur is None:
                comps.append(["", [d]])
            else:
                cur[1].append(d)
    strokes = sorted(d for c in comps for d in c[1])
    comps = [(lab, [d for _, d in sorted(ps)]) for lab, ps in comps if ps]
    return comps, [d for _, d in strokes]


def path(d, color, w=3.6):
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'


def comp_svg(ch, comps, strokes):
    box, gap = 109, 34
    show = comps if len(comps) > 1 else []
    n = len(show)
    width = n * box + max(0, n - 1) * gap + (gap + 10 if n else 0) + box
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 142" width="{width * 1.5:.0f}" height="213">', CREDIT,
           f'<rect width="{width}" height="142" rx="10" fill="#ffffff"/>']
    x = 0
    for i, (lab, ps) in enumerate(show):
        col = COLORS[i % len(COLORS)]
        out.append(f'<g transform="translate({x},0)">' + "".join(path(d, col) for d in ps) + "</g>")
        if lab and lab != ch:
            out.append(f'<text x="{x + box / 2}" y="136" font-size="18" text-anchor="middle" fill="{col}" font-family="Yu Gothic, Meiryo, sans-serif">{lab}</text>')
        x += box
        if i < n - 1:
            out.append(f'<text x="{x + gap / 2}" y="66" font-size="30" text-anchor="middle" fill="#666" font-family="sans-serif">+</text>')
            x += gap
    if n:
        out.append(f'<text x="{x + (gap + 10) / 2}" y="66" font-size="30" text-anchor="middle" fill="#666" font-family="sans-serif">→</text>')
        x += gap + 10
    # Chữ hoàn chỉnh: mỗi thành phần giữ màu của nó.
    body = []
    if n:
        for i, (_, ps) in enumerate(show):
            body += [path(d, COLORS[i % len(COLORS)], 4.2) for d in ps]
    else:
        body = [path(d, INK, 4.2) for d in strokes]
    out.append(f'<g transform="translate({x},0)">' + "".join(body) + "</g></svg>")
    return "".join(out)


def stroke_svg(strokes):
    n, box = len(strokes), 109
    w = n * box
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {box}" width="{n * 46}" height="46">', CREDIT,
           f'<rect width="{w}" height="{box}" rx="8" fill="#ffffff"/>']
    for i in range(n):
        g = [path(strokes[j], DONE if j < i else NEW, 4.5 if j == i else 3.6) for j in range(i + 1)]
        out.append(f'<g transform="translate({i * box},0)">' + "".join(g) + "</g>")
        if i:
            out.append(f'<line x1="{i * box}" y1="6" x2="{i * box}" y2="{box - 6}" stroke="#cfcfcf" stroke-dasharray="4 4"/>')
    out.append("</svg>")
    return "".join(out)


def name(kind, ch):
    return f"kll_{kind}_{ord(ch):05x}.svg"


if __name__ == "__main__":
    chars, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    want = set(chars)
    xml = gzip.open(KVG, "rt", encoding="utf-8").read()
    made, labels = 0, {}
    for blk in re.finditer(r'<kanji id="kvg:kanji_([0-9a-f]+)">(.*?)</kanji>', xml, re.S):
        ch = chr(int(blk.group(1), 16))
        if ch not in want:
            continue
        comps, strokes = components(blk.group(2))
        if not strokes:
            continue
        open(os.path.join(outdir, name("comp", ch)), "w", encoding="utf-8").write(comp_svg(ch, comps, strokes))
        open(os.path.join(outdir, name("stroke", ch)), "w", encoding="utf-8").write(stroke_svg(strokes))
        labels[ch] = [lab for lab, _ in comps if lab and lab != ch]
        made += 1
    import json
    json.dump(labels, open(os.path.join(outdir, "_labels.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("đã vẽ", made, "chữ; thiếu:", "".join(c for c in want if c not in labels))
