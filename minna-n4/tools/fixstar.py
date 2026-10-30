"""Đặt đáp án câu ★ theo câu hoàn chỉnh ("full") và viết lại lời giải.

Cách dùng: py fixstar.py [số bài ...]
"""
import json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "tests")
ns = [int(a) for a in sys.argv[1:]] or range(26, 51)
for n in ns:
    p = os.path.join(ROOT, f"test{n}.json")
    if not os.path.exists(p):
        continue
    t = json.load(open(p, encoding="utf-8"))
    changed = 0
    for sec in t["sections"]:
        for it in sec.get("items", []):
            if "full" not in it or "★" not in it["q"]:
                continue
            full = it["full"].replace(" ", "")
            pos = [full.find(o.replace(" ", "")) for o in it["o"]]
            if -1 in pos:
                print(f"bài {n}: mảnh không có trong câu: {it['q'][:20]}")
                continue
            order = [o for _, o in sorted(zip(pos, it["o"]))]
            slot = re.findall(r"＿＿|★", it["q"]).index("★")
            a = it["o"].index(order[slot])
            e = " ".join(f"{o}{'(★)' if i == slot else ''}" for i, o in enumerate(order)) + f" → ★ = {order[slot]}."
            if it["a"] != a or it.get("e") != e:
                it["a"], it["e"] = a, e
                changed += 1
    json.dump(t, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if changed:
        print(f"bài {n}: sửa {changed} câu ★")
