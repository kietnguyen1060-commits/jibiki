"""Kiểm tra mỗi đề có dùng đủ từ vựng và ngữ pháp của 5 bài tương ứng.

Chỉ tính chữ xuất hiện trong câu hỏi, câu hoàn chỉnh, đáp án đúng và bài đọc
(không tính phương án nhiễu). Động từ, tính từ được nhận diện cả ở dạng chia.
Cách dùng: py check.py [số đề ...]
"""
import json, re, sys, os

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
vocab = json.load(open(os.path.join(ROOT, "vocab.json"), encoding="utf-8"))
grammar = json.load(open(os.path.join(ROOT, "grammar.json"), encoding="utf-8"))

ROW_I = {"い": ("う", "わ", "って", "った"), "ち": ("つ", "た", "って", "った"), "り": ("る", "ら", "って", "った"),
         "み": ("む", "ま", "んで", "んだ"), "び": ("ぶ", "ば", "んで", "んだ"), "に": ("ぬ", "な", "んで", "んだ"),
         "き": ("く", "か", "いて", "いた"), "ぎ": ("ぐ", "が", "いで", "いだ"), "し": ("す", "さ", "して", "した")}
E_ROW = set("えけげせぜてでねへべぺめれ")
GROUP2_I = {"おき", "み", "い", "かり", "あび", "でき", "おり", "たり", "しんじ", "き"}


def verb_forms(kana, kanji):
    """Trả về các dạng chia (chuỗi con) của một động từ ます."""
    ks = kana[:-2]
    stems = [ks] + ([kanji[:-2]] if kanji else [])
    if ks == "き" and (not kanji or kanji.startswith("来")):  # 来ます
        out = ["来ま", "来て", "来た", "来な", "来る", "来れ", "来よ", "きま", "きて", "きた", "こな", "くる"]
        return out
    prefix_k = kanji[:-3] if kanji.endswith("します") else ""
    group3 = ks.endswith("し") and (ks == "し" or re.fullmatch(r"[一-龯ァ-ヿ]{2,}", prefix_k or "") or re.search(r"[ァ-ヿ]", prefix_k or ks))
    if ks == "おき" and kanji.startswith("置"):
        ks = "おき_"
    last = ks.rstrip("_")[-1]
    out = []
    for st in stems:
        out += [st + "ま", st + "たい", st + "たく", st + "たか", st + "に行", st + "に来", st + "方"]
        if group3:
            b = st[:-1]
            out += [b + "して", b + "した", b + "しな", b + "する", b + "でき", b + "すれ"]
        elif last in E_ROW or ks in GROUP2_I or (ks == "き" and kanji.startswith("着")):
            out += [st + "て", st + "た", st + "な", st + "る", st + "れ", st + "よう", st + "ら"]
        elif last in ROW_I:
            d, n, te, ta = ROW_I[last]
            b = st[:-1]
            if ks.endswith("いき"):
                te, ta = "って", "った"
            out += [b + d, b + n + "な", b + n + "なけ", b + te, b + ta]
    return out


def clean(raw):
    """Tách các cách viết thay thế và bỏ phần tùy chọn ［］, dấu câu."""
    out = []
    for raw in (re.sub(r"［[^］]*］", "", raw), re.sub(r"［([^］～]*)］", r"\1", raw)):
        out += clean_one(raw)
    return list(dict.fromkeys(out))


def clean_one(raw):
    alts = [re.sub(r"（[^）]*）", "", raw)] + re.findall(r"（([^）]*)）", raw)
    out = []
    for a in alts:
        for x in re.split(r"[、／]", a):
            x = re.sub(r"[。？！?\s－\-]", "", x).strip("～")
            if x:
                out.append(x)
    return out


def candidates(r):
    """Mỗi phần tử là một danh sách chuỗi con; tất cả phải có mặt."""
    res = []
    kana = clean(r["kana"])
    forms = clean(r["kanji"]) + kana if r["kanji"] else kana
    for a in forms:
        if a.endswith("ます"):
            k = kana[0] if kana else a
            kj = a if not re.fullmatch(r"[ぁ-ゖー]+ます", a) else ""
            for f in verb_forms(k, kj):
                res.append([f])
            continue
        parts = [p for p in a.split("～") if p]
        res.append(parts)
        if int(r["bai"]) >= 8 and a.endswith("い") and len(a) >= 2 and "～" not in a:
            st = "よ" if a in ("いい", "よい") else a[:-1]
            for suf in ("く", "かっ", "くて", "けれ", "さ"):
                res.append([st + suf])
    return res


def strip(s):
    s = re.sub(r"<rt>.*?</rt>", "", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"[\s　＿_★（）()、。？！?]", "", s)


def test_text(t):
    chunks, gram = [], set()
    for sec in t["sections"]:
        chunks.append(sec.get("passage", ""))
        for it in sec.get("items", []):
            chunks.append(it.get("q", ""))
            chunks.append(it.get("full", ""))
            if "o" in it:
                chunks.append(it["o"][it["a"]])
            gram.update(it.get("g", []))
        gram.update(sec.get("g", []))
    return strip("\n".join(chunks)), gram


def star_errors(t):
    """Câu ★: xếp các mảnh theo vị trí trong câu hoàn chỉnh, mảnh ở ô ★ phải là đáp án."""
    errs = []
    for sec in t["sections"]:
        for it in sec.get("items", []):
            if "full" not in it or "★" not in it["q"]:
                continue
            full = it["full"].replace(" ", "")
            pos = []
            for p in it["o"]:
                i = full.find(p.replace(" ", ""))
                pos.append(i)
            if -1 in pos:
                errs.append(it["q"][:24] + " (mảnh không có trong câu)")
                continue
            order = [p for _, p in sorted(zip(pos, it["o"]))]
            blanks = re.findall(r"＿＿|★", it["q"])
            slot = blanks.index("★")
            if order[slot] != it["o"][it["a"]]:
                errs.append(f'{it["q"][:24]} → ★ phải là {order[slot]}')
    return errs


def check(n):
    path = os.path.join(ROOT, "tests", f"test{n}.json")
    t = json.load(open(path, encoding="utf-8"))
    lo, hi = t["lessons"]
    text, gram = test_text(t)
    miss = []
    for r in vocab:
        if lo <= int(r["bai"]) <= hi:
            ok = any(all(p in text for p in c) for c in candidates(r))
            if not ok:
                miss.append(r)
    gids = [g["id"] for b in range(lo, hi + 1) for g in grammar[str(b)]]
    gmiss = [g for g in gids if g not in gram]
    total = sum(1 for r in vocab if lo <= int(r["bai"]) <= hi)
    nq = sum(len(s.get("items", [])) for s in t["sections"])
    print(f"Đề {n} (bài {lo}-{hi}): {nq} câu | từ vựng {total - len(miss)}/{total} | ngữ pháp {len(gids) - len(gmiss)}/{len(gids)}")
    for r in miss:
        print(f"  thiếu từ B{r['bai']}: {r['kanji'] or r['kana']} ({r['kana']}) = {r['nghia'][:30]}")
    if gmiss:
        print("  thiếu ngữ pháp:", ", ".join(gmiss))
    bad = [it for s in t["sections"] for it in s.get("items", []) if "o" in it and not (0 <= it["a"] < len(it["o"]))]
    if bad:
        print("  LỖI đáp án ngoài phạm vi:", len(bad))
    se = star_errors(t)
    if se:
        print("  LỖI câu ★:", se)
    return not miss and not gmiss and not se


if __name__ == "__main__":
    ns = [int(a) for a in sys.argv[1:]] or [1, 2, 3, 4, 5]
    ok = all([check(n) for n in ns])
    sys.exit(0 if ok else 1)
