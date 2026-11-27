import { useEffect, useState } from "react";
import { listRuns, listWorkbooks, subscribeRunEvents } from "../lib/api";
import { localTime, mergeEvents, money } from "../lib/format";
import { ACTIVE_STATES, ATTENTION_STATES, executionMetrics } from "../lib/experience";
import type { ExecutionEvent, RunListItem } from "../lib/types";
import { usePolling } from "../lib/usePolling";
import { MacWaves } from "../MacWorkspace";
import { ErrorNote, Icon, Skeleton, StatePill } from "../ui";

const EVENT_NAMES: Record<string, string> = {
  "extraction.completed": "Document extracted", "plan.admitted": "Entry planned", "code.generated": "Python generated",
  "sandbox.created": "Sandbox provisioned", "sandbox.started": "Execution started", "sandbox.exited": "Execution finished",
  "sandbox.destroyed": "Sandbox destroyed", "validation.completed": "Independent verification", "commit.completed": "Workbook committed",
  "review.required": "Review requested", "run.failed": "Execution stopped", "retry.scheduled": "Repair scheduled",
};

function AgentPeek({ run }: { run: RunListItem | undefined }) {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [stream, setStream] = useState("connecting");
  useEffect(() => {
    setEvents([]);
    if (!run) return;
    return subscribeRunEvents(run.run_id, 0, e => setEvents(prev => mergeEvents(prev, [e])), setStream);
  }, [run?.run_id]);
  const metrics = executionMetrics(events);
  const steps = events.filter(e => EVENT_NAMES[e.event_type]).slice(-5);
  return <section className="agent-peek" aria-label="Latest agent execution">
    <div className="section-heading"><h2><Icon name="terminal" />Agent execution</h2>{run ? <a href={`#/activity/${run.run_id}`} aria-label="Open execution"><Icon name="arrow" /></a> : null}</div>
    {run ? <><div className="agent-peek-identity"><strong>{run.merchant_name ?? "Document"}</strong><StatePill state={run.state} /></div>
      <div className="execution-reference"><code>{run.run_id}</code></div>
      {steps.length ? <ol className="execution-trace">{steps.map(e => <li key={e.sequence}><Icon name={e.event_type === "run.failed" || e.data.result === "fail" ? "x" : e.event_type === "code.generated" ? "code" : e.event_type === "sandbox.created" ? "box" : "check"} /><span>{EVENT_NAMES[e.event_type]}</span><time>{localTime(e.occurred_at, true)}</time></li>)}</ol> : <p className="muted compact-note">{stream === "reconnecting" ? "Reconnecting to execution events…" : "Waiting for backend events…"}</p>}
      {metrics.durationMs !== null || metrics.tokens !== null ? <div className="trace-measurements">{metrics.durationMs !== null ? <span>{(metrics.durationMs / 1000).toFixed(2)} s execution</span> : null}{metrics.tokens !== null ? <span>{metrics.tokens.toLocaleString()} tokens reported</span> : null}</div> : null}
      <a className="text-action" href={`#/activity/${run.run_id}`}>Inspect execution<Icon name="arrow" /></a>
    </> : <div className="agent-idle"><Icon name="terminal" /><p>No execution yet.</p><span>Submit a receipt to see extraction, code and verification here.</span></div>}
  </section>;
}

export default function Overview({ mac = false, workspace }: { mac?: boolean; workspace?: string }) {
  const { data, error } = usePolling(async () => { const [runs, workbooks] = await Promise.all([listRuns(), listWorkbooks()]); return { runs: runs.items, workbooks: workbooks.items }; });
  const [view, setView] = useState("all");
  if (!data) return error ? <ErrorNote error={error} /> : <Skeleton lines={6} />;
  const { runs, workbooks } = data;
  const ready = runs.filter(r => r.state === "AWAITING_APPROVAL");
  const questions = runs.filter(r => ATTENTION_STATES.includes(r.state));
  const active = runs.filter(r => ACTIVE_STATES.includes(r.state));
  const rows = view === "approval" ? ready : view === "questions" ? questions : runs;
  const latest = active[0] ?? ready[0] ?? runs[0];
  return <div className="overview">
    {mac ? <header className="mac-dashboard-hero"><MacWaves/><div><p>{workspace}</p><h1>Dashboard</h1><div className="row"><a className="btn primary" href="#/agent"><Icon name="message"/>Open agent</a><a className="btn" href="#/capture"><Icon name="upload"/>Add a receipt</a></div></div></header> : <header className="page-heading"><div><h1>Overview</h1><p className="muted">Documents, agent executions and your next decisions.</p></div><a className="btn primary" href="#/capture"><Icon name="upload" />Submit a receipt</a></header>}
    <ErrorNote error={error} />
    <section className="workspace-counts" aria-label="Current workspace counts">
      {[[ready.length, "Awaiting approval", "transactions?filter=approval"], [questions.length, "Need attention", "transactions?filter=questions"], [active.length, "In progress", "activity?filter=active"], [workbooks.filter(w => w.status === "ready").length, "Connected workbooks", "workbook"]].map(([count, label, link]) => <a key={label} href={`#/${link}`}><strong>{count}</strong><span>{label}</span></a>)}
    </section>
    <div className="workbench-columns">
      <section className="document-queue" aria-label="Documents">
        <div className="section-heading"><h2>Documents</h2><a className="text-action" href="#/transactions">Open workspace<Icon name="arrow" /></a></div>
        <div className="queue-tabs" role="tablist" aria-label="Document queue">{[["all", "All documents", runs.length], ["approval", "To approve", ready.length], ["questions", "Needs attention", questions.length]].map(([key, name, count]) => <button key={key} role="tab" aria-selected={view === key} onClick={() => setView(String(key))}>{name}<span>{count}</span></button>)}</div>
        {rows.length ? <div className="queue-table-wrap"><table className="document-table"><thead><tr><th>Document</th><th>Date</th><th className="num">Amount · SEK</th><th>Status</th><th><span className="sr-only">Review</span></th></tr></thead><tbody>{rows.slice(0, 10).map(r => <tr key={r.run_id}>
          <td><a className="document-name" href={`#/transactions/${r.run_id}`}><Icon name="file" /><span><strong>{r.merchant_name ?? "Reading document…"}</strong><small>{r.kind === "supplier_invoice" ? "Supplier invoice" : "Receipt"}</small></span></a></td>
          <td><time>{r.document_date ?? localTime(r.created_at).slice(0, 10)}</time></td><td className="num">{money(r.gross_minor)}</td><td><StatePill state={r.state} /></td><td><a className="row-open" href={`#/transactions/${r.run_id}`} aria-label={`Review ${r.merchant_name ?? "document"}`}><Icon name="arrow" /></a></td>
        </tr>)}</tbody></table></div> : <div className="queue-empty"><h3>{view === "approval" ? "Nothing awaiting approval." : view === "questions" ? "No open questions." : "Your documents will arrive here."}</h3><p>{view !== "all" ? "New documents appear automatically as the agent processes them." : "Connect your workbook, then capture a receipt on iPhone or upload it here."}</p>{!workbooks.length ? <a className="btn" href="#/workbook"><Icon name="grid" />Connect a workbook</a> : null}</div>}
        <div className="queue-footer"><span>{rows.length} {rows.length === 1 ? "document" : "documents"} in the current list</span><details><summary>About these counts</summary><p>Counts use the current API response, up to its page limit. Execution measurements are shown only when reported by the server.</p></details></div>
      </section>
      <aside className="workbench-inspector">
        <AgentPeek run={latest} />
        <section className="workbook-directory"><div className="section-heading"><h2>Excel workbooks</h2><a href="#/workbook" aria-label="Connect a workbook"><Icon name="upload" /></a></div>{workbooks.length ? workbooks.map(w => <a className="workbook-row" href={`#/workbook/${w.workbook_id}`} key={w.workbook_id}><span className="workbook-file"><Icon name="grid" /></span><span><strong>{w.display_name}</strong><span className="small">{w.status} · {w.version_count} {w.version_count === 1 ? "version" : "versions"}</span></span><Icon name="arrow" /></a>) : <p className="muted compact-note">Connect the Excel workbook your company already uses.</p>}</section>
        <div className="continuity-entry"><Icon name="phone" /><span><strong>Capture from iPhone</strong><span>Use “Scan with iPhone” in the toolbar. Submitted receipts appear in this workspace automatically.</span></span></div>
      </aside>
    </div>
  </div>;
}
