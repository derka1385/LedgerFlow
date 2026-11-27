import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  approve, ApiError, artifactUrl, cancelRun, correctRun, fetchText, getDiff, getInspection, getRun, newIdempotencyKey, req,
  rerun, resolveDuplicate, subscribeRunEvents,
} from "../lib/api";
import { ACCOUNT_OPTIONS, approvalRequest, CHECK_LABEL, isTerminal, localTime, mergeEvents, money, parseMoney, shortHash } from "../lib/format";
import type { CellDiff, DiffResponse, ExecutionEvent, RunSnapshot, Session, Transaction } from "../lib/types";
import { Callout, ErrorNote, Icon, Pill, Skeleton, StatePill } from "../ui";
import { go } from "../App";
import { executionMetrics, safeDocumentUrl } from "../lib/experience";

const FIELD_LABEL: Record<string, string> = {
  merchant_name: "Supplier", supplier_reference: "Document no.", supplier_org_no: "Seller org/VAT no.", document_date: "Date",
  gross_minor: "Total", net_minor: "Net", tax_minor: "VAT", payment_status: "Payment status", payment_source: "Paid from",
  category_account_id: "Expense account", tax_treatment: "VAT treatment", kind: "Document type",
};
const PAYMENT: [string, string, Transaction["payment_status"], Transaction["payment_source"]][] = [
  ["card", "Company card / bank", "paid", "company_bank"], ["cash", "Cash", "paid", "company_cash"],
  ["private", "Paid privately", "paid", "employee_personal"], ["unpaid", "Not paid yet", "unpaid", "unknown"],
];

export default function Review({ runId, session, activityOnly = false }: { runId: string; session: Session; activityOnly?: boolean }) {
  const [run, setRun] = useState<RunSnapshot | null>(null);
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [diff, setDiff] = useState<DiffResponse | null>(null);
  const [names, setNames] = useState<Record<string, string>>({});
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [captureOrigin, setCaptureOrigin] = useState<string | null>(null);
  const [originalUrl, setOriginalUrl] = useState<string | null>(null);
  const [monitor, setMonitor] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [stream, setStream] = useState<"open" | "reconnecting">("open");
  const finance = session.role !== "employee";

  const refresh = () => getRun(runId).then(setRun).catch(setError);
  useEffect(() => { refresh(); }, [runId]);
  useEffect(() => {
    const close = subscribeRunEvents(runId, 0, (e) => {
      setEvents((p) => mergeEvents(p, [e]));
      if (["run.state_changed", "commit.completed", "validation.completed"].includes(e.event_type)) refresh();
    }, setStream);
    return close;
  }, [runId]);
  useEffect(() => { // snapshot is authoritative; poll as a safety net while work is in flight
    if (!run || isTerminal(run.state)) return;
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [run?.state]);
  useEffect(() => {
    if (!run) return;
    req<{ image_url: string; original_url?: string; capture_origin?: string }>("GET", `/documents/${run.document_id}`).then(d => { setImageUrl(safeDocumentUrl(d.image_url)); setOriginalUrl(d.original_url ? safeDocumentUrl(d.original_url) : null); setCaptureOrigin(d.capture_origin ?? null); }).catch(() => undefined);
    if (finance) getInspection(run.workbook_id).then((i) => setNames(Object.fromEntries((i.accounts ?? []).map((a: any) => [a.account_id, a.name])))).catch(() => undefined);
  }, [run?.document_id]);
  useEffect(() => {
    if (run?.validation_summary) getDiff(runId).then(setDiff).catch(() => setDiff(null));
    else setDiff(null);
  }, [run?.validation_summary?.report_sha256]);

  if (!run) return error ? <ErrorNote error={error} /> : <Skeleton lines={6} />;
  const t = run.transaction;
  const busy = !isTerminal(run.state) && !["AWAITING_APPROVAL", "NEEDS_REVIEW", "DUPLICATE_REVIEW"].includes(run.state);

  if (activityOnly) return <div className="stack"><ErrorNote error={error} /><Monitor run={run} events={events} stream={stream} onClose={() => go(`transactions/${run.run_id}`)} inline /></div>;

  return (
    <div className="stack-lg">
      <div className="spread">
        <div className="stack" style={{ gap: 4 }}>
          <a href="#/inbox" className="small" style={{ textDecoration: "none", display: "inline-flex", gap: 5, alignItems: "center" }}><span style={{ display: "inline-flex", transform: "scaleX(-1)" }}><Icon name="arrow" /></span>Inbox</a>
          <h1>{t?.merchant_name ?? "Document"} {t?.gross_minor != null ? <span className="muted mono" style={{ fontWeight: 400 }}>· SEK {money(t.gross_minor)}</span> : null}</h1>
          <div className="row small">
            <span className="mono">{run.run_id}</span>
            <span>·</span><span>{t?.kind === "supplier_invoice" ? "Supplier invoice" : "Receipt"}</span>
            {t?.document_date ? <><span>·</span><span className="mono">{t.document_date}</span></> : null}
          </div>
        </div>
        <div className="row">
          <StatePill state={run.state} />
          <button className="btn" onClick={() => setMonitor(true)}><Icon name="terminal" />Execution monitor
            {busy ? <span className="dot-busy" aria-hidden style={{ color: "var(--busy)" }} /> : null}</button>
        </div>
      </div>

      {run.mock_labels?.length ? (
        <p className="small"><Icon name="alert" /> Mocked steps in this run: {run.mock_labels.join(" · ")}. Everything else is real.</p>
      ) : null}
      <ErrorNote error={error} />
      <StateCallouts run={run} finance={finance} onChange={refresh} />

      <div className="review">
        <Evidence run={run} imageUrl={imageUrl} originalUrl={originalUrl} captureOrigin={captureOrigin} />
        <div className="stack review-proposal">
          <EntryPanel run={run} names={names} />
          {run.state === "NEEDS_REVIEW" && finance ? <Corrections run={run} onDone={refresh} /> : null}
          <Changes run={run} diff={diff} names={names} />
        </div>
      </div>

      {finance && run.state === "AWAITING_APPROVAL" && diff ? <ApprovalBar run={run} diff={diff} onDone={refresh} /> : null}
      {run.commit ? <CommittedBar run={run} /> : null}
      {monitor ? <Monitor run={run} events={events} stream={stream} onClose={() => setMonitor(false)} /> : null}
    </div>
  );
}

function StateCallouts({ run, finance, onChange }: { run: RunSnapshot; finance: boolean; onChange: () => void }) {
  const [error, setError] = useState<unknown>(null);
  const act = async (fn: () => Promise<unknown>) => { setError(null); try { await fn(); onChange(); } catch (e) { setError(e); } };
  const items = run.review_items ?? [];
  return (
    <>
      {run.state === "NEEDS_REVIEW" && run.state_reason === "SECURITY_REVIEW" ? (
        <Callout tone="warn" title="This document contains text addressed to an AI system." icon="shield">
          <p>It was treated as plain document content. Nothing it asked for was done (no account change, no command). Check the amounts against the image, then continue or reject.</p>
          {finance ? <div className="row">
            <button className="btn" onClick={() => act(() => correctRun(run.run_id, { expected_run_revision: run.revision, expected_transaction_revision: run.transaction?.revision,
              corrections: { acknowledge_security_flag: true }, reason: "Security flag reviewed; amounts checked against the image" }))}>
              <Icon name="check" />Continue with the extracted amounts</button>
            <button className="btn danger" onClick={() => act(() => cancelRun(run.run_id, run.revision))}><Icon name="x" />Reject document</button>
          </div> : null}
        </Callout>
      ) : null}
      {run.state === "NEEDS_REVIEW" && run.state_reason !== "SECURITY_REVIEW" ? (
        <Callout tone="warn" title={items[0]?.message ?? "Needs a human answer before anything is written."}>
          {items.length ? <ul style={{ margin: 0, paddingLeft: 18 }}>{items.map((i, n) => <li key={n}>{i.detail} <span className="small mono">{i.code}</span></li>)}</ul>
            : <p>{run.state_reason}</p>}
          <p className="small">Nothing has been written to the workbook.</p>
        </Callout>
      ) : null}
      {run.state === "DUPLICATE_REVIEW" ? (
        <Callout tone="warn" title="Possible duplicate.">
          <p>Looks like the same purchase as <a href={`#/runs/${run.duplicate_of}`}>{run.duplicate_of}</a>, which is already booked or still in progress: same file, or same supplier, total and document number (or date, when no number is printed).</p>
          {finance ? <div className="row">
            <button className="btn" onClick={() => act(() => resolveDuplicate(run.run_id, { expected_run_revision: run.revision, decision: "same_transaction", reason: "Duplicate" }))}>It's a duplicate: discard</button>
            <button className="btn" onClick={() => act(() => resolveDuplicate(run.run_id, { expected_run_revision: run.revision, decision: "distinct_transaction", reason: "Different purchase" }))}>Different purchase: continue</button>
          </div> : null}
        </Callout>
      ) : null}
      {run.state === "STALE_BASE" ? (
        <Callout tone="warn" title="The workbook changed after this preview.">
          <p>Another entry was committed first, so this preview no longer matches the current file. Re-run it on the current version and approve the new result.</p>
          {finance ? <div><button className="btn primary" onClick={() => act(async () => { const r = await rerun(run.run_id); go(`runs/${r.run_id}`); })}>
            <Icon name="refresh" />Re-run on the current version</button></div> : null}
        </Callout>
      ) : null}
      {run.state === "FAILED" ? <Callout tone="bad" title="Nothing was written to your workbook."><p>{run.state_reason}. Open the execution monitor for the run log.</p></Callout> : null}
      {run.state === "REJECTED" ? <Callout tone="bad" title="Rejected.">The workbook was not changed.</Callout> : null}
      {(run.advisories ?? []).map((a) => <Callout key={a} tone="info">{a}</Callout>)}
      <ErrorNote error={error} />
    </>
  );
}

function Evidence({ run, imageUrl, originalUrl, captureOrigin }: { run: RunSnapshot; imageUrl: string | null; originalUrl: string | null; captureOrigin: string | null }) {
  const t = run.transaction;
  const quote = (field: string) => [...(t?.evidence ?? [])].reverse().find((e) => e.field === field); // latest source wins
  const rows: [string, string | null][] = t ? [
    ["merchant_name", t.merchant_name], ["supplier_org_no", t.supplier_org_no ?? null], ["supplier_reference", t.supplier_reference],
    ["document_date", t.document_date], ["gross_minor", t.gross_minor != null ? `SEK ${money(t.gross_minor)}` : null],
    ["net_minor", t.net_minor != null ? `SEK ${money(t.net_minor)}` : null],
    ["tax_minor", t.tax_minor != null ? `SEK ${money(t.tax_minor)}${t.tax_lines[0]?.rate_basis_points != null ? ` (${t.tax_lines[0].rate_basis_points / 100} %)` : ""}` : null],
    ["payment_status", t.payment_status === "unknown" ? null : `${t.payment_status}${t.payment_source !== "unknown" ? ` · ${t.payment_source.replace("_", " ")}` : ""}`],
    ["category_account_id", t.category_account_id], ["tax_treatment", t.tax_treatment === "unknown" ? null : t.tax_treatment.replace("configured_", "")],
  ] : [];
  return (
    <section className="panel stack" aria-labelledby="ev-h">
      <h2 id="ev-h">Document</h2>
      {captureOrigin ? <p className="small">Uploaded from {captureOrigin}</p> : null}
      {originalUrl ? <a className="btn" href={originalUrl}><Icon name="download"/>Download original PDF</a> : null}
      {imageUrl ? <img className="receipt" src={imageUrl} alt={t ? `Receipt from ${t.merchant_name ?? "unknown supplier"}, total ${money(t.gross_minor)} SEK` : "Uploaded document"} />
        : <Skeleton lines={6} />}
      <h3>What we read</h3>
      {!t ? <Skeleton /> : (
        <div className="facts">
          {rows.map(([f, v]) => {
            const q = quote(f);
            return (
              <div key={f} className={`fact ${v === null ? "unknown" : ""}`}>
                <span className="muted">{FIELD_LABEL[f]}</span>
                <span className="v">{v ?? "Unknown: not on the document"}
                  {q?.text ? <span className="q">{q.source === "human_confirmation" ? <><Icon name="user" /> {q.text}</> : <>“{q.text}”</>}</span> : null}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function EntryPanel({ run, names }: { run: RunSnapshot; names: Record<string, string> }) {
  const e = run.entry;
  if (!e) {
    return <section className="panel stack"><h2>Proposed entry</h2>
      {isTerminal(run.state) || run.state === "NEEDS_REVIEW" ? <p className="muted">No entry: the facts are not complete yet.</p> : <Skeleton />}</section>;
  }
  const deb = e.lines.filter((l) => l.side === "debit").reduce((s, l) => s + l.amount_minor, 0);
  const cre = e.lines.filter((l) => l.side === "credit").reduce((s, l) => s + l.amount_minor, 0);
  return (
    <section className="panel stack" aria-labelledby="en-h">
      <div className="spread"><h2 id="en-h">Proposed entry</h2><span className="small mono">{e.accounting_date}</span></div>
      <div className="table-wrap" style={{ border: 0 }}>
        <table>
          <thead><tr><th>Account</th><th style={{ textAlign: "right" }}>Debit</th><th style={{ textAlign: "right" }}>Credit</th></tr></thead>
          <tbody>
            {e.lines.map((l) => (
              <tr key={l.line_id}>
                <td><span className="mono">{l.account_id}</span> {names[l.account_id] ?? ""}</td>
                <td className="num">{l.side === "debit" ? money(l.amount_minor) : ""}</td>
                <td className="num">{l.side === "credit" ? money(l.amount_minor) : ""}</td>
              </tr>
            ))}
          </tbody>
          <tfoot><tr><td>{deb === cre ? <Pill tone="ok">balanced</Pill> : <Pill tone="bad">unbalanced</Pill>}</td>
            <td className="num">{money(deb)}</td><td className="num">{money(cre)}</td></tr></tfoot>
        </table>
      </div>
      <p><strong>Why: </strong>{e.explanation}</p>
      <p className="small">Built by deterministic rules from the confirmed facts (policy <code>{e.policy_version}</code>). The model never writes debits or credits.</p>
    </section>
  );
}

function Corrections({ run, onDone }: { run: RunSnapshot; onDone: () => void }) {
  const t = run.transaction!;
  const [f, setF] = useState(() => ({
    merchant_name: t.merchant_name ?? "", supplier_org_no: t.supplier_org_no ?? "", supplier_reference: t.supplier_reference ?? "",
    document_date: t.document_date ?? "", gross: t.gross_minor != null ? money(t.gross_minor) : "", net: t.net_minor != null ? money(t.net_minor) : "",
    tax: t.tax_minor != null ? money(t.tax_minor) : "", rate: String(t.tax_lines[0]?.rate_basis_points ?? 2500),
    payment: PAYMENT.find((p) => p[2] === t.payment_status && (p[3] === t.payment_source || p[2] === "unpaid"))?.[0] ?? "",
    category: t.category_account_id ?? "", treatment: t.tax_treatment === "unknown" ? "configured_deductible" : t.tax_treatment,
    kind: t.kind,
  }));
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  if (run.state_reason === "SECURITY_REVIEW") return null;
  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));
  const submit = async () => {
    setError(null);
    const gross = parseMoney(f.gross), net = f.net ? parseMoney(f.net) : null, tax = f.tax ? parseMoney(f.tax) : null;
    if (gross === null || (f.net && net === null) || (f.tax && tax === null)) {
      setError(new ApiError(400, "AMOUNT_FORMAT", "Enter amounts like 1 250,00. Use a decimal part when a number could mean thousands (1 250,00 not 1,250)."));
      return;
    }
    const pay = PAYMENT.find((p) => p[0] === f.payment);
    const proposed: Record<string, unknown> = {
      merchant_name: f.merchant_name || null, supplier_org_no: f.supplier_org_no || null, supplier_reference: f.supplier_reference || null,
      document_date: f.document_date || null, gross_minor: gross, net_minor: net, tax_minor: tax,
      category_account_id: f.category || null, tax_treatment: f.treatment, kind: f.kind,
      ...(pay ? { payment_status: pay[2], payment_source: pay[3] } : {}),
    };
    // Send only what the reviewer changed: unchanged fields keep their document evidence (audit provenance).
    const corrections: Record<string, unknown> = Object.fromEntries(
      Object.entries(proposed).filter(([k, v]) => (t as unknown as Record<string, unknown>)[k] !== v));
    if (Number(f.rate) !== (t.tax_lines[0]?.rate_basis_points ?? null)) corrections.tax_rate_basis_points = Number(f.rate);
    if (!Object.keys(corrections).length) { setError(new ApiError(400, "NO_CHANGES", "Nothing changed. Answer the open question first.")); return; }
    setBusy(true);
    try {
      await correctRun(run.run_id, { expected_run_revision: run.revision, expected_transaction_revision: t.revision, corrections, reason: "Reviewed against the document image" });
      onDone();
    } catch (e) { setError(e); } finally { setBusy(false); }
  };
  return (
    <section className="panel stack" aria-labelledby="co-h">
      <h2 id="co-h">Answer and continue</h2>
      <p className="small">Values you enter are recorded as human confirmations, separate from what was read on the document.</p>
      <div className="segmented" role="group" aria-label="How was this paid?">
        {PAYMENT.map(([k, label]) => <button key={k} type="button" aria-pressed={f.payment === k} onClick={() => set("payment", k)}>{label}</button>)}
      </div>
      <div className="grid2" style={{ gap: 10 }}>
        <label>Supplier<input value={f.merchant_name} onChange={(e) => set("merchant_name", e.target.value)} /></label>
        <label>Seller org/VAT no.<input value={f.supplier_org_no} onChange={(e) => set("supplier_org_no", e.target.value)} placeholder="559999-0101" /></label>
        <label>Document no.<input value={f.supplier_reference} onChange={(e) => set("supplier_reference", e.target.value)} /></label>
        <label>Date<input type="date" value={f.document_date} onChange={(e) => set("document_date", e.target.value)} /></label>
        <label>Total (SEK)<input inputMode="decimal" value={f.gross} onChange={(e) => set("gross", e.target.value)} placeholder="1 250,00" /></label>
        <label>Net (SEK)<input inputMode="decimal" value={f.net} onChange={(e) => set("net", e.target.value)} /></label>
        <label>VAT (SEK)<input inputMode="decimal" value={f.tax} onChange={(e) => set("tax", e.target.value)} /></label>
        <label>VAT rate<select value={f.rate} onChange={(e) => set("rate", e.target.value)}>
          <option value="2500">25 %</option><option value="1200">12 %</option><option value="600">6 %</option></select></label>
        <label>Expense account<select value={f.category} onChange={(e) => set("category", e.target.value)}>
          <option value="">Choose…</option>{ACCOUNT_OPTIONS.map(([c, n]) => <option key={c} value={c}>{c} {n}</option>)}</select></label>
        <label>VAT treatment<select value={f.treatment} onChange={(e) => set("treatment", e.target.value)}>
          <option value="configured_deductible">Deductible</option><option value="configured_nondeductible">Not deductible</option>
          <option value="tax_free">No VAT</option></select></label>
        <label>Document type<select value={f.kind} onChange={(e) => set("kind", e.target.value)}>
          <option value="purchase_receipt">Receipt</option><option value="supplier_invoice">Supplier invoice</option></select></label>
      </div>
      <ErrorNote error={error} />
      <div className="row">
        <button className="btn primary" onClick={submit} disabled={busy}><Icon name="check" />{busy ? "Saving…" : "Save answers and re-run"}</button>
        <button className="btn danger" onClick={() => cancelRun(run.run_id, run.revision).then(onDone).catch(setError)}>Reject document</button>
      </div>
    </section>
  );
}

function colNum(c: string) { return [...c].reduce((n, ch) => n * 26 + ch.charCodeAt(0) - 64, 0); }
function colName(n: number) { let s = ""; while (n) { const r = (n - 1) % 26; s = String.fromCharCode(65 + r) + s; n = Math.floor((n - 1) / 26); } return s; }
const split = (ref: string) => { const m = /^([A-Z]+)(\d+)$/.exec(ref)!; return [m[1], Number(m[2])] as const; };
const show = (c: CellDiff["after"]) => (c.type === "blank" ? "" : String(c.value ?? ""));

/** The Ledger Grid's one device on the real diff: one range rectangle with a fill handle around the changed cells. */
function SelectedRange({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState<{ l: number; t: number; w: number; h: number } | null>(null);
  useLayoutEffect(() => {
    const host = ref.current;
    if (!host) return;
    const measure = () => {
      const cells = [...host.querySelectorAll("td.new")].map(c => c.getBoundingClientRect());
      if (!cells.length) { setBox(null); return; }
      const hr = host.getBoundingClientRect();
      const l = Math.min(...cells.map(r => r.left)), t = Math.min(...cells.map(r => r.top));
      const r = Math.max(...cells.map(c => c.right)), b = Math.max(...cells.map(c => c.bottom));
      setBox({ l: l - hr.left + host.scrollLeft, t: t - hr.top, w: r - l, h: b - t });
    };
    measure();
    const ro = new ResizeObserver(measure); ro.observe(host);
    return () => ro.disconnect();
  }, []);
  return <div ref={ref} className="range-host">{children}{box ? <span className="selection-frame range" style={{ left: box.l, top: box.t, width: box.w, height: box.h }}><i /></span> : null}</div>;
}

function DiffGrid({ diffs, names }: { diffs: CellDiff[]; names: Record<string, string> }) {
  const groups = useMemo(() => {
    const by: Record<string, CellDiff[]> = {};
    diffs.forEach((d) => { (by[d.account_id ?? "?"] ??= []).push(d); });
    return Object.entries(by).map(([acc, ds]) => {
      const ref = ds.find((d) => d.reason.endsWith("reference"))!;
      const c = colNum(split(ref.cell)[0]) - (ref.side === "credit" ? 2 : 0);
      const rows = [...new Set(ds.map((d) => split(d.cell)[1]))].sort((a, b) => a - b);
      const at = Object.fromEntries(ds.map((d) => [d.cell, d]));
      return { acc, c, rows, at };
    });
  }, [diffs]);
  return (
    <div className="stack">
      {groups.map(({ acc, c, rows, at }) => (
        <SelectedRange key={acc}>
          <table className="sheetgrid" aria-label={`Changes in T-account ${acc}`}>
            <caption>{acc} {names[acc] ?? ""} <span className="small" style={{ fontWeight: 400 }}>· debit | credit</span></caption>
            <thead><tr><th></th>{[0, 1, 2, 3].map((i) => <th key={i} scope="col">{colName(c + i)}</th>)}</tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r}>
                  <th scope="row">{r}</th>
                  {[0, 1, 2, 3].map((i) => {
                    const ref = `${colName(c + i)}${r}`;
                    const d = at[ref];
                    return <td key={i} className={`${i % 2 === 0 ? "ref" : ""} ${d ? "new" : ""}`}
                               aria-label={d ? `${ref}, new value ${show(d.after)}, ${d.reason.replace("_", " ")} for ${acc}` : undefined}>
                      {d ? (d.reason.endsWith("amount") ? money(d.amount_delta_minor) : show(d.after)) : ""}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </SelectedRange>
      ))}
    </div>
  );
}

function Changes({ run, diff, names }: { run: RunSnapshot; diff: DiffResponse | null; names: Record<string, string> }) {
  const [showAll, setShowAll] = useState(false);
  if (!diff) {
    return <section className="panel stack"><h2>Changes to your workbook</h2>
      {isTerminal(run.state) || run.state === "NEEDS_REVIEW" || run.state === "DUPLICATE_REVIEW" ? <p className="muted">No candidate file.</p> : <><Skeleton lines={5} />
        <p className="small">The diff appears after the sandbox run and the independent verification.</p></>}</section>;
  }
  const v = diff.validation;
  const st = (id: string) => v.checks.find((c) => c.check_id === id)?.status;
  const passed = v.checks.filter((c) => c.status === "pass").length;
  const tbD = v.account_deltas.reduce((s, a) => s + a.debit_minor, 0);
  const tbC = v.account_deltas.reduce((s, a) => s + a.credit_minor, 0);
  const featureDetail = v.checks.find((c) => c.check_id === "features_preserved")?.detail ?? "";
  const ranges = /\((\d+) ranges\)/.exec(featureDetail)?.[1];
  return (
    <section className="panel stack" aria-labelledby="ch-h">
      <div className="spread"><h2 id="ch-h">Changes to your workbook</h2>
        <Pill tone={v.result === "pass" ? "ok" : v.result === "fail" ? "bad" : "warn"}>{passed}/{v.checks.length} checks</Pill></div>
      <DiffGrid diffs={v.cell_diff} names={names} />
      <details>
        <summary className="small" style={{ cursor: "pointer" }}>Change list ({v.cell_diff.length} cells)</summary>
        <ul className="checklist mono" style={{ marginTop: 8, fontSize: 12 }}>
          {v.cell_diff.map((d) => <li key={d.cell}><span className="ok"><Icon name="check" /></span>
            <span>{d.sheet}!{d.cell}  (empty) → {show(d.after)}  <span className="muted">{d.reason.replace("_", " ")}</span></span></li>)}
        </ul>
      </details>
      <div className="stack" style={{ gap: 6, fontSize: 13 }}>
        <div className="row"><Icon name="grid" /><strong>{v.cell_diff.length} cells changed</strong><span className="muted">· {st("non_target_cells_unchanged") === "pass" ? "0 other changes" : "OTHER CELLS CHANGED"}</span></div>
        <div className="row" style={{ flexWrap: "nowrap", alignItems: "flex-start" }}><Icon name="file" /><span>{st("features_preserved") === "pass" ? "Every other file part byte-identical" : "File parts changed"}{ranges ? ` · dropdowns ${ranges}/${ranges} kept` : ""} · formulas {st("formulas_unchanged") === "pass" ? "untouched" : "CHANGED"}</span></div>
        <div className="row" style={{ flexWrap: "nowrap", alignItems: "flex-start" }}><Icon name="checkCircle" /><span>Trial balance <span className="mono">+{money(tbD)} / +{money(tbC)}</span>
          {v.baseline && v.baseline.difference_minor !== 0 ? <span className="muted"> · pre-existing difference {money(v.baseline.difference_minor)} unchanged</span> : null}</span></div>
        <div className="small">Verified by <code>{v.verifier_version}</code> (no AI) on the actual output file{v.runtime ? <> · sandbox <code>{v.runtime}</code></> : null}.</div>
      </div>
      <button className="btn ghost" style={{ justifySelf: "start" }} onClick={() => setShowAll((s) => !s)}>{showAll ? "Hide" : "Show"} all checks</button>
      {showAll ? (
        <ul className="checklist">
          {v.checks.map((c) => (
            <li key={c.check_id}>
              <span className={c.status === "pass" ? "ok" : c.status === "fail" ? "bad" : "warn"}><Icon name={c.status === "pass" ? "check" : c.status === "fail" ? "x" : "alert"} /></span>
              <span><strong>{CHECK_LABEL[c.check_id] ?? c.check_id}</strong> <span className="small mono">{c.check_id}</span><br /><span className="small">{c.detail}</span></span>
            </li>
          ))}
        </ul>
      ) : null}
      {v.limitations.map((l) => <p key={l} className="small">Limitation: {l}</p>)}
    </section>
  );
}

function ApprovalBar({ run, diff, onDone }: { run: RunSnapshot; diff: DiffResponse; onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("Wrong account");
  const key = useRef(newIdempotencyKey("apr")); // same key on retry: a lost response returns the existing commit
  const n = diff.validation.cell_diff.length;
  const decide = async (decision: "approve" | "reject") => {
    setBusy(true);
    setError(null);
    try { await approve(run.run_id, approvalRequest(diff, decision, decision === "reject" ? reason : undefined), key.current); onDone(); }
    catch (e) { setError(e); if (e instanceof ApiError && e.code === "STALE_BASE") onDone(); }
    finally { setBusy(false); }
  };
  return (
    <div className="approvalbar" role="region" aria-label="Approval">
      <div className="inner">
        <div className="row small" title={`base ${diff.base_sha256}\ncandidate ${diff.candidate_sha256}`}>
          <Icon name="lock" />Approval is tied to this exact file: base <span className="hashchip">{shortHash(diff.base_sha256)}</span> → result <span className="hashchip">{shortHash(diff.candidate_sha256)}</span>
        </div>
        <div className="row">
          {rejecting ? (
            <>
              <select aria-label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} style={{ width: "auto" }}>
                {["Wrong account", "Wrong amount", "Not a business expense", "Duplicate", "Other"].map((r) => <option key={r}>{r}</option>)}
              </select>
              <button className="btn danger" disabled={busy} onClick={() => decide("reject")}>Confirm reject</button>
              <button className="btn ghost" onClick={() => setRejecting(false)}>Cancel</button>
            </>
          ) : <button className="btn" disabled={busy} onClick={() => setRejecting(true)}>Reject…</button>}
          <button className="btn primary" disabled={busy || diff.validation.result !== "pass"} onClick={() => decide("approve")}>
            <Icon name="check" />{busy ? "Writing…" : `Approve and write ${n} cells`}</button>
        </div>
        {error ? <div style={{ flexBasis: "100%" }}><ErrorNote error={error} /></div> : null}
      </div>
    </div>
  );
}

function CommittedBar({ run }: { run: RunSnapshot }) {
  const c = run.commit!;
  return (
    <div className="approvalbar" role="region" aria-label="Committed">
      <div className="inner">
        <div className="row"><Pill tone="ok">Committed</Pill><span className="small">New version <span className="hashchip">{shortHash(c.artifact_sha256)}</span> · {localTime(c.committed_at)}</span></div>
        <div className="row">
          {c.audit_artifact_id ? <a className="btn" href={artifactUrl(c.audit_artifact_id)} download><Icon name="file" />Audit log</a> : null}
          {c.artifact_id ? <a className="btn primary" href={artifactUrl(c.artifact_id)} download><Icon name="download" />Download .xlsx</a>
            : <a className="btn primary" href={`#/versions/${run.workbook_id}`}><Icon name="download" />Download from Versions</a>}
        </div>
      </div>
    </div>
  );
}

const EVENT_ICON: Record<string, string> = {
  "sandbox.created": "box", "sandbox.started": "play", "sandbox.exited": "terminal", "sandbox.destroyed": "trash", "code.generated": "code",
  "validation.completed": "checkCircle", "commit.completed": "lock", "review.required": "alert", "run.failed": "xOctagon", "retry.scheduled": "refresh",
};

function Monitor({ run, events, stream, onClose, inline = false }: { run: RunSnapshot; events: ExecutionEvent[]; stream: string; onClose: () => void; inline?: boolean }) {
  const [code, setCode] = useState<string | null>(null);
  const [codeError, setCodeError] = useState<unknown>(null);
  const metrics = executionMetrics(events);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const attempts = [...new Set(events.map((e) => e.attempt_id).filter(Boolean))] as string[];
  const plan = events.find((e) => e.event_type === "plan.admitted");
  return (
    <aside className={inline ? "execution-panel" : "drawer"} aria-label="Execution monitor">
      <header>
        <div className="stack" style={{ gap: 2 }}>
          <h2>Execution monitor</h2>
          <span className="small mono">{run.run_id} · {attempts.length} attempt(s) · stream {stream}</span>
        </div>
        <button className="btn ghost" onClick={onClose} aria-label="Close monitor"><Icon name="x" /></button>
      </header>
      <div className="body stack">
        <div className="execution-metrics"><div><span className="small">Measured sandbox time</span><strong className="mono">{metrics.durationMs === null ? "Not reported" : `${(metrics.durationMs / 1000).toFixed(2)} s`}</strong></div><div><span className="small">Reported inference tokens</span><strong className="mono">{metrics.tokens === null ? "Not reported" : metrics.tokens.toLocaleString()}</strong></div></div>
        <p className="small">Every line below is an event from the backend. Nothing is simulated in the browser.</p>
        {run.mock_labels?.length ? <Callout tone="warn">Mocked steps reported by backend: {run.mock_labels.join(" · ")}</Callout> : null}
        <ErrorNote error={codeError} />
        {plan ? <Callout tone="info" icon="flag" title="Plan">
          <p>Inspect workbook → locate free rows → write {String(plan.data.operations)} cells → self-check → export. Plan <code>{shortHash(String(plan.data.plan_sha256))}</code></p>
        </Callout> : null}
        <ol className="timeline" aria-live="polite">
          {events.filter((e) => e.event_type !== "sandbox.log").map((e) => (
            <li key={e.sequence}>
              <span className="t">{localTime(e.occurred_at, true)}</span>
              <span><Icon name={EVENT_ICON[e.event_type] ?? "clock"} /></span>
              <span>
                <span>{e.message}</span> <span className="k">{e.event_type}{e.attempt_id ? ` · ${e.attempt_id.split("_").pop()}` : ""}</span>
                {e.event_type === "sandbox.created" && e.data.limits ? (
                  <span className="small mono" style={{ display: "block" }}>{(() => { const l = e.data.limits as any; return `${e.data.runtime} · ${l.cpus} CPU · ${l.memory_mb} MB · ${l.timeout_s} s · ${l.pids} pids · network ${l.network}`; })()}</span>) : null}
                {e.event_type === "sandbox.created" && !e.data.limits ? <span className="small" style={{ display: "block", color: "var(--bad)" }}>Runtime {String(e.data.runtime)}: no isolation.</span> : null}
                {e.event_type === "sandbox.exited" ? <span className="small mono" style={{ display: "block" }}>exit {String(e.data.exit_code)} · {String(e.data.termination_reason)} · {String(e.data.duration_ms)} ms · peak memory {e.data.peak_memory_bytes == null ? "not reported" : String(e.data.peak_memory_bytes)}</span> : null}
                {e.event_type === "code.generated" ? <button className="btn ghost" style={{ minHeight: 28, padding: "4px 6px" }}
                  onClick={() => { setCodeError(null); fetchText(String(e.data.code_artifact_id)).then(setCode).catch(setCodeError); }}><Icon name="code" />View code ({String(e.data.bytes)} bytes, {String(e.data.model_id)})</button> : null}
              </span>
            </li>
          ))}
        </ol>
        {attempts.map((a) => {
          const logs = events.filter((e) => e.event_type === "sandbox.log" && e.attempt_id === a);
          const out = logs.filter((l) => l.data.stream === "stdout").map((l) => String(l.data.text)).join("");
          const err = logs.filter((l) => l.data.stream === "stderr").map((l) => String(l.data.text)).join("");
          return (
            <div key={a} className="stack" style={{ gap: 4 }}>
              <h3>Attempt {a.split("_").pop()}: program output</h3>
              {out ? <pre className="log">{out}</pre> : <p className="small">No stdout.</p>}
              {err ? <pre className="log err">{err}</pre> : null}
            </div>
          );
        })}
        {code !== null ? (
          <div className="stack" style={{ gap: 4 }}>
            <div className="spread"><h3>Generated program</h3><button className="btn ghost" onClick={() => setCode(null)}>Hide</button></div>
            <pre className="log" style={{ maxHeight: 420 }}>{code}</pre>
          </div>
        ) : null}
      </div>
    </aside>
  );
}
