"""Trang Luyện tập của từng bài: phần soạn tay (data/luyen-*.json) + phần sinh tự động từ từ vựng và kanji.

Tự động (như sách drill): mỗi từ hỏi một câu nghĩa → từ; mỗi kanji hỏi một câu đọc và một câu viết.
- Nhiễu của câu đọc: đổi âm đục / trường âm / âm ngắt (lỗi hay gặp), giữ nguyên đuôi ます.
- Nhiễu của câu viết: thay kanji cần hỏi bằng chữ cùng bộ thủ, số nét gần nhau.
Soạn tay: ことばの 使い方, ngữ pháp cho các mẫu ít được hỏi trong đề, bài đọc phải suy luận.
"""
import glob, json, os, random, re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

VOICE = {}
for a, b in zip("かきくけこさしすせそたちつてとはひふへほ", "がぎぐげござじずぜぞだぢづでどばびぶべぼ"):
    VOICE[a] = b; VOICE[b] = a
O_ROW = "おこそとのほもよろごぞどぼぽ"
TSU_BEFORE = "かきくけこさしすせそたちつてとぱぴぷぺぽ"


def bo_ngoac(s):
    """Bỏ phần ghi chú trong ngoặc nửa cỡ: 片づきます[荷物が~]."""
    return re.sub(r"\[[^\]]*\]", "", s or "")


def main_form(r, check):
    """Cách viết chính của từ: bỏ ［…］, lấy cách viết đầu."""
    forms = check.clean(bo_ngoac(r["kanji"])) if r["kanji"] else []
    kana = check.clean(bo_ngoac(r["kana"]))
    return (forms[0] if forms else kana[0] if kana else r["kana"]), (kana[0] if kana else r["kana"])


def word_class(w):
    return "v" if w.endswith("ます") else "a" if w.endswith("い") else "n"


def reading_variants(kana, rng):
    """Các cách đọc sai có thể gặp; không đổi đuôi ます."""
    n = len(kana) - 2 if kana.endswith("ます") else len(kana)
    out = []
    for i in range(n):
        c = kana[i]
        if c in VOICE:
            out.append(kana[:i] + VOICE[c] + kana[i + 1:])
        if c in O_ROW:
            if kana[i + 1:i + 2] == "う":
                out.append(kana[:i + 1] + kana[i + 2:])
            else:
                out.append(kana[:i + 1] + "う" + kana[i + 1:])
        if c == "っ":
            out.append(kana[:i] + kana[i + 1:])
        elif c in TSU_BEFORE and i:
            out.append(kana[:i] + "っ" + kana[i:])
    out = [x for x in dict.fromkeys(out) if x != kana]
    rng.shuffle(out)
    return out


def writing_variants(word, k, bo, rng):
    """Thay kanji k trong từ bằng chữ cùng bộ thủ (số nét gần nhau), thiếu thì lấy chữ cùng số nét."""
    rad, st = bo.get(k, (0, 0))
    same = sorted((x for x, v in bo.items() if x != k and x not in word and v[0] == rad), key=lambda x: (abs(bo[x][1] - st), x))
    near = sorted((x for x, v in bo.items() if x != k and x not in word and v[0] != rad), key=lambda x: (abs(bo[x][1] - st), x))
    head = same[:6]; rng.shuffle(head)
    tail = near[:30]; rng.shuffle(tail)
    return [word.replace(k, x, 1) for x in (head + tail)]


def options(ok, wrong):
    seen, res = {ok}, [ok]
    for w in wrong:
        if w not in seen:
            seen.add(w); res.append(w)
        if len(res) == 4:
            break
    return res


def tu_drill(b, check, rng):
    rows = [r for r in check.vocab if not r["ten"]]
    items = []
    for r in (x for x in rows if int(x["bai"]) == b):
        word, kana = main_form(r, check)
        cls = word_class(word)
        pool = [x for x in rows if x is not r and x["nghia"] != r["nghia"] and word_class(main_form(x, check)[0]) == cls]
        here = [x for x in pool if int(x["bai"]) == b]
        near = [x for x in pool if x not in here and abs(int(x["bai"]) - b) <= 3]
        rng.shuffle(here); rng.shuffle(near)
        o = options(word, [main_form(x, check)[0] for x in here + near])
        if len(o) == 4:
            items.append({"q": r["nghia"], "o": o, "a": 0, "e": f"{word} ({kana}) = {r['nghia']}."})
    return items


def kanji_drill(b, check, bo, rng):
    rows = [r for r in check.vocab if int(r["bai"]) == b]
    read, write = [], []
    for x in check.kanji.get(str(b), []):
        k = x["k"]
        # Kanji có thể chỉ nằm ở cách viết thứ hai (見ます、診ます) hoặc trong ［…］; bài này không có thì tìm cả bộ từ.
        cands = []
        for pool in (rows, check.vocab):
            for r in pool:
                kana = main_form(r, check)[1]
                cands += [(f, kana, r) for f in check.clean(bo_ngoac(r["kanji"])) if k in f and "～" not in f][:1]
            if cands:
                break
        if not cands:
            continue
        word, kana, r = cands[0]
        wrong = reading_variants(kana, rng)
        others = [main_form(z, check)[1] for z in rows]
        rng.shuffle(others)
        others.sort(key=lambda z: abs(len(z) - len(kana)))  # chữ ngắn thì phương án cũng ngắn, không lộ đáp án
        o = options(kana, wrong + others)
        ctx = f"<u>{word}</u>"
        if word in (r.get("vd") or ""):
            ctx = r["vd"].replace(word, f"<u>{word}</u>", 1)
        if len(o) == 4:
            read.append({"q": ctx, "o": o, "a": 0, "e": f"{word} = {kana}. {k}: {x['hv']} ({x['nghia']})."})
        word2, kana2, r2 = cands[-1]
        o = options(word2, writing_variants(word2, k, bo, rng))
        if len(o) == 4:
            write.append({"q": f"<u>{kana2}</u>（{r2['nghia']}）", "o": o, "a": 0, "e": f"{kana2} = {word2}. {k}: {x['hv']} ({x['nghia']})."})
    return read, write


def tay():
    res = {}
    for f in sorted(glob.glob(os.path.join(DATA, "luyen-*.json"))):
        res.update(json.load(open(f, encoding="utf-8")))
    return res


def rotate(sections, seed):
    """Đảo vị trí phương án để đáp án đúng chia đều 4 vị trí (cố định theo seed)."""
    rng = random.Random(seed)
    items = [it for s in sections for it in s["items"]]
    slots = [i % 4 for i in range(len(items))]
    rng.shuffle(slots)
    for it, target in zip(items, slots):
        k = len(it["o"])
        shift = (target % k - it["a"]) % k
        if shift:
            it["o"] = it["o"][-shift:] + it["o"][:-shift]
        it["a"] = (it["a"] + shift) % k


def build(check):
    bo = {k: tuple(v) for k, v in json.load(open(os.path.join(DATA, "bo-thu.json"), encoding="utf-8")).items()}
    hand = tay()
    res = {}
    for b in range(26, 51):
        rng = random.Random(7000 + b)
        h = hand[str(b)]
        read, write = kanji_drill(b, check, bo, rng)
        sections = [
            {"part": "もじ・ごい", "title": "ことばドリル　意味", "instr": "Chọn từ tiếng Nhật có nghĩa này. Mọi từ của bài đều có một câu.", "items": tu_drill(b, check, rng)},
            {"part": "もじ・ごい", "title": "漢字ドリル　読み方", "instr": "Chọn cách đọc đúng của từ gạch chân. Mọi kanji của bài đều có một câu.", "items": read},
            {"part": "もじ・ごい", "title": "漢字ドリル　書き方", "instr": "Chọn cách viết đúng. Các phương án sai dùng chữ có hình gần giống.", "items": write},
            {"part": "もじ・ごい", "title": "もんだい　ことばの 使い方", "instr": "Chọn câu dùng từ đúng nhất.", "items": h["dung"]},
            {"part": "ぶんぽう", "title": "もんだい　文法", "instr": "Chọn từ thích hợp. Câu có ★: sắp xếp các mảnh rồi chọn mảnh ở vị trí ★.", "items": h["np"]},
            {"part": "どっかい", "title": "もんだい　" + h["doc"]["title"], "instr": "Đọc và trả lời. Đáp án không nằm nguyên văn trong bài: phải suy luận.", "kind": "passage", "passage": h["doc"]["passage"], "items": h["doc"]["items"]},
        ]
        rotate(sections, 5000 + b)
        res[b] = {"title": f"Luyện tập bài {b}", "sections": sections}
    return res
