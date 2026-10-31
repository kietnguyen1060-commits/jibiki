"""Gộp dữ liệu N4 (từ vựng, kanji, ngữ pháp, 25 đề) vào template thành một trang HTML.

Cách dùng: py build.py  → ghi ra ../dist/minna-n4.html
"""
import json, os, random, sys, importlib.util

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data")

spec = importlib.util.spec_from_file_location("check", os.path.join(HERE, "check.py"))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

vocab = {}
for r in check.vocab:
    vocab.setdefault(r["bai"], []).append([r["kanji"], r["kana"], r["nghia"], r["vd"], r["vdn"], r["phan"], 1 if r["ten"] else 0])

tests, coverage = {}, {}
for b in range(26, 51):
    t = json.load(open(os.path.join(DATA, "tests", f"test{b}.json"), encoding="utf-8"))
    # Đảo vị trí phương án để đáp án đúng chia đều 4 vị trí (cố định theo seed).
    rng = random.Random(4000 + b)
    items = [it for s in t["sections"] for it in s["items"] if "o" in it]
    slots = [i % 4 for i in range(len(items))]
    rng.shuffle(slots)
    for it, target in zip(items, slots):
        k = len(it["o"])
        shift = (target % k - it["a"]) % k
        if shift:
            it["o"] = it["o"][-shift:] + it["o"][:-shift]
        it["a"] = (it["a"] + shift) % k
    text, ktext, gram = check.pools(t)
    req = [r for r in check.vocab if int(r["bai"]) == b and not r["ten"]]
    used = sum(1 for r in req if any(all(p in text for p in c) for c in check.candidates(r)))
    gids = [g["id"] for g in check.grammar[str(b)]]
    ks = [x["k"] for x in check.kanji.get(str(b), [])]
    coverage[b] = {"vocab": [used, len(req)], "grammar": [sum(g in gram for g in gids), len(gids)],
                   "kanji": [sum(k in ktext for k in ks), len(ks)]}
    tests[b] = t

# So sánh ngữ pháp N5 – N4: dùng chung một tệp cho cả hai trang.
so_sanh = json.load(open(os.path.join(HERE, "..", "data", "so-sanh-n5-n4.json"), encoding="utf-8"))
payload = json.dumps({"soSanh": so_sanh, "vocab": vocab, "kanji": check.kanji, "grammar": check.grammar, "tests": tests, "coverage": coverage},
                     ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
out = tpl.replace("/*__DATA__*/{}", payload)
os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
dst = os.path.join(ROOT, "dist", "minna-n4.html")
open(dst, "w", encoding="utf-8").write(out)
nq = sum(len(s["items"]) for t in tests.values() for s in t["sections"])
print("wrote", dst, f"{len(out) / 1024:.0f} KB", "questions:", nq)
print("vocab", sum(c["vocab"][0] for c in coverage.values()), "/", sum(c["vocab"][1] for c in coverage.values()),
      "grammar", sum(c["grammar"][0] for c in coverage.values()), "/", sum(c["grammar"][1] for c in coverage.values()),
      "kanji", sum(c["kanji"][0] for c in coverage.values()), "/", sum(c["kanji"][1] for c in coverage.values()))
