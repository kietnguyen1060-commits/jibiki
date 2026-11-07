"""Check the practice pages: structure, grammar codes, ★ questions, word / kanji coverage, and reading answers not copied verbatim."""
import collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check, luyen

errs = []
ids = {g["id"] for v in check.grammar.values() for g in v}
hand = luyen.tay()
data = luyen.build(check)
nq = collections.Counter()
for b, t in data.items():
    if str(b) not in hand:
        errs.append(f"bài {b}: thiếu phần soạn tay")
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
            # Names and short numbers can't be avoided; only flag long answers copied from the passage.
            if s.get("passage") and len(check.strip(it["o"][it["a"]])) > 8 and check.strip(it["o"][it["a"]]) in check.strip(s["passage"]):
                errs.append(f"bài {b}: đáp án chép nguyên văn: {it['o'][it['a']]}")
    req = [r for r in check.vocab if int(r["bai"]) == b and not r["ten"]]
    tu = len(t["sections"][0]["items"])
    ks = len(check.kanji.get(str(b), []))
    rd, wr = len(t["sections"][1]["items"]), len(t["sections"][2]["items"])
    if tu != len(req) or rd != ks or wr != ks:
        errs.append(f"bài {b}: phủ chưa đủ: từ {tu}/{len(req)}, đọc {rd}/{ks}, viết {wr}/{ks}")
print("Số câu:", dict(nq), "tổng", sum(nq.values()))
print(f"{len(errs)} lỗi")
for e in errs[:40]:
    print(" ", e)
sys.exit(1 if errs else 0)
