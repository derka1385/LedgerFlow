import { useEffect, useState } from "react";
import { correctRun, getRun, listRuns } from "../lib/api";
import { employeeStatus } from "../lib/experience";
import { localTime, money, parseMoney, stateTone } from "../lib/format";
import type { RunSnapshot } from "../lib/types";
import { usePolling } from "../lib/usePolling";
import { Callout, ErrorNote, Icon, Pill, Skeleton } from "../ui";

export function EmployeeHome() {
  const { data, error } = usePolling(listRuns);
  const questions = data?.items.filter(r => r.state === "NEEDS_REVIEW") ?? [];
  return <div className="stack-lg employee-home"><div className="employee-intro"><div className="spread"><h1>Expenses</h1><span className="receipt-count">{data ? `${data.items.length} submitted` : ""}</span></div><p className="muted">Capture a receipt. Follow it through to booking.</p></div>
    <a className="camera-launch" href="#/capture"><span className="camera-launch-icon"><Icon name="camera" /></span><span><strong>Scan a receipt</strong><span>Camera or photo library</span></span><Icon name="arrow" /></a>
    <ErrorNote error={error} />
    {questions.length ? <Callout tone="warn" title={`${questions.length} receipt(s) need a detail`}><a href="#/requests">Answer finance’s questions</a></Callout> : null}
    <div className="spread"><h2>Recent expenses</h2><a href="#/expenses">See all</a></div><ExpenseList items={data?.items.slice(0, 3)} />
  </div>;
}

function ExpenseList({ items }: { items?: Awaited<ReturnType<typeof listRuns>>["items"] }) {
  if (!items) return <Skeleton />;
  return items.length ? <div className="expense-list">{items.map(r => <a className="expense-row" key={r.run_id} href={`#/expenses/${r.run_id}`}><span className="expense-icon"><Icon name="file" /></span><span className="expense-copy"><strong>{r.merchant_name ?? "Receipt received"}</strong><span className="small">{r.document_date ?? localTime(r.created_at).slice(0, 10)}</span><Pill tone={stateTone(r.state)}>{employeeStatus(r.state)}</Pill></span><span className="expense-amount"><strong>{money(r.gross_minor)}</strong>{r.gross_minor != null ? <small>SEK</small> : null}</span></a>)}</div> : <div className="employee-empty"><Icon name="file" /><h3>No receipts submitted.</h3><p>Scan your first receipt above. Its status will stay available here.</p></div>;
}

export function ExpenseHistory({ questionsOnly = false }: { questionsOnly?: boolean }) {
  const { data, error } = usePolling(listRuns);
  return <div className="stack-lg"><div className="employee-page-heading"><h1>{questionsOnly ? "Requests from finance" : "Expense history"}</h1><p className="muted">{questionsOnly ? "The details finance needs from you." : "Every receipt, from submission to booking."}</p></div><ErrorNote error={error} /><ExpenseList items={data?.items.filter(r => !questionsOnly || r.state === "NEEDS_REVIEW")} /></div>;
}

export function ReceiptSummary({ run }: { run: RunSnapshot }) {
  const t = run.transaction;
  return <section className="receipt-summary stack"><div className="spread"><h2>{t?.merchant_name ?? "Receipt received"}</h2><Pill tone={stateTone(run.state)}>{employeeStatus(run.state)}</Pill></div>{t ? <dl className="kv"><dt>Date</dt><dd>{t.document_date ?? "Not read yet"}</dd><dt>Total</dt><dd className="mono">{money(t.gross_minor)} {t.currency ?? ""}</dd><dt>VAT</dt><dd className="mono">{money(t.tax_minor)} {t.currency ?? ""}</dd><dt>Payment</dt><dd>{t.payment_status === "unpaid" ? "Not paid yet" : ({ company_bank: "Company card / bank", company_cash: "Cash", employee_personal: "Paid personally", unknown: "Not identified" }[t.payment_source])}</dd></dl> : <p className="muted">We’re reading your receipt. You can leave this screen.</p>}</section>;
}

const EMPLOYEE_FIELDS: Record<string, string> = { merchant_name: "Merchant", supplier_reference: "Receipt number", supplier_org_no: "Merchant VAT / organisation number", document_date: "Receipt date", gross_minor: "Total (SEK)", net_minor: "Amount before VAT (SEK)", tax_minor: "VAT (SEK)" };
export function ExpenseDetail({ id }: { id: string }) {
  const { data: run, error, refresh } = usePolling(() => getRun(id));
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<unknown>(null);
  useEffect(() => { setValues({}); setSaveError(null); }, [id]);
  if (!run) return error ? <ErrorNote error={error} /> : <Skeleton />;
  const requested = [...new Set([...(run.review_items ?? []).map(i => i.field), ...(run.transaction?.unresolved_fields ?? [])])].filter((f): f is string => !!f && f in EMPLOYEE_FIELDS);
  async function save() {
    if (!run?.transaction || saving) return;
    setSaving(true); setSaveError(null);
    try {
      const corrections: Record<string, string | number> = {};
      for (const field of requested) {
        const value = values[field]?.trim(); if (!value) continue;
        if (field.endsWith("_minor")) { const minor = parseMoney(value); if (minor === null) throw new Error(`Enter an exact amount for ${EMPLOYEE_FIELDS[field]}.`); corrections[field] = minor; }
        else corrections[field] = value;
      }
      if (!Object.keys(corrections).length) throw new Error("Add a requested detail first.");
      await correctRun(id, { expected_run_revision: run.revision, expected_transaction_revision: run.transaction.revision, corrections, reason: "Employee supplied requested receipt details" });
      setValues({}); refresh();
    } catch (e) { setSaveError(e); } finally { setSaving(false); }
  }
  return <div className="stack-lg"><a href="#/expenses">Back to expenses</a><ReceiptSummary run={run} /><ErrorNote error={error} />
    {run.state === "NEEDS_REVIEW" ? <section className="panel stack"><h2>A little more information</h2>{(run.review_items ?? []).map((item, i) => <p key={i}>{item.message}</p>)}
      {requested.length ? <form className="stack" onSubmit={e => { e.preventDefault(); void save(); }}>{requested.map(field => <label key={field}>{EMPLOYEE_FIELDS[field]}<input type={field === "document_date" ? "date" : "text"} inputMode={field.endsWith("_minor") ? "decimal" : undefined} value={values[field] ?? ""} onChange={e => setValues(v => ({ ...v, [field]: e.target.value }))} /></label>)}<ErrorNote error={saveError} /><button className="btn primary" disabled={saving}>{saving ? "Sending…" : "Send details"}</button></form> : <p className="muted">Finance is reviewing this receipt. There are no receipt details you need to enter right now.</p>}
    </section> : null}
    {run.state === "REJECTED" || run.state === "FAILED" ? <Callout tone="warn" title={employeeStatus(run.state)}>{run.state_reason}. Contact finance if you need help.</Callout> : null}
    <p className="small">Submitted {localTime(run.created_at)} · Updated {localTime(run.updated_at)}</p></div>;
}
