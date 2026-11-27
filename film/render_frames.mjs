import { chromium } from "/Users/petrinolann/Coding/vultr/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs"; import { execFileSync } from "node:child_process";
const FPS = 30, ROOT = "/Users/petrinolann/Coding/vultr/film";
const scenes = process.argv.slice(2);
const b = await chromium.launch({ channel: "chrome", headless: true });
const SCALE = +(process.env.SCALE || 1);  // 1.3333 -> 2560x1440
const p = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: SCALE });
for (const s of scenes) {
  const dir = `${ROOT}/frames/${s}`; fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
  await p.goto(`http://127.0.0.1:8799/film.html#${s}`); await p.reload(); await p.evaluate(() => document.fonts.ready);
  await p.evaluate(() => Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; }))));
  const dur = await p.evaluate(() => window.SCENE_DUR), n = Math.round(dur * FPS);
  for (let f = 0; f < n; f++) {
    await p.evaluate(ms => window.seek(ms), f * 1000 / FPS);
    fs.writeFileSync(`${dir}/${String(f).padStart(5, "0")}.jpg`, await p.screenshot({ type: "jpeg", quality: 90 }));
  }
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", String(FPS), "-i", `${dir}/%05d.jpg`, "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", `${ROOT}/${process.env.OUTDIR || "scenes"}/${s}.mp4`]);
  console.log(new Date().toISOString().slice(11, 19), s, n, "frames");
}
await b.close();
