"""Kiểm tra mỗi đề N4 dùng đủ từ vựng, ngữ pháp và kanji của bài tương ứng.

- Từ vựng: chỉ tính chữ trong câu hỏi, câu hoàn chỉnh, đáp án đúng và bài đọc
  (không tính phương án nhiễu). Động từ nhận diện cả dạng chia theo nhóm I/II/III.
  Tên riêng mà người học đã tạm ngưng trong Anki (cột "ten") không bắt buộc.
- Kanji: mỗi kanji của bài phải nằm trong phần gạch chân hoặc đáp án đúng
  của các phần hỏi kanji (section có "kanji": true).
Cách dùng: py check.py [số bài ...]
"""
import json, os, re, sys, unicodedata

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
vocab = json.load(open(os.path.join(ROOT, "vocab.json"), encoding="utf-8"))
grammar = json.load(open(os.path.join(ROOT, "grammar.json"), encoding="utf-8"))
kanji = json.load(open(os.path.join(ROOT, "kanji.json"), encoding="utf-8"))

ROWS = {"い": "わいうえお", "ち": "たちつてと", "り": "らりるれろ", "み": "まみむめも", "び": "ばびぶべぼ",
        "に": "なにぬねの", "き": "かきくけこ", "ぎ": "がぎぐげご", "し": "さしすせそ"}
TE = {"い": "って", "ち": "って", "り": "って", "み": "んで", "び": "んで", "に": "んで", "き": "いて", "ぎ": "いで", "し": "して"}
STEM_TAIL = ["ま", "たい", "たく", "たか", "に行", "に来", "方", "ながら", "そう", "すぎ", "やす", "にく"]


def clean(raw):
    out = []
    raw = re.sub(r"[－−―‐\-]", "～", raw)
    for r in (re.sub(r"［[^］]*］", "", raw), re.sub(r"［([^］～]*)］", r"\1", raw)):
        alts = [re.sub(r"（[^）]*）", "", r)] + re.findall(r"（([^）]*)）", r)
        for a in alts:
            for x in re.split(r"[、／]", a):
                x = re.sub(r"[。？！?\s－\-…]", "", x).strip("～")
                if x:
                    out.append(unicodedata.normalize("NFKC", x))
    return list(dict.fromkeys(out))


def verb_forms(word, group):
    stem = word[:-2]
    if not stem:
        return []
    out = [stem + t for t in STEM_TAIL] + ["お" + stem]
    if group == "III":
        if stem.endswith("来") or stem.endswith("き") and word.endswith("てきます"):
            base = stem[:-1]
            return out + [base + c for c in ("来", "こ", "く", "き")]
        base = stem[:-1]
        if not base:
            return out
        return out + [base + c for c in ("し", "す", "さ", "せ", "でき")]
    if group == "II":
        return out + [stem + c for c in ("て", "た", "な", "る", "れ", "よ", "ろ", "ら", "さ", "ず")]
    last = stem[-1]
    if last not in ROWS:
        return out
    b = stem[:-1]
    te = "って" if stem.endswith("いき") or stem.endswith("行き") else TE[last]
    ta = te[:-1] + ("だ" if te.endswith("で") else "た")
    row = ROWS[last]
    return out + [b + c for c in row if c != last] + [b + te, b + ta]


def candidates(r):
    res = []
    forms = clean(r["kanji"]) + clean(r["kana"]) if r["kanji"] else clean(r["kana"])
    for a in forms:
        if a.endswith("ます") and r["nhom"] in ("I", "II", "III"):
            res += [[f] for f in verb_forms(a, r["nhom"])]
            continue
        res.append([p for p in re.split(r"[～~]", a) if p])
        if a.endswith("い") and len(a) >= 2 and not re.search(r"[～~]", a):
            st = "よ" if a in ("いい", "よい") else a[:-1]
            res += [[st + s] for s in ("く", "かっ", "くて", "けれ", "さ", "そう", "すぎ", "み")]
    return [c for c in res if c]


def strip(s):
    s = unicodedata.normalize("NFKC", re.sub(r"<[^>]+>", "", s or ""))
    return re.sub(r"[\s　＿_★()、。？！?]", "", s)


def pools(t):
    text, ktext, gram = [], [], set()
    for sec in t["sections"]:
        text.append(sec.get("passage", ""))
        gram.update(sec.get("g", []))
        for it in sec.get("items", []):
            right = it["o"][it["a"]] if "o" in it else ""
            text += [it.get("q", ""), it.get("full", ""), right]
            if right and "（　）" in it.get("q", ""):
                text.append(it["q"].replace("（　）", right, 1))
            gram.update(it.get("g", []))
            if sec.get("kanji"):
                ktext += re.findall(r"<u>(.*?)</u>", it.get("q", "")) + [right]
    return strip("\n".join(text)), "".join(ktext), gram


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


def check(b, verbose=True):
    t = json.load(open(os.path.join(ROOT, "tests", f"test{b}.json"), encoding="utf-8"))
    text, ktext, gram = pools(t)
    words = [r for r in vocab if int(r["bai"]) == b]
    req = [r for r in words if not r["ten"]]
    miss = [r for r in req if not any(all(p in text for p in c) for c in candidates(r))]
    names = [r for r in words if r["ten"] and any(all(p in text for p in c) for c in candidates(r))]
    gids = [g["id"] for g in grammar[str(b)]]
    gmiss = [g for g in gids if g not in gram]
    ks = [x["k"] for x in kanji.get(str(b), [])]
    kmiss = [k for k in ks if k not in ktext]
    nq = sum(len(s.get("items", [])) for s in t["sections"])
    ok = not miss and not gmiss and not kmiss
    if verbose or not ok:
        print(f"Bài {b}: {nq} câu | từ {len(req) - len(miss)}/{len(req)} (+{len(names)}/{len(words) - len(req)} tên riêng)"
              f" | ngữ pháp {len(gids) - len(gmiss)}/{len(gids)} | kanji {len(ks) - len(kmiss)}/{len(ks)}")
    for r in miss:
        print(f"  thiếu từ: {r['kanji'] or r['kana']} ({r['kana']}) [{r['nhom']}] = {r['nghia'][:30]}")
    if gmiss:
        print("  thiếu ngữ pháp:", ", ".join(gmiss))
    if kmiss:
        print("  thiếu kanji:", "".join(kmiss))
    bad = [it["q"][:20] for s in t["sections"] for it in s.get("items", []) if "o" in it and (not 0 <= it["a"] < len(it["o"]) or len(set(it["o"])) != len(it["o"]))]
    if bad:
        print("  LỖI phương án:", bad)
        ok = False
    se = star_errors(t)
    if se:
        print("  LỖI câu ★:", se)
        ok = False
    return ok


if __name__ == "__main__":
    ns = [int(a) for a in sys.argv[1:]] or [b for b in range(26, 51) if os.path.exists(os.path.join(ROOT, "tests", f"test{b}.json"))]
    res = [check(n) for n in ns]
    sys.exit(0 if all(res) else 1)
