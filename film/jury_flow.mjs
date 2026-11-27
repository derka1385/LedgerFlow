// Jury path: landing button -> web app (no account) -> sample workbook in the Excel grid -> receipt -> agent -> approve -> .xlsx download.
import { chromium, devices } from "/Users/petrinolann/Coding/vultr/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = process.env.BASE || "http://localhost:8790", OUT = "/Users/petrinolann/Coding/vultr/film/jury";
const mode = process.argv[2] || "desktop";
const ctxOpts = mode === "android" ? { ...devices["Pixel 7"] } : { viewport: { width: 1440, height: 900 } };
const b = await chromium.launch({ channel: "chrome", headless: true });
const ctx = await b.newContext({ ...ctxOpts, acceptDownloads: true });
const p = await ctx.newPage();
const res = []; const ok = (k, v) => { res.push(`${v ? "PASS" : "FAIL"}  ${k}`); };
const shot = (n) => p.screenshot({ path: `${OUT}/${mode}_${n}.png` });
const api = (path, opts = {}) => p.evaluate(async ([path, opts]) => { const r = await fetch("/api/v1" + path, { credentials: "include", ...opts }); return { status: r.status, body: await r.json().catch(() => null) }; }, [path, opts]);
try {
  await p.goto(BASE + "/welcome/"); await p.waitForTimeout(1500); await shot("01_landing");
  const btn = p.locator("[data-app-link]:visible").first();
  ok("landing shows 'Open the web app'", (await btn.innerText()).includes("Open the web app"));
  await btn.click(); await p.waitForTimeout(3500); await shot("02_app");
  const sess = await api("/auth/session"); ok(`signed in without account (role=${sess.body?.role})`, sess.status === 200);
  // workbook: reuse a ready one or connect the sample
  let wbs = (await api("/workbooks")).body.items; let ready = wbs.find(w => w.status === "ready");
  if (!ready) {
    await p.goto(BASE + "/#/workbook"); await p.waitForTimeout(1500);
    await p.getByRole("button", { name: /Use sample workbook/ }).click(); await p.waitForTimeout(600);
    await p.getByRole("button", { name: /Upload and inspect/ }).click(); await p.waitForTimeout(3000);
    const c = p.getByRole("button", { name: /^Confirm mapping/ }); await c.scrollIntoViewIfNeeded(); await c.click(); await p.waitForTimeout(2500);
    wbs = (await api("/workbooks")).body.items; ready = wbs.find(w => w.status === "ready");
  }
  ok("sample workbook connected and ready", !!ready);
  await p.goto(BASE + `/#/sheet/${ready.workbook_id}`); await p.waitForTimeout(2500); await shot("03_excel_grid");
  ok("workbook opens in the Excel grid", (await p.locator("table td, [role=gridcell]").count()) > 50);
  // receipt
  const before = new Set(((await api("/runs")).body.items || []).map(r => r.run_id));
  await p.goto(BASE + "/#/capture"); await p.waitForTimeout(2000);
  await p.locator("#sample").selectOption({ index: +(process.env.SAMPLE || 1) }); await p.waitForTimeout(1500);
  await p.getByRole("button", { name: /Use this photo|Read receipt/ }).click(); await p.waitForTimeout(3000); await shot("04_receipt_sent");
  let run = null;
  for (let i = 0; i < 40; i++) { const r = (await api("/runs")).body.items; run = r.find(x => !before.has(x.run_id)); if (run && ["AWAITING_APPROVAL","NEEDS_REVIEW","FAILED","DUPLICATE_REVIEW","COMMITTED"].includes(run.state)) break; await p.waitForTimeout(2500); }
  if (run?.state === "DUPLICATE_REVIEW") {  // another tester already sent this sample: release it the way a judge would
    ok(`duplicate detected and shown (${run.merchant_name})`, true);
    await p.goto(BASE + `/#/transactions/${run.run_id}`); await p.waitForTimeout(2500); await shot("05b_duplicate");
    await p.getByRole("button", { name: /Different purchase: continue/ }).click();
    for (let i = 0; i < 40; i++) { run = (await api(`/runs/${run.run_id}`)).body; if (["AWAITING_APPROVAL","NEEDS_REVIEW","FAILED"].includes(run.state)) break; await p.waitForTimeout(2500); }
  }
  ok(`receipt processed (state=${run?.state}, ${run?.merchant_name || run?.transaction?.merchant_name})`, run?.state === "AWAITING_APPROVAL");
  // agent
  await p.goto(BASE + "/#/agent"); await p.waitForTimeout(1500);
  await p.locator("#agent-message").fill("Which receipt is waiting for my approval?"); await p.keyboard.press("Enter");
  let reply = null; for (let i = 0; i < 30; i++) { const m = (await api("/assistant/messages")).body?.items || []; const a = m.filter(x => x.role === "assistant"); if (a.length) { reply = a.at(-1).text; break; } await p.waitForTimeout(2000); }
  await p.waitForTimeout(800); await shot("05_agent");
  ok(`agent answered: "${(reply || "").slice(0, 90).replace(/\n/g, " ")}…"`, !!reply);
  // approve
  await p.goto(BASE + `/#/transactions/${run.run_id}`); await p.waitForTimeout(3000);
  const ap = p.getByRole("button", { name: /Approve and write/ }); await ap.scrollIntoViewIfNeeded(); await shot("06_review");
  await ap.click(); await p.waitForTimeout(6000);
  const after = (await api(`/runs/${run.run_id}`)).body; ok(`entry approved and committed (state=${after.state})`, after.state === "COMMITTED");
  await shot("07_committed");
  const dl = p.getByRole("button", { name: /Download \.xlsx/ }).or(p.getByRole("link", { name: /Download \.xlsx/ })).first();
  await dl.scrollIntoViewIfNeeded();
  const [d] = await Promise.all([p.waitForEvent("download", { timeout: 20000 }), dl.click()]);
  const file = `${OUT}/${mode}_${d.suggestedFilename()}`; await d.saveAs(file);
  ok(`modified .xlsx downloaded (${d.suggestedFilename()}, ${fs.statSync(file).size} bytes)`, fs.statSync(file).size > 5000);
  // phone camera entry from the landing
  await p.goto(BASE + "/welcome/"); await p.waitForTimeout(1000);
  const cam = p.locator('[data-app-link][data-role="employee"]:visible').first();
  if (await cam.count()) { await cam.click(); await p.waitForTimeout(3000); ok("'Try the phone camera' opens capture", /capture/.test(p.url()) || await p.getByText(/Take photo|Upload a file/).first().isVisible()); await shot("08_camera"); }
} catch (e) { res.push("FAIL  " + e.message.split("\n")[0]); await shot("zz_error"); }
console.log(`== ${mode}\n` + res.join("\n")); await b.close();
