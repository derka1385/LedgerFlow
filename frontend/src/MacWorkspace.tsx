import { useId, useState } from "react";
import { Wordmark } from "./Brand";
import { req } from "./lib/api";
import { ErrorNote, Icon } from "./ui";

const sources = [
  { id: "excel", name: "Excel", glyph: "X", color: "#237251" },
  { id: "fortnox", name: "Fortnox", glyph: "F", color: "#397657" },
  { id: "visma", name: "Visma", glyph: "V", color: "#a04350" },
  { id: "quickbooks", name: "QuickBooks", glyph: "Q", color: "#446b2f" },
  { id: "sap", name: "SAP", glyph: "S", color: "#1d6489" },
  { id: "dynamics", name: "Microsoft Dynamics", glyph: "D", color: "#4b5492" },
  { id: "other", name: "Other ERP", glyph: "↗", color: "#555e58" },
] as const;

export type WorkspaceProfile = { name: string; source: typeof sources[number]["id"] };
export const sourceName = (source: WorkspaceProfile["source"]) => sources.find(item => item.id === source)?.name;

export function MacWaves() {
  const ink = useId();
  return <svg className="mac-waves" viewBox="0 0 640 360" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs><linearGradient id={ink}><stop stopColor="#c1dba6" stopOpacity=".05"/><stop offset=".46" stopColor="#c1dba6" stopOpacity=".55"/><stop offset="1" stopColor="#c1dba6" stopOpacity=".1"/></linearGradient></defs>
    <g fill="none" stroke={`url(#${ink})`} strokeWidth=".85">
      {Array.from({length: 13}, (_, i) => <path key={i} vectorEffect="non-scaling-stroke" d={`M-60 ${326 + i * 8} C94 ${333 + i * 7} 124 ${154 + i * 7} 271 ${178 + i * 9} S439 ${312 + i * 6} 702 ${179 + i * 9}`}/>)}
    </g>
  </svg>;
}

export function MacReceipt() {
  return <svg className="mac-receipt" viewBox="0 0 110 124" width="110" height="124" aria-hidden="true">
    <path fill="#eaf2d8" d="M18 6h53l21 21v85l-12-8-12 8-12-8-12 8-12-8-14 8z"/>
    <path fill="#a9c395" d="M71 6v21h21z"/>
    <path fill="none" stroke="#245843" strokeLinecap="round" strokeWidth="3" d="M31 26h23m-23 16h43M31 55h43M31 68h43m-18 18 7 7 13-15"/>
  </svg>;
}

export function MacIntro({ onHoldEnd, onSkip, onExit, leaving }: {
  onHoldEnd: () => void; onSkip: () => void; onExit: () => void; leaving: boolean;
}) {
  return <main className={`mac-intro${leaving ? " mac-intro-leaving" : ""}`} aria-label="Opening LedgerFlow"
    onAnimationEnd={event => { if (event.target === event.currentTarget && event.animationName === "mac-intro-exit") onExit(); }}>
    <MacWaves/>
    <div className="mac-intro-brand">
      <MacReceipt/>
      <span className="mac-intro-name" onAnimationEnd={event => { if (event.animationName === "mac-intro-name") onHoldEnd(); }}>
        <Wordmark/>
      </span>
    </div>
    <button className="mac-intro-skip" type="button" onClick={onSkip}>Skip introduction</button>
  </main>;
}

export function WorkspaceSetup({ profile, onSave, onCancel }: {
  profile: WorkspaceProfile | null; onSave: (profile: WorkspaceProfile) => void; onCancel?: () => void;
}) {
  const [name, setName] = useState(profile?.name ?? "");
  const [source, setSource] = useState<WorkspaceProfile["source"]>(profile?.source ?? "excel");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  return <main className={`mac-setup${profile ? "" : " mac-setup-first"}`}>
    <section className="mac-setup-art"><MacWaves/><div><MacReceipt/><Wordmark/></div></section>
    <form className="mac-setup-form" onSubmit={async event => {
      event.preventDefault();
      setBusy(true); setError(null);
      try {
        const result = await req<{ profile: WorkspaceProfile }>("POST", "/desktop/workspace-profile", {body: { name, source }});
        onSave(result.profile);
      } catch (error) { setError(error); } finally { setBusy(false); }
    }}>
      <div className="mac-setup-heading">
        <h1>{profile ? "Workspace settings" : "Set up your workspace"}</h1>
        <p className="muted">Your local profile keeps your workbooks, receipts and agent activity together on this Mac.</p>
      </div>
      <div className="mac-setup-name">
        <label htmlFor="mac-workspace-name">Workspace name</label>
        <input id="mac-workspace-name" value={name} onChange={e => setName(e.target.value)} placeholder="Company or team" required maxLength={80}/>
      </div>
      <fieldset><legend>Where do your accounts live?</legend><div className="accounting-sources">
        {sources.map(item => <label key={item.id} className="accounting-source">
          <input type="radio" name="source" value={item.id} checked={source === item.id} onChange={() => setSource(item.id)}/>
          <span style={{backgroundColor: item.color}} aria-hidden="true">{item.glyph}</span>{item.name}
        </label>)}
      </div></fieldset>
      <div className="mac-setup-actions">
        <p className="mac-source-note" aria-live="polite">{source === "excel" ? "Import a compatible Excel workbook and review its account mapping before processing receipts." : `${sourceName(source)} is saved as your source. To process receipts today, import a compatible .xlsx workbook. Direct sync is not available yet.`}</p>
        <ErrorNote error={error}/>
        <div className="row"><button className="btn primary" disabled={busy || !name.trim()}>{busy ? "Saving…" : profile ? "Save workspace" : "Create workspace"}<Icon name="arrow"/></button>{onCancel ? <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button> : null}</div>
      </div>
    </form>
  </main>;
}
