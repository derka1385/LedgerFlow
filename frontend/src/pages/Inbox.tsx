import { useEffect, useState } from "react";
import { listRuns } from "../lib/api";
import { money } from "../lib/format";
import type { RunListItem, RunState } from "../lib/types";
import { ErrorNote, Icon, Skeleton, StatePill } from "../ui";
import { go } from "../App";

const TABS: [string, string, RunState[] | null][] = [
  ["approve", "Ready to approve", ["AWAITING_APPROVAL"]],
  ["review", "Needs your answer", ["NEEDS_REVIEW", "DUPLICATE_REVIEW", "STALE_BASE"]],
  ["working", "In progress", ["QUEUED", "EXTRACTING", "PLANNING", "GENERATING_CODE", "SANDBOX_STARTING", "EXECUTING", "VERIFYING", "RETRY_PENDING", "CLEANUP_PENDING", "COMMITTING"]],
  ["done", "Done", ["COMMITTED", "REJECTED", "FAILED", "CANCELLED", "EXPIRED"]],
];
const KIND: Record<string, string> = { purchase_receipt: "Receipt", supplier_invoice: "Supplier invoice" };

function age(iso: string) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  return s < 60 ? "just now" : s < 3600 ? `${Math.floor(s / 60)} min` : `${Math.floor(s / 3600)} h`;
}

export default function Inbox() {
  const [runs, setRuns] = useState<RunListItem[] | null>(null);
  const [tab, setTab] = useState("approve");
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    const load = () => listRuns().then((r) => { setRuns(r.items); setError(null); }).catch(setError);
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);
  if (!runs) return error ? <ErrorNote error={error} /> : <Skeleton lines={5} />;
  const count = (states: RunState[] | null) => runs.filter((r) => !states || states.includes(r.state)).length;
  const current = TABS.find((t) => t[0] === tab)!;
  const rows = runs.filter((r) => !current[2] || current[2].includes(r.state));
  return (
    <div className="stack-lg">
      <div className="spread">
        <h1>Inbox</h1>
        <a className="btn" href="#/capture"><Icon name="camera" />Submit a receipt</a>
      </div>
      <ErrorNote error={error} />
      <div className="tabs" role="tablist">
        {TABS.map(([id, label, states]) => (
          <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}>{label} ({count(states)})</button>
        ))}
      </div>
      {rows.length ? (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Supplier</th><th>Type</th><th>Doc date</th><th style={{ textAlign: "right" }}>Total (SEK)</th><th>Checks</th><th>Status</th><th>Age</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.run_id} className="link" tabIndex={0} onClick={() => go(`runs/${r.run_id}`)}
                    onKeyDown={(e) => { if (e.key === "Enter") go(`runs/${r.run_id}`); }}>
                  <td>{r.merchant_name ?? <span className="muted">Not read yet</span>}<div className="small mono">{r.run_id}</div></td>
                  <td>{r.kind ? KIND[r.kind] ?? r.kind : "—"}</td>
                  <td className="mono">{r.document_date ?? "—"}</td>
                  <td className="num">{money(r.gross_minor)}</td>
                  <td className="mono">{r.validation_summary ? `${r.validation_summary.checks_passed}/${r.validation_summary.checks_total}` : "—"}</td>
                  <td><StatePill state={r.state} /></td>
                  <td className="muted">{age(r.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="panel empty">
          <Icon name="file" />
          <p>{tab === "approve" ? "Nothing waiting for approval." : tab === "review" ? "No questions open." : tab === "working" ? "Nothing running." : "No finished items yet."}</p>
          <p className="small">Employees submit receipts at <code>{window.location.origin}/#/capture</code></p>
        </div>
      )}
    </div>
  );
}
