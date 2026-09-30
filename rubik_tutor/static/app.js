"use strict";
/* Rubik's Cube Tutor front end (no build step, no dependencies). */

const LETTERS = "URFDLB";
const BASE = { U: 0, R: 9, F: 18, D: 27, L: 36, B: 45 };
const CENTERS = new Set([4, 13, 22, 31, 40, 49]);
// net layout: [face, column offset, row offset] on a 12 x 9 grid
const LAYOUT = [["U", 3, 0], ["L", 0, 3], ["F", 3, 3], ["R", 6, 3], ["B", 9, 3], ["D", 3, 6]];
const DEFAULT_PALETTE = { U: "#f5d90a", D: "#f4f4f4", F: "#1faa59", B: "#1f5fd6", R: "#ff8a1f", L: "#d62839" };
const ALL_MOVES = [];
for (const f of LETTERS) ALL_MOVES.push(f, f + "'", f + "2");

const $ = (id) => document.getElementById(id);
const app = {
  facelets: null,          // 54-char string
  palette: { ...DEFAULT_PALETTE },
  low: new Set(),          // indices the scanner was unsure about
  selected: "F",           // colour currently selected for painting
  plan: null, stepIdx: 0, moveIdx: -1,
  mode: "beginner",
  stream: null, scan: { faces: {}, order: [], i: 0, onDone: null },
};

async function api(path, body) {
  const res = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}
const setMsg = (el, text, cls = "") => { el.textContent = text; el.className = "msg " + cls; };

/* ------------------------------------------------------------- net rendering */
function renderNet(container, facelets, opts = {}) {
  container.innerHTML = "";
  const cells = new Array(9 * 12).fill(null);
  for (const [face, cx, cy] of LAYOUT)
    for (let r = 0; r < 3; r++)
      for (let c = 0; c < 3; c++) cells[(cy + r) * 12 + cx + c] = BASE[face] + r * 3 + c;
  for (const idx of cells) {
    const d = document.createElement("div");
    if (idx === null) { d.className = "blank"; container.appendChild(d); continue; }
    const letter = facelets ? facelets[idx] : "?";
    d.className = "st" + (opts.editable ? " edit" : "") + (opts.highlight && opts.highlight.has(idx) ? " hl" : "")
      + (opts.low && opts.low.has(idx) ? " low" : "");
    d.style.background = app.palette[letter] || "#555";
    d.title = LETTERS.includes(letter) ? `${letter} face colour` : "";
    if (opts.editable) d.addEventListener("click", () => opts.onClick && opts.onClick(idx));
    container.appendChild(d);
  }
}
function faceIndices(face) { return new Set(Array.from({ length: 9 }, (_, i) => BASE[face] + i)); }

/* ------------------------------------------------------------- setup: editing */
function renderPalette() {
  const p = $("palette");
  p.innerHTML = "";
  for (const l of LETTERS) {
    const s = document.createElement("div");
    s.className = "sw" + (app.selected === l ? " sel" : "");
    s.style.background = app.palette[l];
    s.title = l;
    s.addEventListener("click", () => { app.selected = l; renderPalette(); });
    p.appendChild(s);
  }
}
function renderSetup() {
  $("netPane").hidden = false;
  renderPalette();
  renderNet($("netEdit"), app.facelets, {
    editable: true, low: app.low,
    onClick: (idx) => {
      if (CENTERS.has(idx)) return;                       // centres define the colours
      app.facelets = app.facelets.slice(0, idx) + app.selected + app.facelets.slice(idx + 1);
      app.low.delete(idx);
      renderSetup();
    },
  });
  const counts = LETTERS.split("").map((l) => `${l}:${[...app.facelets].filter((c) => c === l).length}`);
  $("counts").textContent = "Sticker counts (need 9 each): " + counts.join("  ");
  validateCurrent();
}
let validateSeq = 0;
async function validateCurrent() {
  const seq = ++validateSeq;
  $("btnSolveBeginner").disabled = $("btnSolveFast").disabled = true;
  try {
    const r = await api("/api/validate", { facelets: app.facelets });
    if (seq !== validateSeq) return;
    setMsg($("setupMsg"), r.message, r.valid ? "ok" : "bad");
    $("btnSolveBeginner").disabled = $("btnSolveFast").disabled = !r.valid;
  } catch (e) { setMsg($("setupMsg"), e.message, "bad"); }
}
function blankCubeFrom(facelets) { app.facelets = facelets; app.low = new Set(); renderSetup(); }

/* ------------------------------------------------------------- camera scan */
const SCAN_STEPS = [
  { face: "F", text: "FRONT: white (first-layer colour) on the bottom. Show the face you want to call the front." },
  { face: "R", text: "RIGHT: turn the whole cube so the face that was on your right now faces you. White still on the bottom." },
  { face: "B", text: "BACK: turn the cube once more, showing the face opposite the front." },
  { face: "L", text: "LEFT: turn once more, showing the left face." },
  { face: "U", text: "TOP: go back to the front, then tilt the top TOWARD you so the top face is shown, front edge at the bottom of the picture." },
  { face: "D", text: "BOTTOM: back to the front, then tilt the bottom TOWARD you, front edge at the top of the picture." },
];
async function startCamera() {
  try {
    app.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
    $("video").srcObject = app.stream; await $("video").play();
    $("btnCapture").disabled = false; $("btnRestartScan").disabled = false; $("btnStartCam").disabled = true;
    beginScan(null);
  } catch (e) {
    $("scanPrompt").textContent = "Camera not available (" + e.message + "). Camera needs HTTPS and permission; " +
      "you can still use “Enter / edit colours” or the random scramble.";
  }
}
function beginScan(onDone) {
  app.scan = { faces: {}, i: 0, onDone };
  showScanPrompt();
}
function showScanPrompt() {
  const s = SCAN_STEPS[app.scan.i];
  $("scanPrompt").textContent = `Face ${app.scan.i + 1} of 6 — ${s.text} Fill the grid with the face, then press Capture.`;
  $("scanProgress").textContent = Object.keys(app.scan.faces).join(" ") ? "Captured: " + Object.keys(app.scan.faces).join(" ") : "";
}
function sampleFace() {
  const v = $("video"), size = Math.min(v.videoWidth, v.videoHeight);
  if (!size) throw new Error("Camera not ready yet.");
  const cv = document.createElement("canvas"); cv.width = cv.height = 300;
  const ctx = cv.getContext("2d", { willReadFrequently: true });
  const sx = (v.videoWidth - size) / 2, sy = (v.videoHeight - size) / 2;
  ctx.drawImage(v, sx, sy, size, size, 0, 0, 300, 300);
  const inner = 0.12 * 300, cell = (300 - 2 * inner) / 3, out = [];
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    const cx = inner + (c + 0.5) * cell, cy = inner + (r + 0.5) * cell, half = cell * 0.2;   // central 40% of the cell
    const d = ctx.getImageData(cx - half, cy - half, half * 2, half * 2).data;
    let R = 0, G = 0, B = 0, n = d.length / 4;
    for (let i = 0; i < d.length; i += 4) { R += d[i]; G += d[i + 1]; B += d[i + 2]; }
    out.push([R / n, G / n, B / n]);
  }
  return out;
}
async function captureFace() {
  try {
    const step = SCAN_STEPS[app.scan.i];
    app.scan.faces[step.face] = sampleFace();
    app.scan.i++;
    if (app.scan.i < 6) { showScanPrompt(); return; }
    const patches = [];
    for (const f of LETTERS) patches.push(...app.scan.faces[f]);
    const r = await api("/api/classify", { patches });
    app.palette = { ...DEFAULT_PALETTE, ...Object.fromEntries(Object.entries(r.palette).map(([k, v]) => [k, `rgb(${v.join(",")})`])) };
    $("scanPrompt").textContent = "Scan complete. Check the coloured net; pink outlines are stickers I was unsure about.";
    const cb = app.scan.onDone;
    if (cb) cb(r); else { app.facelets = r.facelets; app.low = new Set(r.low_confidence); renderSetup(); }
  } catch (e) { $("scanPrompt").textContent = "Scan problem: " + e.message; app.scan.i = 0; app.scan.faces = {}; }
}

/* ------------------------------------------------------------- solving / learning */
async function solve(mode) {
  try {
    const plan = await api("/api/solve", { facelets: app.facelets, mode });
    startLearning(plan, mode);
  } catch (e) { setMsg($("setupMsg"), e.message, "bad"); }
}
function startLearning(plan, mode) {
  app.plan = plan; app.mode = mode; app.stepIdx = 0; app.moveIdx = -1;
  $("setup").hidden = true; $("learn").hidden = false;
  $("explainOut").textContent = ""; $("askOut").textContent = ""; setMsg($("checkMsg"), "");
  $("btnReplan").hidden = true; app.pendingActual = null;
  renderLearn();
}
const curStep = () => app.plan.steps[app.stepIdx];
function currentState() {
  if (!app.plan.steps.length) return app.plan.start;
  const s = curStep();
  return app.moveIdx < 0 ? s.before : s.states[app.moveIdx];
}
function nextMove() {
  const s = curStep();
  return app.moveIdx + 1 < s.moves.length ? s.moves[app.moveIdx + 1] : null;
}
function renderLearn() {
  const plan = app.plan;
  if (!plan.steps.length) {
    renderNet($("netLearn"), plan.start, {});
    $("stepTitle").textContent = "Your cube is already solved!";
    $("moveChips").innerHTML = ""; $("stepText").textContent = ""; $("progressText").textContent = "";
    $("stageList").innerHTML = ""; return;
  }
  const s = curStep(), nm = nextMove();
  renderNet($("netLearn"), currentState(), { highlight: nm ? faceIndices(nm[0]) : null });
  $("stepTitle").textContent = `${s.stage_title}${plan.mode === "beginner" ? "" : ""}`;
  $("moveChips").innerHTML = s.moves.map((m, i) =>
    `<span class="chip ${i <= app.moveIdx ? "done" : i === app.moveIdx + 1 ? "now" : ""}">${m}</span>`).join("");
  $("stepText").textContent = s.text;
  const total = plan.total_moves;
  const done = plan.steps.slice(0, app.stepIdx).reduce((a, x) => a + x.moves.length, 0) + app.moveIdx + 1;
  $("progressText").textContent = `Move ${done} of ${total}` + (nm ? ` — next: ${nm}` : "");
  const sl = $("stageList"); sl.innerHTML = "";
  for (const st of plan.stages) {
    const li = document.createElement("li"); li.textContent = st.title;
    li.className = st.stage < s.stage ? "done" : st.stage === s.stage ? "now" : ""; sl.appendChild(li);
  }
  $("btnPrev").disabled = app.stepIdx === 0 && app.moveIdx < 0;
  const last = app.stepIdx === plan.steps.length - 1 && app.moveIdx === s.moves.length - 1;
  $("btnNext").disabled = last;
  if (last) setMsg($("checkMsg"), "Solved! 🎉 Scramble it and try again.", "ok");
}
function goNext() {
  const s = curStep();
  if (app.moveIdx + 1 < s.moves.length) app.moveIdx++;
  else if (app.stepIdx + 1 < app.plan.steps.length) { app.stepIdx++; app.moveIdx = 0; $("explainOut").textContent = ""; }
  renderLearn();
}
function goPrev() {
  if (app.moveIdx >= 0) app.moveIdx--;
  else if (app.stepIdx > 0) { app.stepIdx--; app.moveIdx = curStep().moves.length - 2; $("explainOut").textContent = ""; }
  renderLearn();
}
async function explain() {
  const s = curStep();
  $("explainOut").textContent = "Thinking…";
  try {
    const r = await api("/api/explain", { step: s });
    $("explainOut").textContent = r.text + (r.source === "llm" ? "" : "");
  } catch (e) { $("explainOut").textContent = e.message; }
}
async function ask() {
  const q = $("askInput").value.trim(); if (!q) return;
  $("askOut").textContent = "Looking it up…";
  try { $("askOut").textContent = (await api("/api/ask", { question: q })).answer; }
  catch (e) { $("askOut").textContent = e.message; }
}

/* ------------------------------------------------------------- checking the learner's cube */
function beforeCurrentMove() {   // state before the move the learner is about to make
  return currentState();
}
async function checkWithCamera() {
  if (!app.stream) { setMsg($("checkMsg"), "Start the camera on the first screen to use scanning, or use “I did a different move”.", "bad"); return; }
  $("setup").hidden = false; $("learn").hidden = true; setTab("camera"); $("netPane").hidden = true;
  beginScan(async (r) => {
    try {
      const before = app.plan.steps.length ? (app.moveIdx < 0 ? curStep().before : curStep().states[app.moveIdx]) : app.plan.start;
      const expected = nextMove();
      const d = await api("/api/check", { state_before: before, actual_state: r.facelets, expected_move: expected });
      $("setup").hidden = true; $("learn").hidden = false;
      setMsg($("checkMsg"), d.message + (d.status === "different_move" || d.status === "unknown" ? "" : ""), d.status === "match" ? "ok" : "bad");
      app.pendingActual = d.status === "match" ? null : r.facelets;
      $("btnReplan").hidden = !app.pendingActual;
    } catch (e) { $("setup").hidden = true; $("learn").hidden = false; setMsg($("checkMsg"), e.message, "bad"); }
  });
}
async function replanFrom(facelets) {
  try { startLearning(await api("/api/solve", { facelets, mode: app.mode }), app.mode); }
  catch (e) { setMsg($("checkMsg"), e.message, "bad"); }
}
async function wrongMove() {
  try {
    const before = beforeCurrentMove();
    const r = await api("/api/apply", { facelets: before, moves: [$("wrongMove").value] });
    await replanFrom(r.facelets);
  } catch (e) { setMsg($("checkMsg"), e.message, "bad"); }
}

/* ------------------------------------------------------------- wiring */
function setTab(name) {
  $("tabCamera").classList.toggle("active", name === "camera");
  $("tabManual").classList.toggle("active", name === "manual");
  $("cameraPane").hidden = name !== "camera";
  if (name === "manual" && !app.facelets) blankCubeFrom("U".repeat(9) + "R".repeat(9) + "F".repeat(9) + "D".repeat(9) + "L".repeat(9) + "B".repeat(9));
}
window.addEventListener("DOMContentLoaded", async () => {
  $("wrongMove").innerHTML = ALL_MOVES.map((m) => `<option>${m}</option>`).join("");
  $("tabCamera").onclick = () => setTab("camera");
  $("tabManual").onclick = () => setTab("manual");
  $("btnDemo").onclick = async () => { try { const r = await api("/api/scramble", {}); app.palette = { ...DEFAULT_PALETTE }; blankCubeFrom(r.facelets); } catch (e) { setMsg($("setupMsg"), e.message, "bad"); } };
  $("btnStartCam").onclick = startCamera;
  $("btnCapture").onclick = captureFace;
  $("btnRestartScan").onclick = () => beginScan(app.scan.onDone);
  $("btnSolveBeginner").onclick = () => solve("beginner");
  $("btnSolveFast").onclick = () => solve("fast");
  $("btnNext").onclick = goNext; $("btnPrev").onclick = goPrev;
  $("btnExplain").onclick = explain; $("btnCheck").onclick = checkWithCamera;
  $("btnAsk").onclick = ask; $("askInput").addEventListener("keydown", (e) => { if (e.key === "Enter") ask(); });
  $("btnWrong").onclick = wrongMove;
  $("btnReplan").onclick = () => app.pendingActual && replanFrom(app.pendingActual);
  $("btnReset").onclick = () => { $("learn").hidden = true; $("setup").hidden = false; app.plan = null; };
  try { const h = await api("/api/health"); $("llmBadge").textContent = h.llm ? "AI explanations: on" : "AI explanations: off (built-in text)"; }
  catch { $("llmBadge").textContent = "server unreachable"; }
});
