"""Add a handwriting board to the back of every TOEIC card (note type "TOEIC EZ Vocab") through AnkiConnect.

The board sits under the card with a strip showing the word and its meaning, so all three are visible while writing.
It has handwriting guide lines, pen pressure, undo and clear. Safe to rerun: the block between the markers is replaced.
Usage: py toeic_bang_viet.py [--preview out.html] [--remove]
The original templates are saved to _build/toeic-template-backup.json before the first change.
"""
import json, os, re, sys, urllib.request

MODEL = "TOEIC EZ Vocab"
TEMPLATE = "EN -> VN"
HERE = os.path.dirname(os.path.abspath(__file__))
BACKUP = os.path.join(HERE, "..", "_build", "toeic-template-backup.json")
START, END = "<!-- jibiki-bang-viet -->", "<!-- /jibiki-bang-viet -->"
CSS_START, CSS_END = "/* jibiki-bang-viet */", "/* /jibiki-bang-viet */"

BOARD = START + """
<div class="wb">
  <div class="wb-ref"><span class="wb-word">{{Word}}</span><span class="wb-mean">{{Meaning}}</span></div>
  <div class="wb-box"><canvas class="wb-cv"></canvas></div>
  <div class="wb-bar"><span class="wb-hint">Luyện viết từ mới</span><button type="button" class="wb-undo">↶ Hoàn tác nét</button><button type="button" class="wb-clear">Xoá bảng</button></div>
</div>
<script>
(function () {
  var all = document.querySelectorAll(".wb"), wb = all[all.length - 1];
  if (!wb || wb.dataset.on) return;
  wb.dataset.on = "1";
  var cv = wb.querySelector(".wb-cv"), box = wb.querySelector(".wb-box"), ctx = cv.getContext("2d");
  var strokes = [], cur = null, W = 0, H = 0;
  function lines() {
    var rows = 2, rh = H / rows;
    for (var r = 0; r < rows; r++) {
      var top = r * rh + rh * 0.18, base = r * rh + rh * 0.78, mid = (top + base) / 2;
      ctx.setLineDash([]); ctx.strokeStyle = "#c9d6e8"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(0, top); ctx.lineTo(W, top); ctx.stroke();
      ctx.strokeStyle = "#e3b3b3"; ctx.lineWidth = 1.4;
      ctx.beginPath(); ctx.moveTo(0, base); ctx.lineTo(W, base); ctx.stroke();
      ctx.setLineDash([6, 6]); ctx.strokeStyle = "#d5dde8"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(0, mid); ctx.lineTo(W, mid); ctx.stroke();
    }
    ctx.setLineDash([]);
  }
  function seg(a, b) {
    ctx.lineWidth = 1.6 + (a.p + b.p) * 1.8;
    ctx.beginPath(); ctx.moveTo(a.x * W, a.y * H); ctx.lineTo(b.x * W, b.y * H); ctx.stroke();
  }
  function draw() {
    ctx.clearRect(0, 0, W, H); lines();
    ctx.strokeStyle = "#1a2433"; ctx.lineCap = "round"; ctx.lineJoin = "round";
    strokes.forEach(function (s) {
      if (s.length === 1) seg(s[0], s[0]);
      for (var i = 1; i < s.length; i++) seg(s[i - 1], s[i]);
    });
  }
  function size() {
    var w = box.clientWidth, h = box.clientHeight, d = window.devicePixelRatio || 1;
    if (!w || !h) return;
    W = w; H = h;
    cv.width = Math.round(w * d); cv.height = Math.round(h * d);
    cv.style.width = w + "px"; cv.style.height = h + "px";
    ctx.setTransform(d, 0, 0, d, 0, 0);
    draw();
  }
  function pt(e) {
    var r = cv.getBoundingClientRect();
    return { x: (e.clientX - r.left) / W, y: (e.clientY - r.top) / H, p: e.pressure > 0 && e.pointerType === "pen" ? e.pressure : 0.5 };
  }
  cv.addEventListener("pointerdown", function (e) {
    e.preventDefault();
    try { cv.setPointerCapture(e.pointerId); } catch (er) {}
    cur = [pt(e)]; strokes.push(cur); draw();
  });
  cv.addEventListener("pointermove", function (e) {
    if (!cur) return;
    var evs = e.getCoalescedEvents ? e.getCoalescedEvents() : [];
    (evs.length ? evs : [e]).forEach(function (ev) {
      var p = pt(ev), last = cur[cur.length - 1];
      cur.push(p);
      ctx.strokeStyle = "#1a2433"; ctx.lineCap = "round"; seg(last, p);
    });
  });
  function up() { cur = null; }
  cv.addEventListener("pointerup", up);
  cv.addEventListener("pointercancel", up);
  wb.querySelector(".wb-undo").addEventListener("click", function () { strokes.pop(); draw(); });
  wb.querySelector(".wb-clear").addEventListener("click", function () { strokes = []; draw(); });
  if (window.ResizeObserver) new ResizeObserver(size).observe(box);
  else window.addEventListener("resize", size);
  size();
})();
</script>
""" + END

CSS = CSS_START + """
.wb { margin: 22px auto 6px; width: 100%; max-width: 980px; text-align: left; }
.wb-ref { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; padding: 8px 14px;
          border: 1px solid #d8dee8; border-bottom: none; border-radius: 12px 12px 0 0; background: #f2f5fa; }
.wb-word { font-size: 24px; font-weight: 700; color: #1a1a1a; }
.wb-mean { font-size: 18px; color: #1565c0; }
.wb-box { height: 300px; border: 1px solid #d8dee8; background: #ffffff; touch-action: none;
          cursor: crosshair; }
.wb-cv { display: block; touch-action: none; }
.wb-bar { display: flex; gap: 8px; align-items: center; padding: 6px 10px; border: 1px solid #d8dee8; border-top: none;
          border-radius: 0 0 12px 12px; background: #f2f5fa; }
.wb-hint { flex: 1; font-size: 13px; color: #8a8a8a; }
.wb-bar button { font: inherit; font-size: 14px; padding: 4px 12px; border: 1px solid #c9d1dd; border-radius: 8px;
                 background: #fff; color: #333; cursor: pointer; }
.wb-bar button:hover { border-color: #1565c0; color: #1565c0; }
.nightMode .wb-ref, .night_mode .wb-ref, .nightMode .wb-bar, .night_mode .wb-bar { background: #353b45; border-color: #4a5160; }
.nightMode .wb-word, .night_mode .wb-word { color: #f0f0f0; }
.nightMode .wb-mean, .night_mode .wb-mean { color: #7fb2f0; }
.nightMode .wb-box, .night_mode .wb-box { border-color: #4a5160; }
.nightMode .wb-bar button, .night_mode .wb-bar button { background: #2b2f36; color: #ddd; border-color: #4a5160; }
@media (max-width: 600px) { .wb-box { height: 240px; } }
""" + CSS_END


def call(action, **params):
    req = urllib.request.Request("http://127.0.0.1:8765", json.dumps({"action": action, "version": 6, "params": params}).encode("utf-8"))
    r = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
    if r.get("error"):
        raise RuntimeError(r["error"])
    return r["result"]


def strip(text, a, b):
    return re.sub(r"\s*" + re.escape(a) + r".*?" + re.escape(b), "", text, flags=re.S)


def main():
    args = sys.argv[1:]
    tpl = call("modelTemplates", modelName=MODEL)
    css = call("modelStyling", modelName=MODEL)["css"]
    if not os.path.exists(BACKUP):
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        json.dump({"templates": tpl, "css": css}, open(BACKUP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("backup:", os.path.abspath(BACKUP))
    back = strip(tpl[TEMPLATE]["Back"], START, END).rstrip()
    css = strip(css, CSS_START, CSS_END).rstrip()
    if "--remove" not in args:
        back += "\n\n" + BOARD + "\n"
        css += "\n\n" + CSS + "\n"
    if "--preview" in args:
        out = args[args.index("--preview") + 1]
        cid = call("findCards", query=f'"note:{MODEL}"')[0]
        f = {k: v["value"] for k, v in call("cardsInfo", cards=[cid])[0]["fields"].items()}
        html = back.replace("{{FrontSide}}", tpl[TEMPLATE]["Front"])
        html = re.sub(r"\{\{[#/^][^}]+\}\}", "", html)
        html = re.sub(r"\{\{([^}]+)\}\}", lambda m: f.get(m.group(1).strip(), ""), html)
        html = re.sub(r"\[sound:[^\]]+\]", "▶", html)
        open(out, "w", encoding="utf-8").write(f"<!doctype html><meta charset='utf-8'><style>{css}</style><body class='card card1'>{html}</body>")
        print("preview:", out)
        return
    call("updateModelTemplates", model={"name": MODEL, "templates": {TEMPLATE: {"Front": tpl[TEMPLATE]["Front"], "Back": back}}})
    call("updateModelStyling", model={"name": MODEL, "css": css})
    print("removed" if "--remove" in args else "updated", MODEL)


if __name__ == "__main__":
    main()
