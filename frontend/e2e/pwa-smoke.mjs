import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const base = process.env.LEDGERFLOW_TEST_URL || 'http://127.0.0.1:8789';
const browser = await chromium.launch({ channel: 'chrome', headless: true });
try {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(base);
  await page.evaluate(async () => { await navigator.serviceWorker.ready; });
  await page.reload();
  await page.waitForFunction(() => !!navigator.serviceWorker.controller);
  const cached = await page.evaluate(async () => {
    const names = (await caches.keys()).filter(n => n.startsWith('ledgerflow-public-'));
    return (await Promise.all(names.map(async n => (await (await caches.open(n)).keys()).map(r => new URL(r.url).pathname)))).flat();
  });
  assert(cached.includes('/offline.html'));
  assert(cached.every(p => p === '/offline.html' || p.startsWith('/icons/')));
  assert(!cached.some(p => p.startsWith('/api/') || p === '/' || p === '/index.html'));
  console.log('PASS service worker caches public offline assets only');
  const manifest = await (await context.request.get(`${base}/manifest.webmanifest`)).json();
  assert.equal(manifest.display, 'standalone');
  for (const icon of manifest.icons) assert.equal((await context.request.get(new URL(icon.src, base).href)).status(), 200);
  console.log('PASS manifest and install icons are available');
  await context.setOffline(true);
  await page.reload();
  await page.getByRole('heading', { name: 'Your workspace needs a connection.' }).waitFor();
  assert.equal(await page.locator('.metric, .transaction-item').count(), 0);
  console.log('PASS offline navigation shows a public explanation without cached financial data');
} finally { await browser.close(); }
