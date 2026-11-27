import { chromium } from "/Users/petrinolann/Coding/vultr/frontend/node_modules/playwright/index.mjs";
const b = await chromium.launch({ channel: "chrome", headless: true });
const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
const scenes = process.argv.slice(2);
for (const s of scenes) {
  await p.goto(`http://127.0.0.1:8799/film.html#${s}`); await p.reload(); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(400);
  const dur = await p.evaluate(() => window.SCENE_DUR);
  for (const t of [dur * 0.55, dur - 0.3]) { await p.evaluate(ms => window.seek(ms), t * 1000); await p.screenshot({ path: `/tmp/still_${s}_${Math.round(t)}.jpg`, type: "jpeg", quality: 70 }); }
}
await b.close();
