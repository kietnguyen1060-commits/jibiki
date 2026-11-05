"""Trang Luyện tập N5 cho từng bài. Cách sinh câu dùng chung với N4 (minna-n4/tools/luyen.py).

Tự động: mỗi từ một câu nghĩa → từ; mỗi kanji N5 một câu đọc và một câu viết, hỏi ở bài đầu tiên có chữ đó.
Soạn tay (data/luyen-*.json): ngữ pháp cho các mẫu ít được hỏi trong đề và bài đọc phải suy luận.
"""
import glob, importlib.util, json, os, types

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
spec = importlib.util.spec_from_file_location("luyen_n4", os.path.join(HERE, "..", "..", "minna-n4", "tools", "luyen.py"))
n4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n4)


def tay():
    res = {}
    for f in sorted(glob.glob(os.path.join(DATA, "luyen-*.json"))):
        res.update(json.load(open(f, encoding="utf-8")))
    return res


def build(check):
    import random
    bo = {k: tuple(v) for k, v in json.load(open(os.path.join(HERE, "..", "..", "minna-n4", "data", "bo-thu.json"), encoding="utf-8")).items()}
    kanji = json.load(open(os.path.join(DATA, "kanji-n5.json"), encoding="utf-8"))
    # Từ ví dụ cho các kanji không có trong cột kanji của từ vựng (số đếm, 南, 西).
    them = [{"kanji": x["them"][0], "kana": x["them"][1], "nghia": x["them"][2], "bai": b, "vd": "", "ten": False}
            for b, v in kanji.items() for x in v if "them" in x]
    q = types.SimpleNamespace(vocab=check.vocab + them, kanji=kanji, clean=check.clean)
    hand = tay()
    res = {}
    for b in range(1, 26):
        rng = random.Random(8000 + b)
        h = hand[str(b)]
        read, write = n4.kanji_drill(b, q, bo, rng)
        sections = [
            {"part": "もじ・ごい", "title": "ことばドリル　意味", "instr": "Chọn từ tiếng Nhật có nghĩa này. Mọi từ của bài đều có một câu.", "items": n4.tu_drill(b, check, rng)},
            {"part": "もじ・ごい", "title": "漢字ドリル　読み方", "instr": "Chọn cách đọc đúng của từ gạch chân. Mọi kanji N5 xuất hiện lần đầu ở bài này đều có một câu.", "items": read},
            {"part": "もじ・ごい", "title": "漢字ドリル　書き方", "instr": "Chọn cách viết đúng. Các phương án sai dùng chữ có hình gần giống.", "items": write},
            {"part": "ぶんぽう", "title": "もんだい　文法", "instr": "Chọn từ thích hợp. Câu có ★: sắp xếp các mảnh rồi chọn mảnh ở vị trí ★.", "items": h["np"]},
            {"part": "どっかい", "title": "もんだい　" + h["doc"]["title"], "instr": "Đọc và trả lời. Đáp án thường không nằm nguyên văn trong bài: phải suy luận.", "kind": "passage", "passage": h["doc"]["passage"], "items": h["doc"]["items"]},
        ]
        sections = [s for s in sections if s["items"]]
        n4.rotate(sections, 6000 + b)
        res[b] = {"id": b, "title": f"Luyện tập bài {b}", "lessons": [b, b], "sections": sections}
    return res
