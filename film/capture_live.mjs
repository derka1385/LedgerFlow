// Records genuine LedgerFlow footage against the live demo backend (real Vultr inference, real Docker sandbox).
import { chromium } from "/Users/petrinolann/Coding/vultr/frontend/node_modules/playwright/index.mjs";
const BASE = process.env.BASE || "http://localhost:8790";
const OUT = "/Users/petrinolann/Coding/vultr/film/footage";
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
const b = await chromium.launch({ channel: "chrome", headless: true });
const desk = await b.newContext({ viewport: { width: 1920, height: 1080 }, colorScheme: "light", acceptDownloads: true });
const p = await desk.newPage();
const shot = async (pg, n) => { await pg.screenshot({ path: `${OUT}/${n}.png` }); log("shot", n); };
async function login(pg, invite) {
  await pg.goto(BASE + "/"); await pg.evaluate(() => localStorage.setItem("ledgerflow.howSeen", "1"));
  await pg.getByPlaceholder("Paste your invite").fill(invite); await pg.keyboard.press("Enter"); await pg.waitForTimeout(1800);
}
await login(p, "owner-demo");
await p.goto(BASE + "/#/workbook"); await p.waitForTimeout(1500); await shot(p, "01_workbook_empty");
await p.getByRole("button", { name: /Use sample workbook/ }).click(); await p.waitForTimeout(800);
await p.getByRole("button", { name: /Upload and inspect/ }).click(); await p.waitForTimeout(3500);
await shot(p, "02_workbook_inspected");
await p.mouse.wheel(0, 700); await p.waitForTimeout(900); await shot(p, "03_workbook_accounts"); await p.mouse.wheel(0, -700);
const conf = p.getByRole("button", { name: /^Confirm mapping/ });
await conf.scrollIntoViewIfNeeded({ timeout: 8000 }); await p.waitForTimeout(600); await shot(p, "03b_confirm"); await conf.click({ timeout: 8000 }); await p.waitForTimeout(3000); await p.evaluate(() => window.scrollTo(0, 0));
await shot(p, "04_workbook_ready");
// employee on phone
const phone = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
const q = await phone.newPage();
await login(q, "employee-demo");
await q.goto(BASE + "/#/capture"); await q.waitForTimeout(1500); await shot(q, "05_phone_capture");
await q.locator("#sample").selectOption({ index: 1 }); await q.waitForTimeout(1500); await shot(q, "06_phone_preview");
await q.getByRole("button", { name: /Use this photo|Read receipt/ }).click(); await q.waitForTimeout(4000); await shot(q, "07_phone_sent");
// owner follows the run
await p.goto(BASE + "/#/transactions"); await p.waitForTimeout(2000); await shot(p, "08_transactions_processing");
let run = null;
for (let i = 0; i < 60; i++) {
  const r = await p.evaluate(() => fetch("/api/v1/runs", { credentials: "include" }).then(x => x.json()));
  run = r.items.find(x => x.merchant_name || x.state);
  if (run && ["AWAITING_APPROVAL", "NEEDS_REVIEW", "FAILED", "DUPLICATE_REVIEW"].includes(run.state)) break;
  await p.waitForTimeout(2500);
}
log("run", run && run.run_id, run && run.state);
await p.goto(BASE + `/#/transactions/${run.run_id}`); await p.waitForTimeout(2500); await shot(p, "09_review_top");
await p.mouse.wheel(0, 900); await p.waitForTimeout(1200); await shot(p, "10_review_grid");
await p.mouse.wheel(0, 900); await p.waitForTimeout(1200); await shot(p, "11_review_checks");
await p.mouse.wheel(0, -1800); await p.waitForTimeout(600);
const mon = p.getByRole("link", { name: /Execution monitor/ }).or(p.getByRole("button", { name: /Execution monitor/ }));
if (await mon.first().isVisible().catch(() => false)) { await mon.first().click(); await p.waitForTimeout(2500); await shot(p, "12_monitor"); await p.mouse.wheel(0, 900); await p.waitForTimeout(1000); await shot(p, "13_monitor_code"); await p.goBack(); await p.waitForTimeout(2000); }
const appr = p.getByRole("button", { name: /Approve and write/ });
if (await appr.isVisible().catch(() => false)) {
  await appr.scrollIntoViewIfNeeded(); await p.waitForTimeout(800); await shot(p, "14_before_approve");
  await appr.click(); await p.waitForTimeout(6000); await shot(p, "15_committed");
  const dl = p.getByRole("button", { name: /Download \.xlsx/ }).or(p.getByRole("link", { name: /Download \.xlsx/ }));
  if (await dl.first().isVisible().catch(() => false)) {
    const [d] = await Promise.all([p.waitForEvent("download"), dl.first().click()]);
    await d.saveAs(OUT + "/committed_workbook.xlsx"); log("downloaded", await d.suggestedFilename());
  }
}
const snap = await p.evaluate((id) => fetch(`/api/v1/runs/${id}`, { credentials: "include" }).then(x => x.json()), run.run_id);
const fs = await import("node:fs"); fs.writeFileSync(OUT + "/run_snapshot.json", JSON.stringify(snap, null, 1));
await q.goto(BASE + "/#/home"); await q.waitForTimeout(2500); await shot(q, "16_phone_home");
await desk.close(); await phone.close(); await b.close(); log("done");
