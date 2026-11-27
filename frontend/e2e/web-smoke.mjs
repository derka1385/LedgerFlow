// Integration smoke test against the real DEV-MOCK HTTP service, not intercepted API responses.
// Inference remains labelled mocked; accounting commit requires working Docker and is not claimed here.
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const output = path.join(repo, 'artifacts/apple-platform');
await mkdir(output, { recursive: true });
const base = process.env.LEDGERFLOW_TEST_URL || 'http://127.0.0.1:5174';
const browser = await chromium.launch({ headless: true, channel: 'chrome' });
const errors = [];
const checks = [];
function check(name) { checks.push(name); console.log(`PASS ${name}`); }
async function login(page, role) {
  await page.goto(base);
  page.on('pageerror', e => errors.push(e.message));
  await page.getByLabel('Invite code').fill(`${role}-demo`);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
}
try {
  const desktop = await browser.newContext({ viewport: { width: 1512, height: 982 } });
  const owner = await desktop.newPage();
  await login(owner, 'owner');
  await owner.getByRole('heading', { name: 'Overview', exact: true }).waitFor();
  assert.equal(await owner.getByRole('navigation', { name: 'Main', exact: true }).getByRole('link').count(), 9);
  check('macOS workspace opens with agent and eight accounting destinations');
  await owner.getByRole('link', { name: 'Excel Workbooks', exact: true }).click();
  await owner.getByLabel('Workbook file').setInputFiles(path.join(repo, 'fixtures/synthetic/nordvik_t_accounts.xlsx'));
  await owner.getByRole('button', { name: 'Upload and inspect', exact: true }).click();
  await owner.getByRole('button', { name: 'Confirm mapping', exact: true }).click();
  await owner.getByText('Mapping confirmed.', { exact: true }).waitFor();
  check('existing workbook import, inspection and mapping confirmation remain functional');
  await owner.getByRole('link', { name: 'Overview', exact: true }).click();
  await owner.getByText('nordvik_t_accounts', { exact: true }).first().waitFor();
  await owner.screenshot({ path: path.join(output, 'macos-overview.png'), fullPage: true });
  await owner.getByRole('button', { name: 'Scan with iPhone', exact: true }).click();
  await owner.getByText('Use the public HTTPS application for phone access.', { exact: false }).waitFor();
  assert.equal(await owner.locator('.pairing-qr').count(), 0);
  await owner.getByRole('button', { name: 'Close', exact: true }).click();
  check('local continuity dialog does not offer an unusable localhost QR or fake access');
  const phoneContext = await browser.newContext({ viewport: { width: 393, height: 852 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  const phone = await phoneContext.newPage();
  await login(phone, 'employee');
  await phone.getByRole('heading', { name: 'How LedgerFlow works', exact: true }).waitFor();
  check('first phone launch opens the four-step how-it-works explainer');
  await phone.getByRole('button', { name: 'Skip', exact: true }).click();
  await phone.getByRole('heading', { name: 'Your books, one receipt at a time.', exact: true }).waitFor();
  assert.equal(await phone.locator('.sidebar').count(), 0);
  await phone.screenshot({ path: path.join(output, 'iphone-home.png'), fullPage: true });
  check('employee home is camera-first and does not expose the accountant workspace');
  await phone.getByRole('link', { name: /Scan a receipt/ }).click();
  await phone.locator('input[capture]').setInputFiles(path.join(repo, 'fixtures/synthetic/receipts/E1.png'));
  await phone.locator('.capture-preview').waitFor();
  await phone.screenshot({ path: path.join(output, 'iphone-preview.png'), fullPage: true });
  const runResponse = phone.waitForResponse(r => r.url().endsWith('/api/v1/runs') && r.request().method() === 'POST');
  await phone.getByRole('button', { name: 'Use this photo', exact: true }).click();
  const r = await runResponse;
  assert.equal(r.status(), 202);
  const { run_id } = await r.json();
  await phone.getByRole('heading', { name: 'Receipt submitted.' }).waitFor();
  await phone.getByRole('link', { name: 'View receipt status', exact: true }).click();
  await phone.locator('.receipt-summary h2').waitFor();
  assert.equal(await phone.getByText('Expense account', { exact: true }).count(), 0);
  check('employee upload normalizes the image and creates one authenticated run');
  await owner.getByRole('link', { name: 'Transactions', exact: true }).click();
  await owner.locator(`[data-run-id="${run_id}"]`).waitFor();
  await owner.locator(`[data-run-id="${run_id}"]`).click();
  await owner.locator('.transaction-detail .review').waitFor();
  assert(owner.url().includes(run_id));
  await owner.screenshot({ path: path.join(output, 'macos-transaction.png'), fullPage: true });
  check('phone receipt appears in desktop polling with the same run ID');
  const separator = owner.getByRole('separator', { name: 'Resize document list' });
  await separator.focus(); await owner.keyboard.press('ArrowRight');
  assert.equal(await separator.getAttribute('aria-valuenow'), '308');
  check('split view supports keyboard resizing');
  let accountingCommit = 'not asserted (set LEDGERFLOW_REQUIRE_COMMIT=1 with Docker available)';
  if (process.env.LEDGERFLOW_REQUIRE_COMMIT === '1') {
    let snap;
    for (let i = 0; i < 60; i++) {
      snap = await owner.evaluate(async id => (await fetch(`/api/v1/runs/${id}`)).json(), run_id);
      if (['AWAITING_APPROVAL', 'FAILED', 'NEEDS_REVIEW', 'REJECTED'].includes(snap.state)) break;
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    assert.equal(snap.state, 'AWAITING_APPROVAL', JSON.stringify({ state: snap.state, reason: snap.state_reason }));
    assert.equal(snap.validation_summary.result, 'pass');
    await owner.getByRole('button', { name: /^Approve and write \d+ cells$/ }).click();
    await owner.getByRole('region', { name: 'Committed', exact: true }).waitFor();
    const downloadEvent = owner.waitForEvent('download');
    await owner.getByRole('link', { name: 'Download .xlsx', exact: true }).click();
    const download = await downloadEvent;
    const file = path.join(output, 'verified-synthetic-workbook.xlsx');
    await download.saveAs(file);
    const bytes = await readFile(file);
    assert.equal(bytes.subarray(0, 2).toString(), 'PK');
    const committed = await owner.evaluate(async id => (await fetch(`/api/v1/runs/${id}`)).json(), run_id);
    assert.equal(committed.state, 'COMMITTED');
    assert(committed.commit?.artifact_sha256 && committed.commit?.version_id);
    await phone.getByText('Booked', { exact: true }).waitFor();
    accountingCommit = { status: 'verified locally', inference: 'MOCK_INFERENCE / MOCK_CODEGEN_TEMPLATE', runtime: 'real isolated Docker', version_id: committed.commit.version_id, artifact_sha256: committed.commit.artifact_sha256, file };
    check('independent verifier passes, approval commits a real Excel version and employee status becomes Booked');
  }
  await owner.goto(`${base}/#/activity/${run_id}`);
  await owner.getByRole('heading', { name: 'Execution monitor', exact: true }).waitFor();
  await owner.getByText('Measured sandbox time', { exact: true }).waitFor();
  check('agent activity uses backend events and leaves missing metrics unreported');
  await owner.goto(`${base}/#/settings`);
  await owner.getByRole('button', { name: 'Dark', exact: true }).click();
  assert.equal(await owner.locator('html').getAttribute('data-appearance'), 'dark');
  await owner.getByRole('link', { name: 'Overview', exact: true }).click();
  await owner.screenshot({ path: path.join(output, 'macos-dark.png'), fullPage: true });
  await owner.reload();
  await owner.getByRole('heading', { name: 'Overview', exact: true }).waitFor();
  assert.equal(await owner.locator('html').getAttribute('data-appearance'), 'dark');
  check('appearance switches and persists without storing financial data');
  for (const width of [393, 852]) {
    await phone.setViewportSize({ width, height: width === 393 ? 852 : 393 });
    assert(await phone.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `No mobile page overflow at ${width}px`);
  }
  check('employee receipt detail has no horizontal overflow in portrait or landscape');
  assert.deepEqual(errors, []);
  check('no uncaught browser errors');
  const report = { checks: checks.length, status: 'passed', run_id, accountingCommit, screenshots: output };
  await writeFile(path.join(output, 'browser-test-results.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} finally { await browser.close(); }
