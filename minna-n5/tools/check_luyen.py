"""Kiểm tra trang Luyện tập N5: cấu trúc, mã ngữ pháp, câu ★, độ phủ từ / kanji, mẫu ngữ pháp còn ít câu."""
import collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check, luyen

errs = []
ids = {g["id"] for v in check.grammar.values() for g in v}
data = luyen.build(check)
nq, gc = collections.Counter(), collections.Counter()
for n in range(1, 6):
    for s in json.load(open(os.path.join(check.ROOT, "tests", f"test{n}.json"), encoding="utf-8"))["sections"]:
        if s.get("part") == "ぶんぽう":
            for it in s["items"]:
                gc.update(it.get("g", []))
kan = set()
for b, t in data.items():
    errs += [f"bài {b}: {e}" for e in check.star_errors(t)]
    for s in t["sections"]:
        nq[s["title"].split("　")[0]] += len(s["items"])
        for it in s["items"]:
            if len(set(it["o"])) != 4:
                errs.append(f"bài {b}: phương án trùng hoặc thiếu: {it['q'][:30]} {it['o']}")
            if not 0 <= it["a"] < 4:
                errs.append(f"bài {b}: đáp án ngoài phạm vi: {it['q'][:30]}")
            for g in it.get("g", []):
                if g not in ids:
                    errs.append(f"bài {b}: mã ngữ pháp lạ {g}")
            if s["part"] == "ぶんぽう":
                gc.update(it.get("g", []))
    tu = t["sections"][0]["items"]
    req = [r for r in check.vocab if int(r["bai"]) == b]
    if len(tu) != len(req):
        errs.append(f"bài {b}: từ {len(tu)}/{len(req)}")
ks = json.load(open(os.path.join(check.ROOT, "kanji-n5.json"), encoding="utf-8"))
for b, v in ks.items():
    secs = {s["title"]: len(s["items"]) for s in data[int(b)]["sections"]}
    if secs.get("漢字ドリル　読み方", 0) != len(v) or secs.get("漢字ドリル　書き方", 0) != len(v):
        errs.append(f"bài {b}: kanji {len(v)}, đọc {secs.get('漢字ドリル　読み方', 0)}, viết {secs.get('漢字ドリル　書き方', 0)}")
print("Số câu:", dict(nq), "tổng", sum(nq.values()))
gs = [g["id"] for v in check.grammar.values() for g in v]
print("Ngữ pháp sau khi thêm: 0 câu", sum(gc[g] == 0 for g in gs), "| 1 câu", sum(gc[g] == 1 for g in gs), "| ≥2 câu", sum(gc[g] >= 2 for g in gs), "/", len(gs))
print(f"{len(errs)} lỗi")
for e in errs[:40]:
    print(" ", e)
sys.exit(1 if errs else 0)
