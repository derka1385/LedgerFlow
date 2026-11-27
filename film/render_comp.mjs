import { chromium } from "/Users/petrinolann/Coding/vultr/frontend/node_modules/playwright/index.mjs";
const M = { mode: "mac", x: 80, y: 110, w: 1240, h: 805, tx: 1400, ty: 300, tw: 450 };
const P = { mode: "phone", x: 330, y: 90, w: 416, h: 900, tx: 900, ty: 330, tw: 860 };
const jobs = {
  bg: { part: "bg" },
  ma: { ...M, tag: "Real recording · Mac app", title: "Sign in. Name your agent.", sub: "Google sign-in, a workspace on your Mac, and an agent called Atlas.", note: "Screen recording · pauses cut" },
  mb: { ...M, tag: "Real recording · Mac app", title: "Bring your own Excel.", sub: "LedgerFlow maps its accounts and write areas, then you confirm.", note: "Screen recording · pauses cut" },
  pa: { ...P, tag: "Real recording · iPhone 13 Pro · optional", title: "Pair once. Scan anywhere.", sub: "The iPhone connects to the Mac over local Wi-Fi, then the camera scans a real Rusta receipt.", note: "Screen recording · pauses cut" },
  md: { ...M, tag: "Real recording · Mac app", title: "The receipt lands on the Mac.", sub: "Read by Vultr inference, every field shown with its source. Anything uncertain waits for a human.", note: "Screen recording · pauses cut" },
  nt: { ...P, tag: "Real notification · iPhone lock screen", title: "Human approval.", sub: "LedgerFlow · Review needed — the agent prepares, a person decides. Nothing is written before that.", note: "Screenshot from the iPhone, 27 Nov 2026" },
  beta: { mode: "card", tx: 160, ty: 330, tw: 1600, tag: "LedgerFlow · beta", title: "Try the beta.", sub: "Mac app · web agent · iPhone app (optional). Your receipts, your Excel.", note: "Ask the team for access" },
  pb: { ...P, tag: "Real recording · iPhone", title: "Status flows back.", sub: "History, this month's total and the agent — the same workspace, on the phone.", note: "Screen recording · pauses cut" },
};
const b = await chromium.launch({ channel: "chrome", headless: true });
const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
for (const [name, q] of Object.entries(jobs)) {
  await p.goto("http://127.0.0.1:8799/comp.html?" + new URLSearchParams(q)); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(200);
  await p.screenshot({ path: `/Users/petrinolann/Coding/vultr/film/comp/${name}.png`, omitBackground: name !== "bg" });
}
await b.close(); console.log(JSON.stringify({ M, P }));
