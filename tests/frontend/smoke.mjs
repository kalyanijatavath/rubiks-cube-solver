// DOM smoke test: loads the real index.html + app.js in jsdom against a running server.
// Usage: BASE=http://127.0.0.1:5055 node smoke.mjs      (camera flow is not covered)
import { JSDOM } from "jsdom";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const BASE = process.env.BASE || "http://127.0.0.1:5000";
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "rubik_tutor", "static");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8").replace(/<script src="[^"]*"><\/script>/, "");
const dom = new JSDOM(html, { runScripts: "outside-only", url: BASE + "/", pretendToBeVisual: true });
const { window } = dom;
window.fetch = (u, o) => fetch(u.startsWith("http") ? u : BASE + u, o);
window.eval(fs.readFileSync(path.join(root, "app.js"), "utf8"));
window.document.dispatchEvent(new window.Event("DOMContentLoaded"));

const $ = (id) => window.document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function until(cond, what, ms = 8000) {
  const t0 = Date.now();
  while (!cond()) { if (Date.now() - t0 > ms) throw new Error("timeout waiting for " + what); await sleep(30); }
}
let checks = 0;
const ok = (c, m) => { if (!c) throw new Error("FAIL: " + m); checks++; console.log("ok -", m); };

await until(() => /AI explanations/.test($("llmBadge").textContent), "health badge");
ok(true, "page loads and reaches /api/health");

$("btnDemo").click();
await until(() => !$("btnSolveBeginner").disabled, "valid scramble enabling Solve");
ok($("netEdit").querySelectorAll(".st").length === 54, "net shows 54 stickers");
ok(/need 9 each/.test($("counts").textContent) && /U:9/.test($("counts").textContent), "sticker counts shown");

// break the cube by painting a sticker, expect Solve disabled, then fix by repainting
const first = $("netEdit").querySelectorAll(".st")[0];
const current = first.title[0];                              // letter currently on that sticker
const other = [...$("palette").children].find((sw) => sw.title !== current);
other.dispatchEvent(new window.Event("click"));              // choose a different colour...
$("netEdit").querySelectorAll(".st")[0].dispatchEvent(new window.Event("click"));   // ...and paint the sticker
await until(() => /nine times|cannot occur/.test($("setupMsg").textContent), "invalid cube explained");
ok($("btnSolveBeginner").disabled, "invalid cube disables Solve and tells the user why");
$("btnDemo").click();
await until(() => !$("btnSolveBeginner").disabled, "new valid scramble");

$("btnSolveBeginner").click();
await until(() => !$("learn").hidden, "learning view");
ok($("stageList").children.length === 7, "seven stages listed");
let guard = 0;
while (!$("btnNext").disabled && guard++ < 400) $("btnNext").click();
ok(/Solved/.test($("checkMsg").textContent), `stepped through the whole solution (${guard} clicks) and reached Solved`);
ok(/Move \d+ of \d+/.test($("progressText").textContent), "progress text shown");

$("btnExplain").click();
await until(() => $("explainOut").textContent.length > 20 && $("explainOut").textContent !== "Thinking…", "explanation");
ok(true, "explain endpoint text displayed");
$("askInput").value = "what does a prime mark mean?"; $("btnAsk").click();
await until(() => /prime/i.test($("askOut").textContent), "answer");
ok(true, "ask endpoint answer displayed");

// "I did a different move" -> re-plan from the resulting cube
$("btnReset").click();
$("btnDemo").click(); await until(() => !$("btnSolveBeginner").disabled, "scramble");
$("btnSolveBeginner").click(); await until(() => !$("learn").hidden, "learning view");
$("wrongMove").value = "R'"; $("btnWrong").click();
await until(() => /Move \d+ of \d+/.test($("progressText").textContent) && !$("learn").hidden, "re-plan");
ok(true, "re-plan after a wrong move works");
console.log(`\nfrontend smoke test passed (${checks} checks)`);
process.exit(0);
