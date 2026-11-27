import { useEffect, useId, useState } from "react";
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

export type SetupStep = "workbook" | "guide" | "iphone" | "complete";
export type WorkspaceProfile = { name: string; source: typeof sources[number]["id"]; agent_name?: string; setup_step?: SetupStep };
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

export function MacReceipt({ size = 110 }: { size?: number }) {
  return <svg className="mac-receipt" viewBox="0 0 110 124" width={size} height={size * 124 / 110} aria-hidden="true">
    <path fill="#eaf2d8" d="M18 6h53l21 21v85l-12-8-12 8-12-8-12 8-12-8-14 8z"/>
    <path fill="#a9c395" d="M71 6v21h21z"/>
    <path fill="none" stroke="#245843" strokeLinecap="round" strokeWidth="3" d="M31 26h23m-23 16h43M31 55h43M31 68h43m-18 18 7 7 13-15"/>
  </svg>;
}

export function MacIntro({ onHoldEnd, onSkip, onExit, leaving, waiting }: {
  onHoldEnd: () => void; onSkip: () => void; onExit: () => void; leaving: boolean; waiting: boolean;
}) {
  return <main className={`mac-intro${leaving ? " mac-intro-leaving" : ""}${waiting ? " mac-intro-waiting" : ""}`} aria-label="Opening LedgerFlow"
    onAnimationEnd={event => { if (event.target === event.currentTarget && event.animationName === "mac-intro-exit") onExit(); }}>
    <MacWaves/>
    <div className="mac-intro-brand">
      <MacReceipt/>
      <span className="mac-intro-name" onAnimationEnd={event => { if (event.animationName === "mac-intro-name") onHoldEnd(); }}>
        <Wordmark/>
      </span>
    </div>
    {waiting ? <p className="mac-intro-status" role="status">Opening your workspace…</p> : <button className="mac-intro-skip" type="button" onClick={onSkip}>Skip introduction</button>}
  </main>;
}

export function WorkspaceSetup({ profile, onSave, onCancel }: {
  profile: WorkspaceProfile | null; onSave: (profile: WorkspaceProfile) => void; onCancel?: () => void;
}) {
  const [name, setName] = useState(profile?.name ?? "");
  const [agentName, setAgentName] = useState(profile?.agent_name ?? "");
  const [step, setStep] = useState<"agent" | "workspace">(profile?.agent_name ? "workspace" : "agent");
  const [source, setSource] = useState<WorkspaceProfile["source"]>(profile?.source ?? "excel");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  return <main className={`mac-setup${profile ? "" : " mac-setup-first"}`}>
    <section className="mac-setup-art"><MacWaves/><div><MacReceipt/><Wordmark/></div></section>
    {!profile && busy ? <section className="mac-setup-loading stack" role="status" aria-live="polite" aria-labelledby="setup-loading-title">
      <h1 id="setup-loading-title">Preparing your workspace</h1>
      <SetupProgress agent={agentName.trim() || "LedgerFlow"}/>
    </section> : <form key={step} className="mac-setup-form" onSubmit={async event => {
      event.preventDefault();
      if (step === "agent" && !profile) { if (agentName.trim()) setStep("workspace"); return; }
      if (busy) return;
      setBusy(true); setError(null);
      const started = performance.now();
      try {
        const result = await req<{ profile: WorkspaceProfile }>("POST", "/desktop/workspace-profile", {body: { name, source, agent_name: agentName.trim() || "LedgerFlow" }});
        if (!profile && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
          const remaining = SETUP_MS - (performance.now() - started);
          if (remaining > 0) await new Promise(resolve => window.setTimeout(resolve, remaining));
        }
        onSave(result.profile);
      } catch (error) { setError(error); } finally { setBusy(false); }
    }}>
      {step === "agent" ? <>
        <div className="mac-setup-heading"><h1>Name your agent</h1><p className="muted">You’ll see this name in your workspace and conversation.</p></div>
        <div className="mac-setup-name"><label htmlFor="mac-agent-name">Agent name</label><input id="mac-agent-name" value={agentName} onChange={event => setAgentName(event.target.value)} placeholder="e.g. Atlas" required maxLength={48}/></div>
        <div className="mac-setup-actions"><ErrorNote error={error}/><button className="btn primary" disabled={busy || !agentName.trim()}>{busy ? "Saving…" : "Continue"}<Icon name="arrow"/></button></div>
      </> : <>
      <div className="mac-setup-heading">
        <h1>{profile ? "Workspace settings" : "Set up your workspace"}</h1>
        <p className="muted">Choose where {agentName.trim() || "LedgerFlow"} should work. Your workspace is saved on this Mac.</p>
      </div>
      {profile ? <div className="mac-setup-name"><label htmlFor="mac-agent-name">Agent name</label><input id="mac-agent-name" value={agentName} onChange={event => setAgentName(event.target.value)} placeholder="LedgerFlow" maxLength={48}/></div> : null}
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
        <div className="row"><button className="btn primary" disabled={busy || !name.trim()}>{busy ? "Saving…" : profile ? "Save workspace" : "Create workspace"}<Icon name="arrow"/></button>{onCancel ? <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button> : <button type="button" className="btn ghost" onClick={() => setStep("agent")}>Back</button>}</div>
      </div>
      </>}
    </form>}
  </main>;
}

const SETUP_MS = 3200;
/** Staged loading, so the first launch shows what the Mac is setting up instead of a bare bar. */
function SetupProgress({ agent }: { agent: string }) {
  const steps = [`Creating ${agent}`, "Saving the workspace on this Mac", "Preparing a sample Excel workbook", "Checking the Vultr model connection"];
  const [done, setDone] = useState(0);
  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) { setDone(steps.length); return; }
    const timer = window.setInterval(() => setDone(n => Math.min(n + 1, steps.length)), SETUP_MS / (steps.length + 1));
    return () => window.clearInterval(timer);
  }, [steps.length]);
  return <div className="setup-progress">
    <div className="setup-bar" aria-hidden="true"><i style={{ width: `${(done / steps.length) * 100}%` }}/></div>
    <ol>{steps.map((s, i) => <li key={s} className={i < done ? "done" : i === done ? "now" : ""}>
      <span aria-hidden="true">{i < done ? <Icon name="check"/> : null}</span>{s}</li>)}</ol>
  </div>;
}
