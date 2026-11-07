"""Merge the data (vocabulary, grammar, 5 tests) into the template as a single HTML page.

Usage: py build.py  → writes ../dist/minna-n5.html
"""
import json, os, random, sys, importlib.util
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import luyen

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data")

spec = importlib.util.spec_from_file_location("check", os.path.join(HERE, "check.py"))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

vocab = {}
for r in check.vocab:
    vocab.setdefault(r["bai"], []).append([r["kanji"], r["kana"], r["nghia"], r["vd"], r["vdn"]])

tests, coverage = [], []
for n in range(1, 6):
    t = json.load(open(os.path.join(DATA, "tests", f"test{n}.json"), encoding="utf-8"))
    # Rotate the options so correct answers spread evenly over the 4 positions (fixed by the seed).
    rng = random.Random(1000 + n)
    items = [it for s in t["sections"] for it in s["items"] if "o" in it]
    slots = [i % 4 for i in range(len(items))]
    rng.shuffle(slots)
    for it, target in zip(items, slots):
        k = len(it["o"])
        shift = (target - it["a"]) % k
        it["o"] = it["o"][-shift:] + it["o"][:-shift] if shift else it["o"]
        it["a"] = target % k
        assert it["o"][it["a"]] is not None
    lo, hi = t["lessons"]
    text, gram = check.test_text(t)
    total = sum(1 for r in check.vocab if lo <= int(r["bai"]) <= hi)
    used = sum(1 for r in check.vocab if lo <= int(r["bai"]) <= hi
               and any(all(p in text for p in c) for c in check.candidates(r)))
    gids = [g["id"] for b in range(lo, hi + 1) for g in check.grammar[str(b)]]
    coverage.append({"id": n, "vocab": [used, total], "grammar": [sum(g in gram for g in gids), len(gids)]})
    tests.append(t)

# N5–N4 grammar comparison: one shared file for both pages.
so_sanh = json.load(open(os.path.join(HERE, "..", "..", "minna-n4", "data", "so-sanh-n5-n4.json"), encoding="utf-8"))
payload = json.dumps({"soSanh": so_sanh, "vocab": vocab, "grammar": check.grammar, "tests": tests, "coverage": coverage, "luyen": luyen.build(check)},
                     ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
out = tpl.replace("/*__DATA__*/{}", payload)
os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
dst = os.path.join(ROOT, "dist", "minna-n5.html")
open(dst, "w", encoding="utf-8").write(out)
print("wrote", dst, f"{len(out) / 1024:.0f} KB")
for c in coverage:
    print(c)
