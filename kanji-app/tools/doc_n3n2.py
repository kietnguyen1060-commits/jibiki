"""Đọc sách "Kanji Look and Learn N3 N2 (tiếng Việt)" (PDF có lớp chữ) thành dữ liệu từng chữ + tranh.

Mỗi mục trong sách: "N. 字    hán việt    nghĩa    romaji", câu gợi nhớ, 訓:…, 音:…, rồi danh sách từ ghép
đánh số (từ, cách đọc, HÁN VIỆT, nghĩa). Tranh của mục là ảnh lớn trên cùng trang, theo thứ tự từ trên xuống.

Cách dùng: py doc_n3n2.py <sách.pdf> <thư mục ra>
Ghi ra n3n2.json, tranh kll_n3_<mã chữ 5 số hex>.png, _bao_cao.txt và _xem.png (bảng soát).
Dữ liệu và tranh là của sách, chỉ dùng riêng: thư mục ra nằm trong _build/ (không đưa lên repo).
"""
import json, os, re, sys
import pymupdf

sys.stdout.reconfigure(encoding="utf-8")
pdf_path, out_dir = sys.argv[1:3]
FIRST, LAST = 4, 169  # các trang mục chữ (sau đó là bảng tóm tắt lặp lại)

HEAD = re.compile(r"(?m)^[ \t]*(\d+)\.[ \t]*\n?[ \t]*([㐀-鿿])[ \t]{2,}")
KANA = re.compile(r"^[぀-ヿー～・.\s（）()]+$")


def fix(t):
    # Phông chữ của bản PDF mã hoá "ư" thành "ƣ" và "ú" thành "ö".
    return t.replace("ƣ", "ư").replace("Ƣ", "Ư").replace("Ö", "Ú").replace("ö", "ú")


def hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def is_hv(tok):
    return tok.isupper() and not re.search(r"[぀-鿿\d]", tok)


def parse_word(item):
    """'迎合 げいごう NGHÊNH HỢP sự nắm được ý…' → [từ, cách đọc, HÁN VIỆT, nghĩa]."""
    toks = item.split()
    if not toks:
        return None
    w, i = toks[0], 1
    r = ""
    if i < len(toks) and KANA.match(toks[i]):
        r, i = toks[i], i + 1
    hv = []
    while i < len(toks) and is_hv(toks[i]):
        hv.append(toks[i])
        i += 1
    if not r and KANA.match(w):
        r = w
    m = " ".join(toks[i:]).strip(" .;")
    return [w, r, " ".join(hv), m]


def parse_entry(n, k, body):
    lines = [l.strip() for l in body.split("\n")]
    # Dòng tiêu đề có thể xuống dòng: gom tới dòng trống đầu tiên.
    head = []
    while lines and lines[0]:
        head.append(lines.pop(0))
        # Dòng tiêu đề kết thúc bằng romaji (có khi kèm "CX"); câu gợi nhớ có thể nằm ngay dòng sau.
        if re.search(r"\s{2,}[a-z]+(?:\s+[A-Z]{1,3})?\s*$", head[-1]):
            break
    parts = [p.strip() for p in re.split(r"\s{2,}", " ".join(head)) if p.strip()]
    hv, romaji = (parts[0] if parts else ""), (parts[-1] if len(parts) > 2 else "")
    nghia = " ".join(parts[1:-1]) if len(parts) > 2 else (parts[1] if len(parts) > 1 else "")
    # Bỏ dấu ngắt trang; dòng 音: có khi bị đẩy sang trang sau, nằm giữa danh sách từ.
    rest = "\n".join(l for l in lines if not l.startswith("@@PAGE"))
    on = re.search(r"音\s*:[ \t]*([^\n]*)", rest)
    if on:
        rest = rest[:on.start()] + rest[on.end():]
    cut = re.search(r"訓\s*:|$", rest).start()
    nho = rest[:cut]
    kun = re.search(r"訓\s*:(.*?)(?=\n\s*\n|\n\s*1\s*\n|$)", rest, re.S)
    first = re.search(r"(?m)^\s*[123]\s*$", rest[cut:])  # có mục sách quên in số 1
    after = rest[cut + first.start():] if first else ""
    # Bỏ chữ lớn + Hán Việt in hoa của mục kế tiếp nằm cuối phần thân (ví dụ "路 / LỘ").
    after = re.sub(r"\n\s*[㐀-鿿]\s*\n\s*[A-ZÀ-ỸĐ ]+\s*$", "", after.rstrip())
    words = []
    for item in re.split(r"(?m)^\s*\d{1,2}\s*$", after)[1:]:
        w = parse_word(" ".join(item.split()))
        if w and re.search(r"[぀-鿿]", w[0]):
            words.append(w)
    clean = lambda s: " ".join(s.split()).strip(" ,")
    kun_s = [hira(x.strip()) for x in re.split(r"[,、]", clean(kun.group(1)) if kun else "") if x.strip()]
    on_s = [hira(x.strip()) for x in re.split(r"[,、]", clean(on.group(1)) if on else "") if x.strip()]
    return {"n": n, "k": k, "hv": hv.upper(), "nghia": clean(nghia), "romaji": romaji, "nho": clean(nho),
            "kun": kun_s, "on": on_s, "tu": words}


def main():
    os.makedirs(out_dir, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    text, starts = "", []          # starts: (vị trí trong text, trang)
    for pi in range(FIRST, LAST):
        t = fix(doc[pi].get_text())
        t = re.sub(r"^\s*\d+\s*\n", "", t, count=1)  # số trang
        starts.append((len(text), pi))
        text += t + "\n"
    heads = list(HEAD.finditer(text))
    page_of = lambda pos: max(p for s, p in starts if s <= pos)
    entries, report = [], []
    for j, m in enumerate(heads):
        end = heads[j + 1].start() if j + 1 < len(heads) else len(text)
        e = parse_entry(int(m.group(1)), m.group(2), text[m.end():end])
        e["page"] = page_of(m.start())
        entries.append(e)
    # Tranh: ảnh lớn của trang, từ trên xuống, ghép với các mục bắt đầu trên trang đó.
    by_page = {}
    for e in entries:
        by_page.setdefault(e["page"], []).append(e)
    for pi, es in by_page.items():
        page = doc[pi]
        imgs = sorted((b for b in page.get_text("dict")["blocks"] if b["type"] == 1 and b["bbox"][3] - b["bbox"][1] > 60),
                      key=lambda b: b["bbox"][1])
        if len(imgs) != len(es):
            report.append(f"trang {pi + 1}: {len(imgs)} tranh cho {len(es)} mục ({' '.join(e['k'] for e in es)})")
        for e, b in zip(es, imgs):
            name = f"kll_n3_{ord(e['k']):05x}.png"
            pymupdf.Pixmap(b["image"]).save(os.path.join(out_dir, name)) if False else open(os.path.join(out_dir, name), "wb").write(
                pymupdf.Pixmap(pymupdf.csRGB, pymupdf.Pixmap(b["image"])).tobytes("png") if b.get("ext") not in ("png",) else b["image"])
            e["img"] = name
    for e in entries:
        if not e.get("img"):
            report.append(f"{e['n']} {e['k']}: không có tranh")
        if not e["tu"]:
            report.append(f"{e['n']} {e['k']}: không đọc được từ ghép")
        if not e["nho"]:
            report.append(f"{e['n']} {e['k']}: không có câu gợi nhớ")
    json.dump(entries, open(os.path.join(out_dir, "n3n2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(out_dir, "_bao_cao.txt"), "w", encoding="utf-8").write("\n".join(report))
    print(f"{len(entries)} mục; có tranh {sum(1 for e in entries if e.get('img'))}; ghi chú {len(report)}")
    print("\n".join(report[:30]))


main()
