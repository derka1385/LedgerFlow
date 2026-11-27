import { useRef, useState } from "react";
import type { CSSProperties } from "react";
import { go } from "../App";
import { listRuns } from "../lib/api";
import { ACTIVE_STATES, ATTENTION_STATES } from "../lib/experience";
import { localTime, money } from "../lib/format";
import type { Session } from "../lib/types";
import { usePolling } from "../lib/usePolling";
import { ErrorNote, Icon, Skeleton, StatePill } from "../ui";
import Review from "./Review";

export default function Transactions({ session, selected, mode = "transactions" }: { session: Session; selected?: string; mode?: string }) {
  const { data, error } = usePolling(listRuns);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState(() => { const f = new URLSearchParams(location.hash.split("?")[1] ?? "").get("filter"); return ["approval", "questions", "active"].includes(f ?? "") ? f! : "all"; });
  const [width, setWidth] = useState(292);
  const [context, setContext] = useState<string | null>(null);
  const drag = useRef<{ x: number; width: number } | null>(null);
  const audit = mode === "audit";
  const runs = (data?.items ?? []).filter(r => (!audit || ["COMMITTED", "REJECTED", "CANCELLED"].includes(r.state)) && (!query || `${r.merchant_name ?? ""} ${r.run_id} ${r.document_date ?? ""}`.toLowerCase().includes(query.toLowerCase())) && (filter === "all" || (filter === "approval" ? r.state === "AWAITING_APPROVAL" : filter === "questions" ? ATTENTION_STATES.includes(r.state) : ACTIVE_STATES.includes(r.state))));
  const title = { transactions: "Transactions", receipts: "Receipts", activity: "Agent Activity", audit: "Audit History" }[mode] ?? "Transactions";
  const open = (id: string) => go(`${mode}/${id}`);
  const selectedId = selected ?? runs[0]?.run_id;
  return <div className="stack-lg"><div className="page-heading"><div><h1>{title}</h1><p className="muted">{audit ? "Decisions, verified changes and workbook versions." : mode === "activity" ? "Inspect the agent’s decisions, code and execution." : "Review the source document alongside the proposed entry."}</p></div><a href="#/capture" className="btn"><Icon name="upload" />Submit a receipt</a></div><ErrorNote error={error} />
    <div className="transaction-workspace" style={{ "--list-width": `${width}px` } as CSSProperties}>
      <section className="transaction-list" aria-label={`${title} list`}>
        <div className="list-tools"><label className="search-field"><Icon name="search" /><input id="workspace-search" type="search" placeholder="Search documents" aria-label="Search documents" value={query} onChange={e => setQuery(e.target.value)} /></label>
          {!audit ? <select aria-label="Filter transactions" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All documents</option><option value="approval">Awaiting approval</option><option value="questions">Need attention</option><option value="active">In progress</option></select> : <p className="small">Actual decisions and linked workbook versions.</p>}
        </div>
        {!data ? <Skeleton lines={5} /> : runs.length ? <div className="transaction-items">{runs.map((r, i) => <div key={r.run_id} className="transaction-item-wrap"><button data-run-id={r.run_id} className={`transaction-item ${selectedId === r.run_id ? "selected" : ""}`} aria-current={selectedId === r.run_id ? "true" : undefined} onClick={() => open(r.run_id)} onContextMenu={e => { e.preventDefault(); setContext(context === r.run_id ? null : r.run_id); }} onKeyDown={e => { if (["ArrowDown", "ArrowUp"].includes(e.key)) { e.preventDefault(); open(runs[Math.max(0, Math.min(runs.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)))].run_id); } }}>
          <span className="spread"><strong>{r.merchant_name ?? "Reading document…"}</strong><span className="mono">{money(r.gross_minor)}</span></span><span className="small">{r.document_date ?? localTime(r.created_at).slice(0, 10)}</span><StatePill state={r.state} />
        </button>{context === r.run_id ? <div className="context-actions"><a className="btn" href={`#/runs/${r.run_id}`}>Open review</a><a className="btn" href={`#/activity/${r.run_id}`}>Execution details</a><button className="btn ghost" onClick={() => setContext(null)}>Close</button></div> : null}</div>)}</div> : <div className="empty"><Icon name="file" /><p>No matching documents.</p></div>}
      </section>
      <div className="split-handle" role="separator" aria-label="Resize document list" aria-orientation="vertical" tabIndex={0} aria-valuemin={240} aria-valuemax={440} aria-valuenow={width} onKeyDown={e => { if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); setWidth(w => Math.max(240, Math.min(440, w + (e.key === "ArrowRight" ? 16 : -16)))); } }} onPointerDown={e => { drag.current = { x: e.clientX, width }; e.currentTarget.setPointerCapture(e.pointerId); }} onPointerMove={e => { if (drag.current) setWidth(Math.max(240, Math.min(440, drag.current.width + e.clientX - drag.current.x))); }} onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }} />
      <section className="transaction-detail" aria-label="Selected document">
        {selectedId ? <Review key={`${selectedId}-${mode}`} runId={selectedId} session={session} activityOnly={mode === "activity"} /> : <div className="detail-empty"><Icon name={mode === "activity" ? "terminal" : audit ? "clock" : "file"} /><h2>{mode === "activity" ? "No execution selected" : "No document selected"}</h2><p className="muted">{runs.length ? "Select a document from the list to inspect it." : "Submit a receipt to begin. Its source, entry and verification will appear here."}</p></div>}
      </section>
    </div>
  </div>;
}
