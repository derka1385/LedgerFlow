import { chromium } from "/Users/petrinolann/Coding/vultr/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://localhost:8790", OUT = "/Users/petrinolann/Coding/vultr/film/footage";
const snap = JSON.parse(fs.readFileSync(OUT + "/run_snapshot.json", "utf8"));
const b = await chromium.launch({ channel: "chrome", headless: true });
const p = await (await b.newContext({ viewport: { width: 1920, height: 1080 } })).newPage();
await p.goto(BASE + "/"); await p.evaluate(() => localStorage.setItem("ledgerflow.howSeen", "1"));
await p.getByPlaceholder("Paste your invite").fill("owner-demo"); await p.keyboard.press("Enter"); await p.waitForTimeout(1800);
const code = await p.evaluate(id => fetch(`/api/v1/artifacts/${id}/download`, { credentials: "include" }).then(r => r.status + "\n" + "").then(async s => s), snap.code_artifact_id);
const text = await p.evaluate(id => fetch(`/api/v1/artifacts/${id}/download`, { credentials: "include" }).then(r => r.text()), snap.code_artifact_id);
fs.writeFileSync(OUT + "/generated_program.py", text); console.log("artifact status", code.trim(), text.length, "bytes");
await p.goto(BASE + `/#/transactions/${snap.run_id}`); await p.waitForTimeout(2500);
await p.getByRole("button", { name: /Execution monitor/ }).or(p.getByRole("link", { name: /Execution monitor/ })).first().click(); await p.waitForTimeout(2000);
const vc = p.getByText(/View code/).first();
if (await vc.isVisible().catch(() => false)) { await vc.click(); await p.waitForTimeout(1500); await p.screenshot({ path: OUT + "/17_view_code.png" }); }
await b.close();
