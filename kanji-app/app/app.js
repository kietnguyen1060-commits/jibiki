/* 字引 (Jibiki) — bảng trắng nhận diện chữ (KanjiCanvas), thẻ kanji kiểu Look and Learn,
   bộ đề Minna, và học thẻ trực tiếp trên bộ sưu tập Anki qua AnkiConnect. */
(function () {
  "use strict";
  const D = window.APPDATA, STROKES = window.STROKES || {};
  const $ = (s, el = document) => el.querySelector(s);
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const isKanji = c => /[\u3400-\u9fff々]/.test(c);
  const fold = s => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "d").toLowerCase();
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  };

  /* ---------- Chỉ mục dữ liệu ---------- */
  const kllByChar = new Map(), kllByN = new Map();
  D.kll.forEach(x => { kllByChar.set(x.k, x); kllByN.set(x.n, x); });
  const addTo = (map, key, v) => { if (!map.has(key)) map.set(key, []); map.get(key).push(v); };
  const wordsByChar = new Map(), sentsByChar = new Map(), minnaByChar = new Map();
  D.words.forEach(w => new Set([...(w[0] + w[3])].filter(isKanji)).forEach(c => addTo(wordsByChar, c, w)));
  D.sents.forEach(s => new Set([...s[1]].filter(isKanji)).forEach(c => addTo(sentsByChar, c, s)));
  D.minna.forEach(m => new Set([...m[0]].filter(isKanji)).forEach(c => addTo(minnaByChar, c, m)));
  const searchIndex = D.kll.map(x => ({ x, hay: fold([x.k, x.hv, x.nghia, x.on, x.kun, x.n].join(" ")) }));

  /* ---------- Kết nối Anki (AnkiConnect) ---------- */
  const anki = {
    ok: false,
    async call(action, params = {}) {
      const r = await fetch("http://127.0.0.1:8765", { method: "POST", body: JSON.stringify({ action, version: 6, params }) });
      const j = await r.json();
      if (j.error) throw new Error(j.error);
      return j.result;
    },
    async ping() {
      try { await this.call("version"); this.ok = true; } catch (e) { this.ok = false; }
      const pill = $("#ankiPill");
      pill.className = "anki-pill " + (this.ok ? "on" : "off");
      pill.textContent = this.ok ? "Anki: đã kết nối" : "Anki: chưa mở";
      return this.ok;
    }
  };

  /* ---------- Âm thanh ---------- */
  let audio = null;
  function play(file) {
    if (!file) return;
    if (audio) audio.pause();
    audio = new Audio("/media/" + encodeURIComponent(file));
    audio.play().catch(() => {});
  }
  document.addEventListener("click", e => {
    const b = e.target.closest("[data-play]");
    if (b) { e.preventDefault(); play(b.dataset.play); }
  });

  /* ---------- Nét viết (KanjiVG) ---------- */
  function strokeSvg(paths, upto, size, whole) {
    let s = `<svg viewBox="0 0 109 109" width="${size}" height="${size}" aria-hidden="true">`;
    for (let i = 0; i < upto; i++) s += `<path class="${whole ? "stroke-anim" : i === upto - 1 ? "stroke-new" : "stroke-done"}" d="${paths[i]}"/>`;
    return s + "</svg>";
  }
  function animate(box, paths) {
    box.innerHTML = `<svg viewBox="0 0 109 109" aria-label="Thứ tự nét">${paths.map(d => `<path class="stroke-anim" d="${d}"/>`).join("")}</svg>`;
    const els = [...box.querySelectorAll("path")];
    els.forEach(p => { const L = p.getTotalLength(); p.style.strokeDasharray = L; p.style.strokeDashoffset = L; });
    let i = 0;
    (function next() {
      if (i >= els.length || !box.isConnected) return;
      const p = els[i++], L = parseFloat(p.style.strokeDasharray);
      p.animate([{ strokeDashoffset: L }, { strokeDashoffset: 0 }], { duration: Math.max(260, L * 7), fill: "forwards", easing: "ease-in-out" }).onfinish = next;
    })();
  }

  /* ---------- Bảng vẽ dùng chung (bảng trắng tra cứu và bảng tập viết khi học thẻ) ----------
     Pointer Events, nét làm mượt bằng đường cong bậc hai, dày theo lực bút, nét lưu theo toạ độ 300×300
     kèm thời điểm từng điểm (để nhận diện chữ viết tay). */
  const SIZE = 300;
  function makeBoard(canvas, onStroke) {
    const ctx = canvas.getContext("2d"), strokes = [];
    let cur = null, guide = null;
    function fit() {
      const dpr = Math.max(1, window.devicePixelRatio || 1), css = canvas.getBoundingClientRect().width || SIZE;
      canvas.width = Math.round(css * dpr); canvas.height = Math.round(css * dpr);
      ctx.setTransform(canvas.width / SIZE, 0, 0, canvas.height / SIZE, 0, 0);
      redraw();
    }
    const inkColor = () => getComputedStyle(canvas).getPropertyValue("--ink-draw").trim() || "#1b1b1b";
    function drawStroke(pts, color) {
      ctx.strokeStyle = ctx.fillStyle = color;
      ctx.lineCap = ctx.lineJoin = "round";
      if (pts.length === 1) { ctx.beginPath(); ctx.arc(pts[0].x, pts[0].y, pts[0].w / 2, 0, Math.PI * 2); ctx.fill(); return; }
      // Đi qua trung điểm các đoạn, lấy điểm gốc làm điểm điều khiển → đường cong liền, không gãy khúc.
      for (let i = 1; i < pts.length; i++) {
        const a = pts[i - 1], b = pts[i], p0 = i === 1 ? a : { x: (pts[i - 2].x + a.x) / 2, y: (pts[i - 2].y + a.y) / 2 };
        const m = i === pts.length - 1 ? b : { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
        ctx.lineWidth = (a.w + b.w) / 2;
        ctx.beginPath(); ctx.moveTo(p0.x, p0.y); ctx.quadraticCurveTo(a.x, a.y, m.x, m.y); ctx.stroke();
      }
    }
    function redraw() {
      ctx.clearRect(0, 0, SIZE, SIZE);
      // Nét mẫu đặt chồng sau khi kiểm tra: xanh nhạt là phần khớp, đỏ là đoạn bạn thiếu hoặc viết lệch.
      if (guide) guide.forEach(g => {
        ctx.lineWidth = 7; ctx.lineCap = ctx.lineJoin = "round";
        ctx.strokeStyle = "rgba(52, 120, 220, .28)";
        ctx.beginPath(); g.pts.forEach(([x, y], j) => j ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.stroke();
        ctx.strokeStyle = "rgba(214, 48, 49, .6)";
        ctx.beginPath();
        g.pts.forEach(([x, y], j) => { if (!g.miss[j]) return; if (j && g.miss[j - 1]) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
        ctx.stroke();
      });
      const ink = inkColor();
      strokes.forEach((s, i) => {
        drawStroke(s, ink);
        ctx.font = "600 12px system-ui, sans-serif"; ctx.fillStyle = "#c0392b";
        ctx.fillText(String(i + 1), s[0].x + 6, s[0].y - 6);
      });
      if (cur) drawStroke(cur, ink);
    }
    function toPad(e) {
      const r = canvas.getBoundingClientRect(), k = SIZE / r.width;
      const pressure = e.pointerType === "pen" && e.pressure > 0 ? e.pressure : 0.5;
      return { x: (e.clientX - r.left) * k, y: (e.clientY - r.top) * k, w: 3 + pressure * 4.5, t: Math.round(performance.now()) };
    }
    function addPoint(p) {
      const last = cur[cur.length - 1];
      const dx = p.x - last.x, dy = p.y - last.y;
      if (dx * dx + dy * dy < 2.25) return;               // bỏ rung tay < 1.5px
      // Lọc nhẹ để nét không bị răng cưa khi chuột/cảm ứng báo điểm thô.
      cur.push({ x: last.x + dx * 0.6, y: last.y + dy * 0.6, w: last.w * 0.6 + p.w * 0.4, t: p.t });
    }
    canvas.addEventListener("pointerdown", e => {
      if (e.button > 0) return;
      e.preventDefault();
      canvas.setPointerCapture(e.pointerId);
      cur = [toPad(e)];
      redraw();
    });
    canvas.addEventListener("pointermove", e => {
      if (!cur) return;
      const evs = e.getCoalescedEvents ? e.getCoalescedEvents() : [e];
      (evs.length ? evs : [e]).forEach(ev => addPoint(toPad(ev)));
      redraw();
    });
    function endStroke(e) {
      if (!cur) return;
      if (e && e.type === "pointerup") { const p = toPad(e), l = cur[cur.length - 1]; if (Math.hypot(p.x - l.x, p.y - l.y) > 1) cur.push(p); }
      strokes.push(cur);
      const s = cur;
      cur = null;
      redraw();
      if (onStroke) onStroke(s);
    }
    canvas.addEventListener("pointerup", endStroke);
    canvas.addEventListener("pointercancel", endStroke);
    window.addEventListener("resize", () => { if (canvas.isConnected) fit(); });
    fit();
    return {
      strokes, fit,
      undo() { strokes.pop(); redraw(); },
      clear() { strokes.length = 0; guide = null; redraw(); },
      showGuide(g) { guide = g; redraw(); },
    };
  }
  // Nhận diện chữ viết tay của Google (qua /api/viet của server): không phụ thuộc thứ tự nét, số nét, nét viết liền.
  // Trả về danh sách chữ gợi ý (một ký tự Nhật mỗi gợi ý); lỗi mạng thì ném lỗi để nơi gọi dùng phương án khác.
  const isOneJa = c => [...c].length === 1 && /[぀-ヿ㐀-鿿々]/.test(c);
  async function readInk(strokes) {
    const t0 = strokes[0][0].t || 0;
    const ink = strokes.map(s => [s.map(p => Math.round(p.x)), s.map(p => Math.round(p.y)), s.map(p => Math.max(0, (p.t || 0) - t0))]);
    const r = await fetch("/api/viet", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ink }) });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return (await r.json()).filter(isOneJa);
  }

  /* ---------- Bảng trắng tra cứu ----------
     Vẽ trên #pad; #can ẩn chỉ giữ dữ liệu nét cho KanjiCanvas (nhận diện trên máy, dùng khi mất mạng). */
  KanjiCanvas.init("can");
  let recTimer = null;
  const board = makeBoard($("#pad"), s => {
    KanjiCanvas.recordedPattern_can.push(s.map(p => [Math.round(p.x), Math.round(p.y)]));
    clearTimeout(recTimer); recTimer = setTimeout(recognize, 30);
  });
  const strokes = board.strokes;
  /* Nhận diện: hiện ngay kết quả KanjiCanvas (chạy trên máy, so từng nét), rồi thay bằng kết quả nhận diện
     chữ viết tay của Google (qua /api/viet của server) — không phụ thuộc thứ tự nét, số nét hay nét viết liền.
     Mất mạng thì giữ kết quả KanjiCanvas. */
  let recSeq = 0;
  async function recognize() {
    const seq = ++recSeq;
    if (!strokes.length) { showCands([]); return; }
    const offline = (KanjiCanvas.recognize("can") || "").trim().split(/\s+/).filter(Boolean);
    showCands(offline, "offline");
    try {
      const online = await readInk(strokes);
      if (seq !== recSeq || !online.length) return;   // đã vẽ thêm / xoá trong lúc chờ
      showCands([...new Set([...online, ...offline])].slice(0, 10), "google");
    } catch (e) { /* giữ kết quả KanjiCanvas */ }
  }
  function showCands(list, src) {
    const el = $("#cands");
    if (!list.length) { el.innerHTML = `<span class="muted">Chữ gợi ý sẽ hiện ở đây.</span>`; return; }
    el.innerHTML = list.map(c => `<button class="cand" type="button" data-k="${esc(c)}" title="${kllByChar.has(c) ? "Có trong Kanji Look and Learn" : ""}">${esc(c)}${kllByChar.has(c) ? '<span class="dot"></span>' : ""}</button>`).join("")
      + `<span class="cand-src" title="${src === "google" ? "Nhận diện chữ viết tay của Google: không cần đúng thứ tự hay số nét" : "Nhận diện trên máy (KanjiCanvas): đang chờ Google hoặc không có mạng"}">${src === "google" ? "Google" : "trên máy"}</span>`;
  }
  $("#undo").addEventListener("click", () => { board.undo(); KanjiCanvas.recordedPattern_can.pop(); recognize(); });
  $("#clear").addEventListener("click", () => { board.clear(); KanjiCanvas.recordedPattern_can.length = 0; showCands([]); });
  document.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) { e.preventDefault(); $("#undo").click(); }
  });
  $("#cands").addEventListener("click", e => { const b = e.target.closest("[data-k]"); if (b) go("lookup/" + b.dataset.k); });

  /* ---------- Tìm bằng chữ gõ ---------- */
  $("#q").addEventListener("input", e => {
    const v = e.target.value.trim(), res = $("#results");
    if (!v) { res.innerHTML = ""; return; }
    const ks = [...v].filter(isKanji);
    let hits = [];
    if (ks.length) hits = [...new Set(ks)].map(c => kllByChar.get(c) || { k: c, n: null, hv: "", nghia: "(ngoài KLL)" });
    else {
      const f = fold(v), low = v.toLowerCase();
      // Ưu tiên: đúng âm Hán Việt có dấu → đúng âm bỏ dấu → nghĩa có dấu → còn lại.
      const score = x => {
        const hv = x.hv.toLowerCase().split(/[,、\s]+/);
        if (hv.includes(low)) return 0;
        if (hv.map(fold).includes(f)) return 1;
        if (x.nghia.toLowerCase().split(/[,;、]\s*/).includes(low)) return 2;
        if (x.nghia.toLowerCase().includes(low)) return 3;
        return 4;
      };
      hits = /^\d+$/.test(v) ? [kllByN.get(+v)].filter(Boolean)
        : searchIndex.filter(s => s.hay.includes(f)).map(s => s.x).sort((a, b) => score(a) - score(b) || a.n - b.n);
    }
    res.innerHTML = hits.slice(0, 40).map(x => `<button type="button" data-k="${esc(x.k)}"><span class="rk">${esc(x.k)}</span><span><b>${esc(x.hv)}</b> ${esc(x.nghia)} ${x.n ? `<small>· số ${noLabel(x)}</small>` : ""}</span></button>`).join("") || `<span class="muted">Không tìm thấy.</span>`;
  });
  $("#q").addEventListener("keydown", e => { if (e.key === "Enter") { const b = $("#results button"); if (b) b.click(); } });
  $("#results").addEventListener("click", e => { const b = e.target.closest("[data-k]"); if (b) go("lookup/" + b.dataset.k); });

  function pushRecent(ch) {
    const r = store.get("tk-recent", []).filter(c => c !== ch);
    r.unshift(ch); store.set("tk-recent", r.slice(0, 24)); renderRecent();
  }
  function renderRecent() {
    const r = store.get("tk-recent", []);
    $("#recentLabel").hidden = !r.length;
    $("#recent").innerHTML = r.map(c => `<button type="button" data-k="${esc(c)}">${esc(c)}</button>`).join("");
  }
  $("#recent").addEventListener("click", e => { const b = e.target.closest("[data-k]"); if (b) go("lookup/" + b.dataset.k); });

  /* ---------- Thẻ kanji kiểu Look and Learn ---------- */
  // Chữ bổ sung từ Minna mang số 1001+ trong dữ liệu, hiển thị là +1, +2… như trên thẻ Anki.
  const noLabel = x => x.n > 2000 ? "N3·" + (x.n - 2000) : x.n > 1000 ? "+" + (x.n - 1000) : x.n;
  const hexOf = ch => ch.codePointAt(0).toString(16).padStart(5, "0");
  // Tranh → chữ và hình thành phần màu, cùng các tệp đã đưa vào Anki: tranh lấy đúng tệp đang gắn
  // ở trường "Hình" của thẻ (sách KLL, sách N3–N2 hoặc tranh OpenMoji).
  const picOf = ch => (kllByChar.get(ch) || {}).img || `kll_pic_${hexOf(ch)}.svg`;
  const figHtml = ch => `<img class="comp" src="/media/${picOf(ch)}" alt="Tranh gợi nhớ chữ ${esc(ch)}"><img class="comp" src="/media/kll_comp_${hexOf(ch)}.svg" alt="Các thành phần ghép thành chữ ${esc(ch)}">`;
  function splitReads(s) { return String(s || "").split(/[、,]\s*/).filter(Boolean); }
  function minnaLink(m) {
    const book = m[3] <= 25 ? "n5" : "n4";
    return `<a href="#minna-${book}/bai-${m[3]}" title="${esc(m[2])}"><span class="t">${esc(m[0])}</span><small>${esc(m[1])} · Bài ${m[3]}</small></a>`;
  }
  function renderEmpty() {
    $("#card").innerHTML = `<div class="empty"><b>後</b>Viết một chữ lên bảng trắng hoặc gõ chữ, âm Hán Việt, nghĩa, cách đọc hay số thứ tự trong sách để mở thẻ kanji.</div>`;
  }
  function renderCard(ch) {
    const x = kllByChar.get(ch), paths = STROKES[ch] || [], area = $("#card");
    pushRecent(ch);
    const words = wordsByChar.get(ch) || [], sents = sentsByChar.get(ch) || [], minna = minnaByChar.get(ch) || [];
    let h = "";
    if (x) {
      const prev = kllByN.get(x.n - 1), next = kllByN.get(x.n + 1);
      h += `<div class="nav-book">${prev ? `<a class="btn small" href="#lookup/${encodeURIComponent(prev.k)}">‹ ${noLabel(prev)} ${esc(prev.k)}</a>` : "<span></span>"}
        <span class="where">${x.n > 2000 ? `Sách N3–N2 tiếng Việt · ${noLabel(x)} · ${esc(x.bai)}` : x.n > 1000 ? `Bổ sung theo Minna · ${noLabel(x)} · bài ${esc(x.bai)}` : `Kanji Look and Learn · số ${x.n} · bài ${esc(x.bai)}`}</span>
        ${next ? `<a class="btn small" href="#lookup/${encodeURIComponent(next.k)}">${esc(next.k)} ${noLabel(next)} ›</a>` : "<span></span>"}</div>`;
    }
    const core = x ? x.ex.filter(e => e[3]) : [], more = x ? x.ex.filter(e => !e[3]) : [];
    h += `<div class="page" aria-label="Thẻ kanji ${esc(ch)}">
      <div class="row1">
        <div class="bigk">${x ? `<span class="no">${noLabel(x)}</span>` : ""}<div><div class="ch">${esc(ch)}</div>${x ? `<div class="mean">${esc(x.nghia)}</div><div class="hv">${esc(x.hv)}</div>` : ""}</div></div>
        <div class="anim"><div id="animBox">${x ? figHtml(ch) : paths.length ? strokeSvg(paths, paths.length, 140, true) : '<span class="muted">Chưa có dữ liệu nét</span>'}</div>
          ${paths.length ? `<button class="btn small" type="button" id="animBtn">▶ Xem cách viết</button>` : ""}</div>
        <div class="nho">${x ? `<p id="nhoText">${esc(x.nho) || '<span class="muted">Chưa có cách nhớ.</span>'}</p>${x.lq ? `<div class="lq">Liên quan: <b>${esc(x.lq)}</b></div>` : ""}`
          : `<p class="muted">Chữ này không có trong Kanji Look and Learn. Dưới đây là thứ tự nét và các từ có chứa chữ này trong bộ tài liệu của bạn.</p>`}</div>
      </div>`;
    if (x) {
      h += `<div class="row2">
        <div class="reads">${splitReads(x.on).length ? `<div class="on">${splitReads(x.on).map(esc).join("　")}</div>` : ""}${splitReads(x.kun).length ? `<div class="kun">${splitReads(x.kun).map(esc).join("　")}</div>` : ""}</div>
        <div class="ex-core">${core.map(e => `<div>${esc(e[0])}（${esc(e[1])}）<small>${esc(e[2])}</small></div>`).join("") || '<span class="muted">—</span>'}</div>
        <div class="ex-more">${more.map(e => `<div>${esc(e[0])}（${esc(e[1])}）<small>${esc(e[2])}</small></div>`).join("") || '<span class="muted">—</span>'}</div>
      </div>`;
    }
    if (paths.length) {
      h += `<div class="row3"><span class="cnt">&lt;${paths.length}&gt;</span>${paths.map((_, i) => strokeSvg(paths, i + 1, 44)).join("")}${x && x.lq ? `<span class="rad">${esc(x.lq)}</span>` : ""}</div>`;
    }
    h += `</div>`;
    if (x) h += `<section class="panel" id="ankiPanel"><h3>Thẻ Anki của chữ này <small>đồng bộ trực tiếp với bộ sưu tập</small></h3><div id="ankiBody" class="muted">Đang tải…</div></section>`;
    if (words.length) {
      h += `<section class="panel"><h3>Từ ghép <small>${words.length} từ · deck KLL Từ ghép</small></h3><div class="wlist">${words.map(w => `<div class="w">${w[7] ? `<button class="play" type="button" data-play="${esc(w[7])}" aria-label="Nghe ${esc(w[0])}">▶</button>` : ""}<div class="grow"><div class="t">${esc(w[0])}</div><div class="r">${esc(w[1])}</div><div class="m">${esc(w[2])}</div></div></div>`).join("")}</div></section>`;
    }
    if (sents.length) {
      h += `<section class="panel"><h3>Câu ví dụ <small>Workbook KLL</small></h3><div class="slist">${sents.slice(0, 12).map(s => `<div class="s">${s[5] ? `<button class="play" type="button" data-play="${esc(s[5])}" aria-label="Nghe câu">▶</button>` : ""}<div><span class="jp">${s[0].replace(/<(?!\/?span( class="hl")?>)[^>]*>/g, "")}</span><small>${esc(s[1])}（${esc(s[2])}）${esc(s[3])}</small></div></div>`).join("")}</div></section>`;
    }
    if (minna.length) {
      h += `<section class="panel"><h3>Trong Minna no Nihongo <small>${minna.length} từ · bấm để mở bài</small></h3><div class="minna-links">${minna.slice(0, 40).map(minnaLink).join("")}</div></section>`;
    }
    area.innerHTML = h;
    const btn = $("#animBtn");
    if (btn) btn.addEventListener("click", () => {
      // Bấm lần nữa để quay lại hình thành phần.
      if (x && btn.dataset.on) { delete btn.dataset.on; btn.textContent = "▶ Xem cách viết"; $("#animBox").innerHTML = figHtml(ch); return; }
      animate($("#animBox"), paths);
      if (x) { btn.dataset.on = "1"; btn.textContent = "◧ Hình thành phần"; }
    });
    if (x) loadAnkiPanel(x);
    window.scrollTo({ top: 0 });
  }

  const KLL_TEMPLATES = ["Kanji → Nghĩa/Âm", "Nghĩa → Kanji"];
  function cardState(c) {
    if (c.queue === -1) return ['<span class="st sus">Tạm ngưng</span>', "sus"];
    if (c.type === 0) return ['<span class="st new">Mới</span>', "new"];
    if (c.type === 1 || c.type === 3) return ['<span class="st learn">Đang học</span>', "learn"];
    return [`<span class="st rev">Ôn tập · ${c.interval} ngày</span>`, "rev"];
  }
  async function loadAnkiPanel(x) {
    const body = $("#ankiBody");
    if (!body) return;
    if (!(await anki.ping())) { body.innerHTML = `Mở Anki (đã cài AnkiConnect) để xem lịch ôn, học thẻ và sửa cách nhớ của chữ này.`; return; }
    try {
      const [note] = await anki.call("notesInfo", { notes: [x.nid] });
      if (!note || !note.noteId) { body.textContent = "Không tìm thấy ghi chú của chữ này trong Anki."; return; }
      const nhoLive = (note.fields["Cách nhớ"] || {}).value || "";
      const plain = nhoLive.replace(/<[^>]+>/g, "");
      if (plain !== x.nho) { x.nho = plain; const t = $("#nhoText"); if (t) t.textContent = plain; }
      const cards = await anki.call("cardsInfo", { cards: note.cards });
      const due = await anki.call("areDue", { cards: note.cards });
      if (!body.isConnected) return;
      body.className = "";
      body.innerHTML = `<div class="anki-cards">${cards.map((c, i) => {
        const [st, kind] = cardState(c);
        const isDue = due[i] && (kind === "rev" || kind === "learn");
        return `<div class="ac"><span>${esc(KLL_TEMPLATES[c.ord] || "Thẻ " + (c.ord + 1))} · ${st}${isDue ? ' <span class="st learn">đến hạn</span>' : ""}<small class="muted"> · ${c.reps} lần ôn, ${c.lapses} lần quên</small></span>
          <span class="row-actions">${kind === "sus" ? `<button class="btn small" data-unsus="${c.cardId}" type="button">Bỏ tạm ngưng</button>` : ""}</span></div>`;
      }).join("")}</div>
      <div class="row-actions"><button class="btn small primary" id="studyLesson" data-deck="${esc(cards[0].deckName)}" type="button">Học bài “${esc(cards[0].deckName.split("::").pop())}” trong Anki</button>
      <span class="muted">Anki đưa thẻ theo đúng thứ tự và lịch ôn của bài này.</span></div>
      <div class="nho-edit"><label for="nhoEdit" class="muted">Cách nhớ của bạn (lưu thẳng vào ghi chú Anki)</label><textarea id="nhoEdit">${esc(plain)}</textarea>
      <div class="row-actions"><button class="btn small primary" id="nhoSave" type="button">Lưu vào Anki</button><button class="btn small" id="openAnki" type="button">Mở trong trình duyệt thẻ của Anki</button><span id="nhoMsg" class="saved"></span></div></div>`;
      body.querySelectorAll("[data-unsus]").forEach(b => b.addEventListener("click", async () => { await anki.call("unsuspend", { cards: [+b.dataset.unsus] }); loadAnkiPanel(x); }));
      $("#studyLesson").addEventListener("click", e => startSession({ title: `KLL ${e.target.dataset.deck.split("::").pop()}`, deck: e.target.dataset.deck, back: "lookup/" + x.k }));
      $("#openAnki").addEventListener("click", () => anki.call("guiBrowse", { query: `nid:${x.nid}` }));
      $("#nhoSave").addEventListener("click", async () => {
        const v = $("#nhoEdit").value.trim();
        try {
          await anki.call("updateNoteFields", { note: { id: x.nid, fields: { "Cách nhớ": esc(v) } } });
          x.nho = v; const t = $("#nhoText"); if (t) t.textContent = v;
          $("#nhoMsg").textContent = "Đã lưu vào Anki.";
        } catch (e) { $("#nhoMsg").textContent = "Không lưu được: " + e.message; }
      });
    } catch (e) { body.textContent = "Lỗi khi đọc dữ liệu Anki: " + e.message; }
  }

  /* ---------- Học với Anki ---------- */
  const studyEl = $("#study");
  let session = null;
  async function renderDecks() {
    session = null;
    if (!(await anki.ping())) {
      studyEl.innerHTML = `<div class="notice"><b>Chưa kết nối được Anki.</b> Hãy mở Anki trên máy này (đã cài add-on AnkiConnect), rồi bấm <button class="btn small" id="retry" type="button">Thử lại</button>. Mọi lần chấm thẻ ở đây đều ghi thẳng vào bộ sưu tập Anki, nên lịch ôn hai bên luôn giống nhau.</div>`;
      $("#retry").addEventListener("click", renderDecks);
      return;
    }
    studyEl.innerHTML = `<div class="notice">Đang tải danh sách deck…</div>`;
    const names = (await anki.call("deckNames")).filter(n => n !== "Mặc định" && n !== "Default");
    const stats = await anki.call("getDeckStats", { decks: names });
    const byName = {}; Object.values(stats).forEach(s => { byName[s.name] = s; });
    const reviewed = await anki.call("getNumCardsReviewedToday");
    const open = store.get("tk-open-decks", {});
    const rows = names.filter(n => { const p = n.split("::"); for (let i = 1; i < p.length; i++) if (!open[p.slice(0, i).join("::")]) return false; return true; });
    const num = (v, cls) => `<span class="n ${v ? cls : "zero"}">${v}</span>`;
    studyEl.innerHTML = `<div class="study-head"><div><h1>Học với Anki</h1><span class="muted">Hôm nay đã ôn ${reviewed} thẻ. Lịch ôn và FSRS do chính Anki tính.</span></div>
      <div class="row-actions"><button class="btn" id="syncBtn" type="button">Đồng bộ AnkiWeb</button><button class="btn" id="reload" type="button">Tải lại</button></div></div>
      <div class="decks"><div class="deck head"><span>Deck</span><span class="n">Mới</span><span class="n">Học</span><span class="n">Đến hạn</span></div>
      ${rows.map(n => {
        const p = n.split("::"), s = byName[n] || { new_count: 0, learn_count: 0, review_count: 0 };
        const hasKids = names.some(m => m.startsWith(n + "::"));
        return `<div class="deck"><span class="name" style="padding-left:${(p.length - 1) * 18}px">${hasKids ? `<button class="tog" data-tog="${esc(n)}" type="button" aria-label="Mở rộng">${open[n] ? "−" : "+"}</button>` : '<span style="width:20px"></span>'}<a data-deck="${esc(n)}" title="${esc(n)}">${esc(p[p.length - 1])}</a></span>${num(s.new_count, "new")}${num(s.learn_count, "lrn")}${num(s.review_count, "rev")}</div>`;
      }).join("")}</div>`;
    studyEl.querySelectorAll("[data-tog]").forEach(b => b.addEventListener("click", () => { open[b.dataset.tog] = !open[b.dataset.tog]; store.set("tk-open-decks", open); renderDecks(); }));
    studyEl.querySelectorAll("[data-deck]").forEach(a => a.addEventListener("click", () => startSession({ title: a.dataset.deck, deck: a.dataset.deck })));
    $("#reload").addEventListener("click", renderDecks);
    $("#syncBtn").addEventListener("click", async e => {
      e.target.disabled = true; e.target.textContent = "Đang đồng bộ…";
      try { await anki.call("sync"); e.target.textContent = "Đã đồng bộ"; } catch (err) { e.target.textContent = "Lỗi: " + err.message; }
      setTimeout(renderDecks, 1200);
    });
  }

  async function deckCounts(deck) {
    const st = await anki.call("getDeckStats", { decks: [deck] });
    return Object.values(st)[0] || { new_count: 0, learn_count: 0, review_count: 0 };
  }
  // Học bằng chính trình ôn tập của Anki: app mở deck trong Anki, hiển thị thẻ Anki đang đưa ra
  // và chấm qua nút của Anki. Thứ tự thẻ, giới hạn ngày, bước học, FSRS đều do Anki quyết định.
  async function startSession(opts) {
    go("study", true);
    if (!(await anki.ping())) { renderDecks(); return; }
    session = { title: opts.title, deck: opts.deck, back: opts.back || null, done: 0 };
    studyEl.innerHTML = `<div class="notice">Đang mở deck trong Anki…</div>`;
    try {
      if (!(await anki.call("guiDeckReview", { name: opts.deck }))) throw new Error("Anki không mở được deck này.");
    } catch (e) {
      studyEl.innerHTML = `<div class="notice">Không mở được deck trong Anki: ${esc(e.message)}</div>`;
      return;
    }
    await new Promise(r => setTimeout(r, 250));
    nextCard();
  }
  async function endSession() {
    session = null;
    try { await anki.call("guiDeckBrowser"); } catch (e) {}
    renderDecks();
  }
  // Anki thay [sound:…] bằng [anki:play:q|a:N]; tìm lại file theo thứ tự trường trong mẫu thẻ.
  const tplCache = {};
  async function templatesOf(model) {
    if (!tplCache[model]) tplCache[model] = await anki.call("modelTemplates", { modelName: model });
    return tplCache[model];
  }
  async function avLists(c, ord) {
    const t = Object.values(await templatesOf(c.modelName))[ord] || { Front: "", Back: "" };
    const sounds = tpl => {
      const out = [];
      for (const m of tpl.matchAll(/\{\{([^}]+)\}\}/g)) {
        const raw = m[1].trim();
        if (/^[#^/!]/.test(raw) || raw === "FrontSide") continue;
        const f = c.fields[raw.split(":").pop().trim()];
        if (f) for (const s of f.value.matchAll(/\[sound:([^\]]+)\]/g)) out.push(s[1]);
      }
      return out;
    };
    return { q: sounds(t.Front), a: sounds(t.Back) };
  }
  function playBtn(f) {
    return f ? `<button class="tk-play" title="Nghe" onclick="new Audio('/media/'+encodeURIComponent(${JSON.stringify(f).replace(/"/g, "&quot;")})).play()">▶</button>` : "";
  }
  function cardDoc(html, css, ord, av) {
    const body = html
      .replace(/\[anki:play:(q|a):(\d+)\]/g, (_, side, n) => playBtn(((av || {})[side] || [])[+n]))
      .replace(/\[sound:([^\]]+)\]/g, (_, f) => playBtn(f));
    return `<!doctype html><html><head><meta charset="utf-8"><base href="${location.origin}/media/"><style>${css}
      html,body{margin:0} body{padding:18px} .tk-play{width:32px;height:32px;border-radius:50%;border:1px solid #ccc;background:#f4f4f4;cursor:pointer}</style></head>
      <body class="card card${ord + 1}${theme.dark() ? " nightMode night_mode" : ""}">${body}</body></html>`;
  }
  function fitFrame(f) {
    try { f.style.height = Math.max(340, f.contentDocument.documentElement.scrollHeight + 4) + "px"; } catch (e) {}
  }
  const EASE = { 1: ["again", "Lại"], 2: ["hard", "Khó"], 3: ["good", "Tốt"], 4: ["easy", "Dễ"] };

  /* ---------- Học ngược: nhìn mặt sau, nhớ mặt trước ----------
     - Thẻ kanji (ghi chú có trường Kanji / 漢字 / character là đúng một chữ Hán): hiện Hán Việt + nghĩa,
       người học viết chữ lên bảng, bấm kiểm tra thì máy đọc chữ vừa viết rồi hiện đáp án.
     - Thẻ khác: hiện phần mặt sau của thẻ (sau <hr id=answer>), che các chữ thuộc mặt trước; nhớ ra rồi lật xem.
     Vẫn chấm trên chính thẻ Anki đang ôn, nên lịch ôn của thẻ đó tính theo cách học này. */
  let hocNguoc = store.get("tk-hoc-nguoc", false);
  const plain = html => new DOMParser().parseFromString(String(html || ""), "text/html").body.textContent.trim();
  const fieldOf = (c, ...names) => { for (const n of names) { const f = c.fields && c.fields[n]; if (f && plain(f.value)) return f.value; } return ""; };
  function kanjiOf(c) {
    const v = plain(fieldOf(c, "Kanji", "漢字", "character"));
    return [...v].length === 1 && isKanji(v) && v !== "々" ? v : null;
  }
  // Mặt sau không có mặt trước: lấy phần sau <hr id=answer>, che chữ của các trường ở mặt trước, bỏ âm thanh.
  async function backOnly(c, ord) {
    const parts = String(c.answer || "").split(/<hr[^>]*id=["']?answer["']?[^>]*>/i);
    if (parts.length < 2) return "";
    const tpl = Object.values(await templatesOf(c.modelName))[ord] || { Front: "" };
    const hide = new Set();
    for (const m of tpl.Front.matchAll(/\{\{([^}]+)\}\}/g)) {
      const name = m[1].trim().replace(/^[#^/]/, "").split(":").pop().trim();
      const v = plain(fieldOf(c, name)).replace(/［[^］]*］/g, "").trim();
      if (!v || v.length > 30) continue;
      v.split(/[、,／/]\s*/).forEach(x => {
        x = x.trim();
        if (!x) return;
        hide.add(x);
        if (x.endsWith("ます") && x.length > 3) hide.add(x.slice(0, -2));   // che cả dạng chia: 逃げます → 逃げろ
      });
    }
    const doc = new DOMParser().parseFromString(parts.slice(1).join(""), "text/html");
    doc.querySelectorAll("audio, script").forEach(n => n.remove());
    const words = [...hide].sort((x, y) => y.length - x.length).map(x => x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    if (words.length) {
      const re = new RegExp(words.join("|"), "g");
      const walk = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
      const nodes = [];
      while (walk.nextNode()) nodes.push(walk.currentNode);
      nodes.forEach(n => {
        if (!n.nodeValue.match(re)) return;
        const span = doc.createElement("span");
        span.innerHTML = esc(n.nodeValue).replace(re, '<span class="tk-blank">＿＿</span>');
        n.replaceWith(span);
      });
    }
    return doc.body.innerHTML.replace(/\[sound:[^\]]+\]|\[anki:play:[qa]:\d+\]/g, "").trim();
  }
  let wboard = null;
  /* So hình chữ người viết với nét mẫu KanjiVG, không phụ thuộc thứ tự hay số nét.
     Căn chữ: mẫu chuẩn hoá theo trọng tâm và bán kính trung bình; chữ người viết co giãn về độ trải của mẫu,
     dịch cho khớp, rồi căn affine có giới hạn (xoay tối đa 15°, co giãn lệch tối đa 25% giữa hai hướng) để
     chữ viết nghiêng / tỉ lệ khác vẫn khớp. Sau đó, trong bán kính 0,25, chữ là "chưa đúng" khi:
     - hơn 15% nét mẫu không có mực nào ở gần (thiếu bộ phận: 夋 thay cho 後, phần trong 南 viết sai);
     - một nét dài viết ngắn hẳn: đầu nét mẫu cách mực quá 0,65;
     - một đoạn nét nhô qua nét khác (dài từ 0,6) mà người viết không nhô (sổ dọc 生 dừng ở nét ngang đầu);
     - hơn 15% nét mẫu không có mực cùng hướng (lệch dưới 40°) trong bán kính 0,2 (飲 viết nguệch ngoạc: chữ
       nhiều nét thì nét mẫu nằm sát nhau, chỉ xét khoảng cách thì nét nào cũng "chạm").
     Ngưỡng chọn bằng cách thử chữ in Yu Gothic / MS Gothic và nét KanjiVG làm méo như chữ viết tay (xoay,
     nghiêng, lệch từng nét, có hoặc không viết liền): méo vừa không báo nhầm chữ nào trong 200 chữ; 去 viết
     đúng mà nghiêng được tính đúng; năm chữ viết sai thật (後, 南 hai lần, 生, 飲) đều bị bắt. */
  function refPoints(paths) {
    const NS = "http://www.w3.org/2000/svg", svg = document.createElementNS(NS, "svg");
    svg.style.cssText = "position:absolute;width:0;height:0";
    document.body.appendChild(svg);
    const out = paths.map(d => {
      const p = document.createElementNS(NS, "path");
      p.setAttribute("d", d); svg.appendChild(p);
      const L = p.getTotalLength(), n = Math.max(2, Math.ceil(L)), pts = [];
      for (let i = 0; i <= n; i++) { const q = p.getPointAtLength(L * i / n); pts.push([q.x, q.y]); }
      return pts;
    });
    svg.remove();
    return out;
  }
  function spread(P) {
    const c = [0, 1].map(a => P.reduce((t, p) => t + p[a], 0) / P.length);
    const s = [0, 1].map(a => Math.sqrt(P.reduce((t, p) => t + (p[a] - c[a]) ** 2, 0) / P.length));
    return { c, s };
  }
  function nearest(P, x, y) {
    let best = Infinity, bi = 0;
    for (let i = 0; i < P.length; i++) { const d = (P[i][0] - x) ** 2 + (P[i][1] - y) ** 2; if (d < best) { best = d; bi = i; } }
    return [Math.sqrt(best), bi];
  }
  // Giới hạn ma trận affine 2×2: tách thành xoay × co giãn đối xứng, kẹp góc xoay và tỉ lệ hai hướng co giãn.
  function clampAffine([[a, b], [c, d]], smax, rot) {
    if (a * d - b * c <= 0) return [[1, 0], [0, 1]];
    let th = Math.atan2(c - b, a + d);
    const co = Math.cos(th), si = Math.sin(th);
    const p = co * a + si * c, q = co * b + si * d, r = co * d - si * b;   // P = Rᵀ·A = [[p, q], [q, r]]
    const m = (p + r) / 2, h = Math.hypot((p - r) / 2, q);
    let l1 = m + h, l2 = m - h;
    const gm = Math.sqrt(Math.max(l1 * l2, 1e-9));
    l1 = Math.min(gm * smax, Math.max(gm / smax, l1)); l2 = Math.min(gm * smax, Math.max(gm / smax, l2));
    const ang = 0.5 * Math.atan2(2 * q, p - r), ec = Math.cos(ang), es = Math.sin(ang);
    const P = [[l1 * ec * ec + l2 * es * es, (l1 - l2) * ec * es], [(l1 - l2) * ec * es, l1 * es * es + l2 * ec * ec]];
    th = Math.max(-rot, Math.min(rot, th));
    const C = Math.cos(th), S = Math.sin(th);
    return [[C * P[0][0] - S * P[1][0], C * P[0][1] - S * P[1][1]], [S * P[0][0] + C * P[1][0], S * P[0][1] + C * P[1][1]]];
  }
  // Bình phương tối thiểu dst ≈ A·src + t (affine 2D) qua phương trình chuẩn 3×3.
  function fitAffine(src, dst) {
    const M = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], bx = [0, 0, 0], by = [0, 0, 0];
    src.forEach(([x, y], i) => {
      const v = [x, y, 1];
      for (let r = 0; r < 3; r++) { for (let c = 0; c < 3; c++) M[r][c] += v[r] * v[c]; bx[r] += v[r] * dst[i][0]; by[r] += v[r] * dst[i][1]; }
    });
    const det3 = m => m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
    const D = det3(M);
    if (Math.abs(D) < 1e-12) return null;
    const solve = b => [0, 1, 2].map(k => det3(M.map((row, r) => row.map((v, c) => (c === k ? b[r] : v)))) / D);
    const X = solve(bx), Y = solve(by);
    return [[X[0], X[1]], [Y[0], Y[1]]];
  }
  // Xoay + co giãn đều (Procrustes), dùng khi affine suy biến (chữ một nét thẳng như 一: điểm gần như thẳng hàng).
  function fitSimilarity(src, dst) {
    const n = src.length, cs = [0, 1].map(a => src.reduce((t, p) => t + p[a], 0) / n), cd = [0, 1].map(a => dst.reduce((t, p) => t + p[a], 0) / n);
    let p = 0, q = 0, ss = 0;
    src.forEach(([x, y], i) => { const sx = x - cs[0], sy = y - cs[1], dx = dst[i][0] - cd[0], dy = dst[i][1] - cd[1]; p += sx * dx + sy * dy; q += sx * dy - sy * dx; ss += sx * sx + sy * sy; });
    const k = Math.hypot(p, q) / (ss || 1), th = Math.atan2(q, p);
    return [[k * Math.cos(th), -k * Math.sin(th)], [k * Math.sin(th), k * Math.cos(th)]];
  }
  function shapeCheck(k, strokes) {
    const paths = STROKES[k];
    if (!paths || !paths.length) return null;
    const R = 0.25, refs = refPoints(paths), all = refs.flat();
    const r0 = spread(all), g = Math.hypot(r0.s[0], r0.s[1]) || 1;
    const refN = refs.map(st => st.map(([x, y]) => [(x - r0.c[0]) / g, (y - r0.c[1]) / g]));
    const flatN = refN.flat(), rs = spread(flatN).s;
    // Mực người viết: chấm dày mỗi 2 đơn vị cho đều, rồi đưa về cùng tỉ lệ với mẫu.
    const ink = [], sid = [];
    strokes.forEach((st, k) => {
      ink.push([st[0].x, st[0].y]); sid.push(k);
      for (let i = 1; i < st.length; i++) {
        const a = st[i - 1], b = st[i], n = Math.ceil(Math.hypot(b.x - a.x, b.y - a.y) / 2);
        for (let j = 1; j <= n; j++) { ink.push([a.x + (b.x - a.x) * j / n, a.y + (b.y - a.y) * j / n]); sid.push(k); }
      }
    });
    const u0 = spread(ink), f0 = 1 / (Math.hypot(u0.s[0], u0.s[1]) || 1);
    const f = [0, 1].map(a => f0 * (u0.s[a] > 1e-6 ? Math.min(1.15, Math.max(1 / 1.15, rs[a] / u0.s[a] / f0)) : 1.15));
    let shift = [0, 0];
    const toN = ([x, y]) => [(x - u0.c[0]) * f[0] + shift[0], (y - u0.c[1]) * f[1] + shift[1]];
    let base = ink.map(toN);
    for (let it = 0; it < 3; it++) {
      let dx = 0, dy = 0, m = 0;
      base.forEach(([x, y]) => { const [d, i] = nearest(flatN, x, y); if (d < 2 * R) { dx += flatN[i][0] - x; dy += flatN[i][1] - y; m++; } });
      if (m <= 5) break;
      shift = [shift[0] + dx / m * 0.8, shift[1] + dy / m * 0.8];
      base = ink.map(toN);
    }
    // Căn affine: ghép mực ↔ mẫu theo điểm gần nhất (cả hai chiều), giải affine, kẹp giới hạn, lặp 12 lần.
    let A = [[1, 0], [0, 1]], t = [0, 0];
    const ap = ([x, y]) => [A[0][0] * x + A[0][1] * y + t[0], A[1][0] * x + A[1][1] * y + t[1]];
    let u = base;
    for (let it = 0; it < 12; it++) {
      const src = [], dst = [];
      u.forEach(([x, y], j) => { const [d, i] = nearest(flatN, x, y); if (d < 3 * R) { src.push(base[j]); dst.push(flatN[i]); } });
      flatN.forEach(([x, y]) => { const [d, j] = nearest(u, x, y); if (d < 3 * R) { src.push(base[j]); dst.push([x, y]); } });
      if (src.length < 10) break;
      let fit = fitAffine(src, dst);
      if (!fit || Math.abs(fit[0][0] * fit[1][1] - fit[0][1] * fit[1][0]) < 0.2 * fit.flat().reduce((t, v) => t + v * v, 0) / 2) fit = fitSimilarity(src, dst);
      A = clampAffine(fit, 1.25, Math.PI / 12);
      t = [0, 1].map(a => dst.reduce((s, p, i) => s + p[a] - (A[a][0] * src[i][0] + A[a][1] * src[i][1]), 0) / src.length);
      u = base.map(ap);
    }
    // Ngược lại: toạ độ chuẩn hoá → toạ độ bảng (để vẽ nét mẫu chồng lên chữ người viết).
    const det = A[0][0] * A[1][1] - A[0][1] * A[1][0];
    const toPad = ([x, y]) => {
      const qx = x - t[0], qy = y - t[1];
      const bx = (A[1][1] * qx - A[0][1] * qy) / det, by = (-A[1][0] * qx + A[0][0] * qy) / det;
      return [(bx - shift[0]) / f[0] + u0.c[0], (by - shift[1]) / f[1] + u0.c[1]];
    };
    // Hướng nét (0–180°). Mực: theo chiều kéo bút (±3 điểm cùng nét), điểm lẻ thì theo các điểm mực lân cận.
    const angDiff = (a, b) => { const d = Math.abs(a - b) % Math.PI; return Math.min(d, Math.PI - d); };
    const pcaDir = (P, x, y, r) => {
      let sxx = 0, syy = 0, sxy = 0;
      P.forEach(([px, py]) => { const dx = px - x, dy = py - y; if (dx * dx + dy * dy < r * r) { sxx += dx * dx; syy += dy * dy; sxy += dx * dy; } });
      return 0.5 * Math.atan2(2 * sxy, sxx - syy);
    };
    const ud = u.map(([x, y], i) => {
      let a = i, b = i;
      while (a > i - 3 && a > 0 && sid[a - 1] === sid[i]) a--;
      while (b < i + 3 && b < u.length - 1 && sid[b + 1] === sid[i]) b++;
      return b > a ? Math.atan2(u[b][1] - u[a][1], u[b][0] - u[a][0]) : pcaDir(u, x, y, 0.06);
    });
    // Phủ có hướng: điểm mẫu chỉ tính là có mực khi trong bán kính 0,2 có mực đi cùng hướng (lệch dưới 40°).
    // Chữ nhiều nét (飲) các nét mẫu nằm sát nhau, nét viết nguệch ngoạc vẫn "chạm" gần hết; xét hướng thì không.
    const R2 = 0.2, ANG = Math.PI * 40 / 180;
    let miss = 0, missDir = 0, sai = false;
    const guide = refN.map((st, si) => {
      const d = st.map(([x, y]) => nearest(u, x, y)[0]);
      miss += d.filter(v => v >= R).length;
      const lacHuong = st.map(([x, y], i) => {
        const p = st[Math.max(0, i - 2)], q = st[Math.min(st.length - 1, i + 2)], rd = Math.atan2(q[1] - p[1], q[0] - p[0]);
        return !u.some(([ux, uy], j) => (ux - x) ** 2 + (uy - y) ** 2 < R2 * R2 && angDiff(ud[j], rd) < ANG);
      });
      missDir += lacHuong.filter(Boolean).length;
      // Nét dài viết ngắn hẳn. Chấm ngắn như ở 心 không xét: mỗi người đặt một kiểu.
      if (st.length / g >= 0.6 && Math.max(d[0], d[d.length - 1]) > 0.65) sai = true;
      // Đoạn đầu nét nhô qua nét khác: tìm chỗ chạm nét khác gần đầu nét nhất; đoạn từ đó ra đầu nét dài từ 0,6
      // thì người viết cũng phải có mực ở đó (bỏ khúc sát chỗ giao, nơi mực của nét kia nằm).
      const others = refN.filter((_, j) => j !== si).flat();
      if (others.length) {
        const dk = st.map(([x, y]) => nearest(others, x, y)[0]);
        [[...st.keys()], [...st.keys()].reverse()].forEach(idx => {
          const j = idx.findIndex(i => dk[i] < 0.06);
          if (j <= 0) return;
          let arc = 0, test = 0, phu = 0;
          for (let p = j - 1; p >= 0; p--) {
            const a = st[idx[p]], b = st[idx[p + 1]];
            arc += Math.hypot(a[0] - b[0], a[1] - b[1]);
            if (arc >= R) { test++; if (d[idx[p]] < R) phu++; }
          }
          if (arc >= 0.6 && test >= 2 && !phu) sai = true;
        });
      }
      return { miss: lacHuong, pts: st.map(toPad) };
    });
    return { lech: missDir / flatN.length > 0.15 || miss / flatN.length > 0.15 || sai, guide };
  }
  // Máy đọc chữ người học vừa viết rồi so với chữ đúng.
  async function inkVerdict(k) {
    if (!wboard || !wboard.strokes.length) return `<div class="wr-res none">Bạn chưa viết gì. Chữ đúng là <b class="jp-big">${esc(k)}</b>.</div>`;
    let cands = null;
    try { cands = await readInk(wboard.strokes); } catch (e) { cands = null; }
    if (!cands) return `<div class="wr-res none">Không nhận diện được (mất mạng). Tự so chữ bạn viết với chữ đúng: <b class="jp-big">${esc(k)}</b>.</div>`;
    // Google đoán theo chữ thông dụng gần nhất: viết thiếu một bộ phận (夋 thay vì 後) vẫn ra chữ đủ.
    // Nên so thêm hình chữ với nét mẫu. Không so số nét: viết liền nét (口 một nét) vẫn là đúng.
    const i = cands.indexOf(k);
    const hinh = shapeCheck(k, wboard.strokes);
    const dung = i === 0 && !(hinh && hinh.lech);
    if (dung) return `<div class="wr-res ok"><b class="wr-head">✓ Đúng rồi!</b></div>`;
    // Chưa đúng: một câu gợi ý ngắn, kèm nét mẫu đặt chồng lên bảng (nét đỏ là chỗ cần sửa).
    if (hinh) wboard.showGuide(hinh.guide);
    const xemDo = hinh ? " Nét đỏ trên bảng là chỗ cần sửa." : "";
    let tip;
    if (i === 0) tip = `Vài nét chưa đúng chỗ.${xemDo || " So lại với đáp án nhé."}`;
    else if (i > 0 && i < 5) tip = `Gần đúng rồi, xem lại từng nét nhé.${xemDo}`;
    else tip = `Chữ bạn viết trông giống <b class="jp-big">${esc(cands[0] || "?")}</b> hơn.${xemDo}`;
    return `<div class="wr-res no"><b class="wr-head">Chưa đúng</b><span class="wr-tip">${tip}</span></div>`;
  }

  async function nextCard() {
    const s = session;
    if (!s) return;
    let c = null;
    try { c = await anki.call("guiCurrentCard"); } catch (e) { c = null; }
    const counts = await deckCounts(s.deck);
    if (!c) {
      studyEl.innerHTML = `<div class="notice"><b>Xong phần hôm nay của “${esc(s.title)}”.</b> Đã chấm ${s.done} thẻ trong phiên này.${counts.learn_count ? ` Còn ${counts.learn_count} thẻ đang học sẽ đến hạn lại sau vài phút.` : ""}
        <div class="row-actions" style="margin-top:10px">${s.back ? `<a class="btn" href="#${esc(s.back)}">← Quay lại thẻ kanji</a>` : ""}<button class="btn" id="toDecks" type="button">Danh sách deck</button>${counts.learn_count ? '<button class="btn primary" id="again" type="button">Kiểm tra lại</button>' : ""}</div></div>`;
      $("#toDecks").addEventListener("click", endSession);
      const ag = $("#again"); if (ag) ag.addEventListener("click", () => startSession({ title: s.title, deck: s.deck, back: s.back }));
      return;
    }
    const names = Object.keys(await templatesOf(c.modelName));
    const ord = Math.max(0, names.indexOf(c.template));
    if (c.css === undefined) { const [ci] = await anki.call("cardsInfo", { cards: [c.cardId] }); c.css = ci ? ci.css : ""; }
    s.cur = c; s.ord = ord; s.shown = false;
    try { s.av = await avLists(c, ord); } catch (e) { s.av = null; }
    s.kanji = hocNguoc ? kanjiOf(c) : null;
    const back = hocNguoc && !s.kanji ? await backOnly(c, ord) : "";
    s.mode = s.kanji ? "viet" : back ? "nguoc" : "thuong";
    const modeBtn = `<button class="btn small mode-btn" id="modeS" type="button" aria-pressed="${hocNguoc}" title="Học ngược: kanji thì nhìn Hán Việt + nghĩa rồi viết chữ; từ vựng thì nhìn mặt sau để nhớ mặt trước">Học ngược: ${hocNguoc ? "Bật" : "Tắt"}</button>`;
    const so = plain(fieldOf(c, "Số"));
    const writeUI = s.mode !== "viet" ? "" : `<div class="write-q">
        <div class="small muted">${so ? "#" + esc(so) + " · " : ""}Viết chữ Hán có nghĩa này</div>
        ${fieldOf(c, "Hán Việt") ? `<div class="wq-hv">${esc(plain(fieldOf(c, "Hán Việt")))}</div>` : ""}
        <div class="wq-mean">${esc(plain(fieldOf(c, "Nghĩa", "Translate", "meaning", "English")))}</div>
        ${fieldOf(c, "Cách nhớ") ? `<details class="wq-hint"><summary>Gợi ý cách nhớ</summary>${esc(plain(fieldOf(c, "Cách nhớ")))}</details>` : ""}
        <div class="board-actions"><button class="btn" id="wUndo" type="button">↶ Xoá nét cuối</button><button class="btn" id="wClear" type="button">Xoá hết</button></div>
        <div id="wResult"></div>
      </div>
      <div class="write-area"><div class="canvas-box"><canvas id="wpad" aria-label="Bảng viết chữ"></canvas><div class="guide" aria-hidden="true"></div></div></div>`;
    studyEl.innerHTML = `<div class="reviewer"><div class="rv-top"><div><b>${esc(s.title)}</b> <span class="muted">· ${esc(c.deckName || "")} · đã chấm ${s.done}</span></div>
      <span class="counts"><span class="new">${counts.new_count}</span><span class="lrn">${counts.learn_count}</span><span class="rev">${counts.review_count}</span></span>
      <span class="row-actions">${modeBtn}${s.back ? `<a class="btn small" href="#${esc(s.back)}">← Thẻ kanji</a>` : ""}<button class="btn small" id="endS" type="button">Dừng</button></span></div>
      ${s.mode === "viet"
        // Viết kanji: bảng viết bên trái, mặt sau thẻ hiện bên phải sau khi kiểm tra (màn hình hẹp thì xếp dọc).
        ? `<div class="write-wrap" id="writeWrap"><div class="write-left">${writeUI}</div><iframe class="cardframe" id="cf" title="Thẻ Anki" hidden></iframe></div>`
        : `<iframe class="cardframe" id="cf" title="Thẻ Anki"></iframe>`}
      <div id="ansArea"><button class="btn primary show-ans" id="showAns" type="button">${s.mode === "viet" ? "Kiểm tra chữ vừa viết <small>(Enter)</small>" : "Hiện đáp án <small>(Space)</small>"}</button></div></div>`;
    const f = $("#cf");
    f.addEventListener("load", () => fitFrame(f));
    if (s.mode === "viet") {
      wboard = makeBoard($("#wpad"));
      $("#wUndo").addEventListener("click", () => wboard.undo());
      $("#wClear").addEventListener("click", () => wboard.clear());
    } else {
      wboard = null;
      f.srcdoc = s.mode === "nguoc"
        ? cardDoc(`<div class="tk-nguoc">${back}</div>`, c.css + " .tk-blank{color:#999;letter-spacing:.1em}", ord, null)
        : cardDoc(c.question, c.css, ord, s.av);
    }
    $("#showAns").addEventListener("click", showAnswer);
    $("#endS").addEventListener("click", endSession);
    $("#modeS").addEventListener("click", () => {
      hocNguoc = !hocNguoc;
      store.set("tk-hoc-nguoc", hocNguoc);
      if (!s.shown) nextCard(); else { $("#modeS").textContent = "Học ngược: " + (hocNguoc ? "Bật" : "Tắt"); $("#modeS").setAttribute("aria-pressed", String(hocNguoc)); }
    });
  }
  async function showAnswer() {
    const s = session; if (!s || s.shown || s.busy) return;
    s.busy = true;
    if (s.mode === "viet") {
      $("#showAns").disabled = true;
      $("#showAns").textContent = "Đang đọc chữ…";
      $("#wResult").innerHTML = await inkVerdict(s.kanji);
    }
    try { await anki.call("guiShowAnswer"); } catch (e) {}
    s.busy = false;
    s.shown = true;
    const c = s.cur, f = $("#cf");
    f.hidden = false;
    const ww = $("#writeWrap");
    if (ww) { ww.classList.add("da-hien"); if (wboard) wboard.fit(); }  // bảng nhỏ lại: vẽ lại nét theo kích thước mới
    f.srcdoc = cardDoc(c.answer, c.css, s.ord, s.av);
    const eases = (c.buttons && c.buttons.length ? c.buttons : [1, 2, 3, 4]);
    $("#ansArea").innerHTML = `<div class="answers">${eases.map((e, i) => {
      const [cls, label] = EASE[e] || ["good", String(e)];
      const ivl = c.nextReviews && c.nextReviews[i] ? String(c.nextReviews[i]).replace(/[⁦-⁩]/g, "") : "";
      return `<button class="${cls}" data-ease="${e}" type="button">${label}<small>${esc(ivl)}${ivl ? " · " : ""}phím ${e}${e === 3 ? " · Space" : ""}</small></button>`;
    }).join("")}</div>`;
    $("#ansArea").querySelectorAll("[data-ease]").forEach(b => b.addEventListener("click", () => answer(+b.dataset.ease)));
  }
  async function answer(ease) {
    const s = session; if (!s || !s.shown || s.busy) return;
    s.busy = true;
    try {
      if (!(await anki.call("guiAnswerCard", { ease }))) throw new Error("Anki không nhận câu trả lời. Hãy kiểm tra cửa sổ Anki đang ở màn hình ôn tập.");
      s.done++;
      s.busy = false;
      await new Promise(r => setTimeout(r, 150));
      nextCard();
    } catch (e) {
      s.busy = false;
      const n = document.createElement("div");
      n.className = "notice"; n.textContent = "Không chấm được thẻ: " + e.message;
      studyEl.prepend(n);
    }
  }
  document.addEventListener("keydown", e => {
    if (!session || $("#view-study").hidden || /input|textarea/i.test(e.target.tagName)) return;
    // Đang viết kanji thì Space không lật thẻ (dễ bấm nhầm), dùng Enter; Ctrl+Z xoá nét cuối trên bảng viết.
    if (!session.shown && (e.key === "Enter" || (e.key === " " && session.mode !== "viet"))) { e.preventDefault(); showAnswer(); }
    else if (!session.shown && session.mode === "viet" && (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); if (wboard) wboard.undo(); }
    else if (session.shown && /^[1-4]$/.test(e.key)) answer(+e.key);
    else if (session.shown && e.key === " ") { e.preventDefault(); answer(3); }
  });

  /* ---------- Điều hướng ---------- */
  /* ---------- Quét chữ: bôi đen chữ Nhật ở bất kỳ đâu (cả trong trang Minna và thẻ Anki) ----------
     Chữ Hán: nghĩa + Hán Việt từ bộ thẻ của người học; chữ ngoài bộ thẻ lấy KANJIDIC2/Unihan (tham khảo).
     Katakana: đổi sang hiragana. Nếu đoạn bôi đen bắt đầu bằng một từ có trong Minna / KLL thì hiện nghĩa từ. */
  const TD = window.TUDIEN || {};
  const wordMap = new Map();
  const addWord = (w, r, m) => { w = String(w || "").replace(/［[^］]*］|～/g, "").trim(); if (w && !wordMap.has(w)) wordMap.set(w, [r, m]); };
  D.minna.forEach(m => { String(m[0]).split(/[、,／]/).forEach(w => addWord(w, m[1], m[2])); addWord(m[1], m[1], m[2]); });
  D.words.forEach(w => addWord(w[0], w[1], w[2]));
  D.kll.forEach(x => x.ex.forEach(e => addWord(e[0], e[1], e[2])));
  const toHira = s => s.replace(/[ァ-ヶ]/g, c => String.fromCharCode(c.charCodeAt(0) - 0x60));
  const hasJa = s => /[぀-ヿ㐀-鿿々]/.test(s);
  let scanOn = store.get("tk-quet", true);
  const pop = document.createElement("div");
  pop.className = "scan-pop";
  pop.hidden = true;
  pop.setAttribute("role", "dialog");
  pop.setAttribute("aria-label", "Nghĩa của chữ đã chọn");
  document.body.appendChild(pop);
  function drawToggle() {
    const b = $("#scanToggle");
    b.textContent = "Quét chữ: " + (scanOn ? "Bật" : "Tắt");
    b.setAttribute("aria-pressed", String(scanOn));
  }
  $("#scanToggle").addEventListener("click", () => { scanOn = !scanOn; store.set("tk-quet", scanOn); drawToggle(); if (!scanOn) hidePop(); });
  drawToggle();
  function wordOf(t) {
    // Đúng cả đoạn, không thì bỏ dần đuôi (okurigana, trợ từ) để tìm từ dài nhất ở đầu.
    for (let n = t.length; n >= 2; n--) { const w = wordMap.get(t.slice(0, n)); if (w) return [t.slice(0, n), w]; }
    return null;
  }
  // Đoạn bôi đen dài (từ 5 ký tự) mà không phải đúng một từ đã biết thì dịch cả câu.
  const isSentence = t => t.length >= 5 && !wordMap.has(t);
  function scanHtml(t) {
    let h = isSentence(t) ? `<div class="sp-tr"><span class="lbl">Dịch cả câu</span><p id="spTr">Đang dịch…</p><small class="ref">Dịch máy (Google Translate), nên đối chiếu với nghĩa từng phần bên dưới.</small></div>` : "";
    const w = wordOf(t);
    if (w) h += `<div class="sp-word"><b>${esc(w[0])}</b><span>${esc(w[1][0])}</span><p>${esc(w[1][1])}</p></div>`;
    if (/[ァ-ヺ]/.test(t)) h += `<div class="sp-kana"><span>${esc(t)}</span><span class="arr">→</span><b>${esc(toHira(t))}</b></div>`;
    [...new Set([...t].filter(isKanji))].slice(0, 8).forEach(c => {
      const x = kllByChar.get(c), d = TD[c];
      if (x) h += `<div class="sp-k"><button type="button" class="ch" data-k="${esc(c)}" title="Mở thẻ chữ ${esc(c)}">${esc(c)}</button><div><b class="hv">${esc(x.hv)}</b> ${esc(x.nghia)}<small>${esc(x.on)}${x.kun ? " · " + esc(x.kun) : ""}</small></div></div>`;
      else if (d) h += `<div class="sp-k"><button type="button" class="ch" data-k="${esc(c)}" title="Mở thẻ chữ ${esc(c)}">${esc(c)}</button><div>${d[0] ? `<b class="hv">${esc(d[0])}</b> <small class="ref">Hán Việt tham khảo</small> ` : ""}<span class="en">${esc(d[1])}</span><small>${esc(d[2])}${d[3] ? " · " + esc(d[3]) : ""}</small></div></div>`;
      else h += `<div class="sp-k"><span class="ch">${esc(c)}</span><div class="muted">Chưa có trong từ điển của app.</div></div>`;
    });
    return h ? h + `<div class="sp-act"><button type="button" class="btn small" data-note>＋ Ghi chú hôm nay</button></div>` : "";
  }
  let popText = "", popTr = "";
  const trCache = new Map();
  function hidePop() { pop.hidden = true; }
  // Dịch cả câu qua server (/api/dich gọi Google Translate); khung đã đổi sang câu khác thì bỏ kết quả cũ.
  async function translate(t) {
    let vi = trCache.get(t);
    if (vi === undefined) {
      try {
        const r = await fetch("/api/dich?q=" + encodeURIComponent(t));
        vi = r.ok ? (await r.json()).vi : null;
      } catch (e) { vi = null; }
      if (vi) trCache.set(t, vi);
    }
    const el = pop.querySelector("#spTr");
    if (!el || popText !== t) return;
    if (vi) { popTr = vi; el.textContent = vi; }
    else { el.textContent = "Chưa dịch được (cần mạng, và chạy app bằng start.bat bản mới)."; el.classList.add("muted"); }
  }
  function scanFrom(doc, frame) {
    if (!scanOn) return;
    const a = doc.activeElement;
    if (a && /INPUT|TEXTAREA/.test(a.tagName)) return;
    const sel = doc.getSelection(), t = (sel ? sel.toString() : "").replace(/\s+/g, "").slice(0, 300);
    if (!t || !hasJa(t) || !sel.rangeCount) return;
    const html = scanHtml(t);
    if (!html) return;
    const r = sel.getRangeAt(0).getBoundingClientRect(), off = frame ? frame.getBoundingClientRect() : { left: 0, top: 0 };
    popText = t;
    popTr = "";
    pop.innerHTML = html;
    pop.hidden = false;
    if (isSentence(t)) translate(t);
    const w = pop.offsetWidth, hgt = pop.offsetHeight;
    const left = Math.min(Math.max(8, r.left + off.left), innerWidth - w - 8);
    let top = r.bottom + off.top + 8;
    if (top + hgt > innerHeight - 8) top = Math.max(8, r.top + off.top - hgt - 8);
    pop.style.left = left + "px";
    pop.style.top = top + "px";
  }
  function bindScan(doc, frame) {
    if (!doc || doc.__quet) return;
    doc.__quet = true;
    const later = () => setTimeout(() => scanFrom(doc, frame), 10);
    doc.addEventListener("mouseup", later);
    doc.addEventListener("touchend", later);
    doc.addEventListener("mousedown", e => { if (!pop.contains(e.target)) hidePop(); });
    doc.addEventListener("keydown", e => { if (e.key === "Escape") hidePop(); });
    doc.addEventListener("scroll", hidePop, { passive: true });
  }
  bindScan(document, null);
  // Khung Minna và khung thẻ Anki cùng nguồn với app nên gắn được bộ quét vào tài liệu bên trong.
  document.addEventListener("load", e => {
    const f = e.target;
    if (f && f.tagName === "IFRAME") { try { bindScan(f.contentDocument, f); } catch (err) {} }
  }, true);
  window.addEventListener("resize", hidePop);
  pop.addEventListener("click", async e => {
    const k = e.target.closest("[data-k]");
    if (k) { hidePop(); go("lookup/" + k.dataset.k); return; }
    const nb = e.target.closest("[data-note]");
    if (nb) {
      const w = wordOf(popText);
      const lines = [...new Set([...popText].filter(isKanji))].map(c => {
        const x = kllByChar.get(c), d = TD[c];
        return x ? `${c} ${x.hv} — ${x.nghia}` : d ? `${c} ${d[0]} — ${d[1]}` : c;
      });
      const kana = /[ァ-ヺ]/.test(popText) ? [`${popText} → ${toHira(popText)}`] : [];
      nb.disabled = true;
      const head = popTr ? [popText, "→ " + popTr] : [w ? `${w[0]}（${w[1][0]}）${w[1][1]}` : popText];
      try { await notes.append([...head, ...kana, ...lines].join("\n")); nb.textContent = "✓ Đã thêm vào ghi chú"; }
      catch (err) { nb.textContent = "Không lưu được"; nb.disabled = false; }
    }
  });

  /* ---------- Ghi chú theo ngày (lưu thành file notes/YYYY-MM-DD.md qua server) ---------- */
  const notes = (() => {
    const pad = n => String(n).padStart(2, "0");
    const today = () => { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };
    const WD = ["Chủ nhật", "Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy"];
    const title = day => { const [y, m, d] = day.split("-").map(Number); return `${WD[new Date(y, m - 1, d).getDay()]}, ${d}/${m}/${y}`; };
    let list = [], cur = today(), timer = null, dirty = false;
    const api = (day, opt) => fetch(day ? `/api/notes/${day}` : "/api/notes", opt).then(r => { if (!r.ok) throw new Error(r.status); return r; });
    const put = (day, body) => api(day, { method: "PUT", headers: { "Content-Type": "text/plain; charset=utf-8" }, body });
    function remember(day, text) {
      const i = list.findIndex(n => n.date === day);
      if (i >= 0) { if (text.trim()) list[i].text = text; else list.splice(i, 1); }
      else if (text.trim()) list.push({ date: day, text });
    }
    async function loadList() {
      try { list = await (await api()).json(); } catch (e) { list = []; }
      drawList();
    }
    function drawList() {
      const q = fold($("#noteSearch").value.trim());
      const days = list.filter(n => !q || fold(n.text).includes(q) || n.date.includes(q));
      if (!q && !days.some(n => n.date === cur)) days.push({ date: cur, text: $("#noteText").value });
      days.sort((a, b) => b.date.localeCompare(a.date));
      $("#noteList").innerHTML = days.map(n => `<button type="button" data-day="${n.date}" ${n.date === cur ? 'aria-current="true"' : ""}><b>${title(n.date)}</b><span>${esc((n.text.split("\n").find(l => l.trim()) || "(trống)").slice(0, 60))}</span></button>`).join("")
        || `<span class="muted">Không thấy ghi chú nào.</span>`;
    }
    async function open(day) {
      await save();
      cur = day;
      $("#noteDate").value = day;
      $("#noteTitle").textContent = title(day) + (day === today() ? " · hôm nay" : "");
      let text = "";
      try { text = await (await api(day)).text(); $("#noteState").textContent = text ? "Đã lưu" : ""; }
      catch (e) { $("#noteState").textContent = "Không kết nối được server"; }
      $("#noteText").value = text;
      drawList();
    }
    async function save() {
      clearTimeout(timer);
      if (!dirty) return;
      dirty = false;
      const text = $("#noteText").value;
      try {
        await put(cur, text);
        $("#noteState").textContent = "Đã lưu " + new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
        remember(cur, text);
        drawList();
      } catch (e) { dirty = true; $("#noteState").textContent = "Chưa lưu được — kiểm tra server"; }
    }
    $("#noteText").addEventListener("input", () => { dirty = true; $("#noteState").textContent = "Đang gõ…"; clearTimeout(timer); timer = setTimeout(save, 700); });
    $("#noteText").addEventListener("blur", save);
    $("#noteText").addEventListener("keydown", e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); } });
    $("#noteToday").addEventListener("click", () => go("notes/" + today()));
    $("#noteDate").addEventListener("change", e => { if (e.target.value) go("notes/" + e.target.value); });
    $("#noteSearch").addEventListener("input", drawList);
    $("#noteList").addEventListener("click", e => { const b = e.target.closest("[data-day]"); if (b) go("notes/" + b.dataset.day); });
    return {
      async show(day) { await loadList(); await open(/^\d{4}-\d{2}-\d{2}$/.test(day || "") ? day : today()); },
      // Thêm một đoạn vào cuối ghi chú hôm nay (dùng từ khung quét chữ).
      async append(text) {
        const day = today();
        if (cur === day && dirty) await save();
        const old = await (await api(day)).text();
        const t = new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
        const body = (old.trimEnd() ? old.trimEnd() + "\n\n" : "") + `[${t}] ${text}`;
        await put(day, body);
        remember(day, body);
        if (!$("#view-notes").hidden && cur === day) { $("#noteText").value = body; drawList(); }
      }
    };
  })();

  /* ---------- Giao diện Sáng / Tối ----------
     Mặc định "light"; "auto" theo hệ thống; "dark" luôn tối. Áp cả vào trang Minna (data-theme) và thẻ Anki
     đang học (lớp nightMode / night_mode mà mẫu thẻ Anki dùng cho chế độ tối). */
  const theme = (() => {
    const mq = matchMedia("(prefers-color-scheme: dark)");
    let mode = store.get("tk-theme", "light");
    const dark = () => mode === "dark" || (mode === "auto" && mq.matches);
    function into(doc) {
      if (!doc || !doc.documentElement) return;
      if (mode === "auto") delete doc.documentElement.dataset.theme; else doc.documentElement.dataset.theme = mode;
      if (doc.body && doc.body.classList.contains("card")) {
        doc.body.classList.toggle("nightMode", dark());
        doc.body.classList.toggle("night_mode", dark());
      }
    }
    function apply() {
      into(document);
      document.querySelectorAll("iframe").forEach(f => { try { into(f.contentDocument); } catch (e) {} });
      document.querySelectorAll("[data-theme-set]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.themeSet === mode)));
    }
    $("#themePick").addEventListener("click", e => {
      const b = e.target.closest("[data-theme-set]");
      if (b) { mode = b.dataset.themeSet; store.set("tk-theme", mode); apply(); }
    });
    mq.addEventListener("change", apply);
    document.addEventListener("load", e => { if (e.target.tagName === "IFRAME") { try { into(e.target.contentDocument); } catch (err) {} } }, true);
    apply();
    return { dark };
  })();

  let silent = false;
  function go(route, quiet) {
    if (decodeURIComponent(location.hash.replace(/^#/, "")) === route) { if (!quiet) window.dispatchEvent(new HashChangeEvent("hashchange")); return; }
    if (quiet) silent = true;
    location.hash = route;
  }
  function show(tab) {
    document.querySelectorAll(".tabs a").forEach(a => {
      if (a.dataset.tab === tab) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    $("#view-lookup").hidden = tab !== "lookup";
    $("#view-study").hidden = tab !== "study";
    $("#view-minna").hidden = !tab.startsWith("minna");
    $("#view-notes").hidden = tab !== "notes";
  }
  function route() {
    const h = decodeURIComponent(location.hash.replace(/^#/, "")) || "lookup";
    if (h.startsWith("minna-")) {
      const [book, ...rest] = h.split("/"), sub = rest.join("/");  // giữ cả đường dẫn con, vd so-sanh/te-imasu
      show(book);
      const src = `minna/${book.slice(6)}.html${sub ? "#" + sub : ""}`;
      const fr = $("#minnaFrame");
      if (fr.dataset.src !== src) { fr.dataset.src = src; fr.src = src; }
      return;
    }
    if (h === "notes" || h.startsWith("notes/")) { show("notes"); notes.show(h.slice(6)); return; }
    if (h === "study") { show("study"); if (silent) { silent = false; return; } renderDecks(); return; }
    show("lookup");
    const ch = h.startsWith("lookup/") ? h.slice(7) : "";
    if (ch) renderCard([...ch][0]); else renderEmpty();
  }
  window.addEventListener("hashchange", route);
  renderRecent();
  anki.ping();
  setInterval(() => anki.ping(), 10000);
  route();
})();
