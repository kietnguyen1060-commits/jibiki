"""Cắt tranh minh hoạ của từng chữ từ bản PDF sách Kanji Look and Learn của người học (dùng riêng, không đưa lên repo).

Mỗi mục chữ trong sách là một khung: hàng 1 (ô chữ lớn | tranh | lời giải thích), hàng 2 (âm đọc, từ ví dụ),
hàng 3 (thứ tự nét). Script tìm các đường kẻ ngang để nhận ra từng khung theo thứ tự trang, đánh số 1…512,
rồi cắt phần tranh nằm giữa ô chữ lớn và cột chữ giải thích.

Cách dùng: py cat_tranh_sach.py <sách.pdf> <app-data.js> <thư mục ra>
Ghi ra kll_book_<mã chữ 5 số hex>.png, _bao_cao.txt và _xem.html (để soát bằng mắt).
"""
import json, os, re, sys
import numpy as np
import pymupdf

sys.stdout.reconfigure(encoding="utf-8")
pdf_path, app_path, out_dir = sys.argv[1:4]
DPI = 200
S = DPI / 100  # các ngưỡng dưới đây đo ở 100 dpi

src = open(app_path, encoding="utf-8").read()
kll = sorted((x for x in json.loads(src[src.index("=") + 1:src.rindex(";")])["kll"] if x["n"] < 1000), key=lambda x: x["n"])


def groups(v):
    return [(int(g[0]), int(g[-1])) for g in np.split(v, np.where(np.diff(v) > 2)[0] + 1) if len(g)]


def runs(col, gap):
    idx = np.where(col)[0]
    if not len(idx):
        return []
    br = np.where(np.diff(idx) > gap)[0]
    return list(zip(np.r_[idx[0], idx[br + 1]], np.r_[idx[br], idx[-1]]))


def entries(gray):
    """Các khung chữ trên trang, từ trên xuống: (x cạnh phải ô chữ lớn, đỉnh, đáy hàng 1) theo pixel.

    Nhận ra ô chữ lớn nhờ hai cạnh dọc cao ~134 px (ở 100 dpi) cách nhau ~134 px (ô vuông)."""
    H, W = gray.shape
    dark = gray < 160
    # Nới ngang ±3 px để đường kẻ của trang scan hơi nghiêng vẫn liền một mạch.
    r = int(1.5 * S)
    dark = np.logical_or.reduce([np.roll(dark, k, axis=1) for k in range(-r, r + 1)])
    cand = []
    for x in range(int(.10 * W), int(.45 * W)):
        for s, e in runs(dark[:, x], int(4 * S)):
            if 118 * S <= e - s <= 150 * S:
                # Cạnh trái ô chữ phải là một đường dọc liền trên cùng đoạn.
                lo, hi = max(0, x - int(152 * S)), max(0, x - int(108 * S))
                if hi <= lo or dark[s:e, lo:hi].mean(0).max() <= 0.85:
                    continue
                # Bảng chữ ở đầu bài có nhiều đường dọc liên tiếp; khung chữ thì bên phải ô chữ gần như không có.
                right = dark[s:e, x + int(20 * S):int(.9 * W)].mean(0) > 0.85
                if len(groups(np.where(right)[0])) <= 1:
                    cand.append((x, int(s), int(e)))
    out = []
    for x, s, e in sorted(cand, key=lambda t: (t[1], t[0])):
        if out and abs(out[-1][1] - s) < 20 * S:
            out[-1] = (max(out[-1][0], x), out[-1][1], out[-1][2])
        elif not out or s - out[-1][1] > 200 * S:
            out.append((x, s, e))
    return out


def crop_picture(gray, kcell, top, bot):
    """Cắt vùng tranh của hàng 1: sau cạnh phải ô chữ lớn, trước khe trắng tách cột lời giải thích."""
    band = gray[top + 4:bot - 3] < 150
    H, W = band.shape
    right_lines = [(a + b) // 2 for a, b in groups(np.where(band.mean(0) > 0.8)[0]) if a > kcell + 200 * S]
    right = right_lines[-1] if right_lines else int(W * .93)
    # Khe trắng rộng nhất trong khoảng 38–68% bề ngang phần bên phải ô chữ.
    lo, hi = kcell + int((right - kcell) * .38), kcell + int((right - kcell) * .68)
    blank = np.where(band[:, lo:hi].sum(0) <= 1)[0]
    cut = lo + sum(max(groups(blank), key=lambda r: r[1] - r[0])) // 2 if len(blank) else kcell + int((right - kcell) * .52)
    x0 = kcell + int(4 * S)
    ys, xs = np.where(band[:, x0:cut])
    if not len(ys):
        return None
    pad = int(6 * S)
    return (x0 + max(0, xs.min() - pad), top + 4 + max(0, ys.min() - pad), x0 + xs.max() + pad, top + 4 + min(H, ys.max() + pad))


HEADER = re.compile(r"[（(]\s*(\d{1,3})\s*[-~～–－]\s*(\d{1,3})\s*[)）]")


def main():
    os.makedirs(out_dir, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    # Lượt 1: các khung chữ của từng trang và dải số in ở đầu trang (nếu OCR đọc được).
    pages = []
    for pi in range(doc.page_count):
        page = doc[pi]
        pm = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
        gray = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width)
        found = entries(gray)
        if found:
            m = HEADER.search(page.get_text())
            pages.append([pi, (int(m.group(1)), int(m.group(2))) if m else None, found])
    # Lượt 2: đánh số. Trang có dải số thì theo dải số; các trang không có nằm giữa hai trang có
    # thì đánh tiếp. Nếu một đoạn như vậy thừa khung (bảng chữ đầu bài), bỏ các khung trên cùng.
    report, assign = [], []          # assign: (số, trang, khung)
    i, n = 0, 0
    while i < len(pages):
        pi, hdr, found = pages[i]
        if hdr and hdr[1] - hdr[0] + 1 == len(found):
            assign += [(hdr[0] + j, pi, f) for j, f in enumerate(found)]
            n = hdr[1]
            i += 1
            continue
        j = i
        while j < len(pages) and not (pages[j][1] and pages[j][1][1] - pages[j][1][0] + 1 == len(pages[j][2])):
            j += 1
        nxt = pages[j][1][0] if j < len(pages) else len(kll) + 1
        span = [(pages[k][0], f) for k in range(i, j) for f in pages[k][2]]
        need = nxt - 1 - n
        if len(span) != need:
            report.append(f"trang {pages[i][0] + 1}–{pages[j - 1][0] + 1}: thấy {len(span)} khung cho số {n + 1}–{nxt - 1}; giữ {min(need, len(span))} khung dưới cùng")
            span = span[len(span) - need:] if len(span) > need else span
        assign += [(n + 1 + k, pg, f) for k, (pg, f) in enumerate(span)]
        n = nxt - 1
        i = j
    seen = []
    for num, pi, (kcell, top, bot) in assign:
        if not 1 <= num <= len(kll):
            continue
        x = kll[num - 1]
        page = doc[pi]
        pm = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
        gray = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width)
        box = crop_picture(gray, kcell, top, bot)
        if not box:
            report.append(f"{num} {x['k']} trang {pi + 1}: không cắt được tranh")
            continue
        name = f"kll_book_{ord(x['k']):05x}.png"
        page.get_pixmap(dpi=DPI, clip=pymupdf.Rect(*(c * 72 / DPI for c in box)), colorspace=pymupdf.csGRAY).save(os.path.join(out_dir, name))
        # Ảnh nhỏ của ô chữ lớn, chỉ để soát trong _xem.html.
        h = bot - top
        page.get_pixmap(dpi=40, clip=pymupdf.Rect(*(c * 72 / DPI for c in (kcell - int(.97 * h), top, kcell, bot))),
                        colorspace=pymupdf.csGRAY).save(os.path.join(out_dir, f"_o_{num:03d}.png"))
        seen.append((num, x["k"], name, pi + 1))
    done = {s[0] for s in seen}
    report += [f"THIẾU {x['n']} {x['k']}" for x in kll if x["n"] not in done]
    open(os.path.join(out_dir, "_bao_cao.txt"), "w", encoding="utf-8").write("\n".join(report))
    html = "".join(f'<figure style="margin:3px;display:flex;gap:2px;align-items:center"><img src="_o_{num:03d}.png" style="height:44px">'
                   f'<img src="{f}" style="height:44px"><figcaption>{num}{k}<br>tr.{pg}</figcaption></figure>' for num, k, f, pg in seen)
    open(os.path.join(out_dir, "_xem.html"), "w", encoding="utf-8").write(
        '<!doctype html><meta charset=utf-8><body style="display:flex;flex-wrap:wrap;font:12px sans-serif;margin:2px">' + html)
    print(f"đã cắt {len(seen)} / {len(kll)} chữ; ghi chú {len(report)}")
    print("\n".join(report[:40]))


main()
