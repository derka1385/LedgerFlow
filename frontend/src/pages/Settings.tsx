import type { Session } from "../lib/types";
import { useEffect, useState } from "react";
import { LangSwitch } from "../App";
import { req } from "../lib/api";
import { Callout, ErrorNote, Icon } from "../ui";

export type Appearance = "system" | "light" | "dark";
type SettingsProps = { session: Session; appearance: Appearance; setAppearance: (a: Appearance) => void; onSignOut: () => void; mac?: boolean; onPhone?: () => void };

export default function Settings({ session, appearance, setAppearance, onSignOut, mac, onPhone }: SettingsProps) {
  if (session.backend === "LOCAL") return <LocalSettings session={session} appearance={appearance} setAppearance={setAppearance} onSignOut={onSignOut} mac={mac} onPhone={onPhone}/>;
  return <div className="stack-lg settings"><div><h1>{session.role === "employee" ? "Profile" : "Settings"}</h1></div><section className="panel stack"><h2>Signed in as</h2><dl className="kv"><dt>Name</dt><dd>{session.display_name ?? session.user_id}</dd><dt>Role</dt><dd>{session.role}</dd><dt>Session expires</dt><dd>{new Date(session.expires_at).toLocaleString()}</dd></dl><div><button className="btn" onClick={onSignOut}>Sign out</button></div></section>
    <section className="panel stack"><h2>Appearance</h2><div className="segmented" aria-label="Appearance">{(["system", "light", "dark"] as const).map(a => <button key={a} aria-pressed={appearance === a} onClick={() => setAppearance(a)}>{a === "system" ? "Use device setting" : a === "light" ? "Light" : "Dark"}</button>)}</div><p className="small">Appearance is saved on this device. Financial data and credentials are not stored in local storage.</p></section>
    <section className="panel stack"><h2><Icon name="download" /> Install LedgerFlow</h2><p><strong>Mac:</strong> open the public HTTPS app in Safari, then choose Share → Add to Dock.</p><p><strong>iPhone:</strong> open it in Safari, choose Share → Add to Home Screen. Sign in with your employee invite.</p><p className="muted">The browser app has the same workflows. An internet connection is required to submit, process and approve receipts.</p></section>
    {session.role !== "employee" ? <section className="panel stack"><h2>Keyboard shortcuts</h2><dl className="kv"><dt>⌘ / Ctrl + 1–9</dt><dd>Switch workspace</dd><dt>⌘ / Ctrl + K</dt><dd>Find a document</dd><dt>⌘ / Ctrl + N</dt><dd>Submit a receipt</dd><dt>Escape</dt><dd>Close a dialog or execution monitor</dd></dl></section> : null}
    <Callout tone="info" title="One shared service">Mac, iPhone and browser use the same authenticated API. Generated accounting programs execute on the server’s isolated infrastructure.</Callout>
  </div>;
}

function LocalSettings({ session, appearance, setAppearance, onSignOut, mac, onPhone }: SettingsProps) {
  const [status,setStatus]=useState<{vision:boolean;model:string|null;docker:boolean;image_ready:boolean}|null>(null);
  const [error,setError]=useState<unknown>(null);
  const [loading,setLoading]=useState(false);
  const refresh=async()=>{setLoading(true);setError(null);try{setStatus(await req("GET","/desktop/status"));}catch(e){setError(e);}finally{setLoading(false);}};
  useEffect(()=>{void refresh();},[]);
  return <div className="stack-lg settings"><h1>{mac ? "Account & settings" : "Settings"}</h1>
    {mac ? <section className="panel stack"><h2>Workspace profile</h2><div className="row"><a href="#/workspace-profile" className="btn">Edit agent and workspace</a><a href="#/connect-workspace" className="btn">Open setup walkthrough</a></div><h2>Language</h2><LangSwitch/></section> : null}
    <section className="panel stack"><h2>Your local workspace</h2><p>Workbooks, receipts and the conversation are stored on your Mac. The vision model uses the Vultr service configured for this project.</p><p className="muted">Closing the window keeps LedgerFlow running in the background. Quitting the app or putting the Mac to sleep stops access from the iPhone.</p></section>
    {mac ? <section className="panel stack"><h2>iPhone</h2><p>Pair your iPhone to share this workspace, receipts and expenses over Wi-Fi.</p><button className="btn primary" onClick={onPhone}><Icon name="phone"/>Connect iPhone</button></section> : <section className="panel stack"><h2>Mac and iPhone</h2><p>Open LedgerFlow on the iPhone, then <strong>Pair with my Mac</strong>. Scan the code shown on the Mac under “Scan with iPhone”.</p><p className="muted">Both devices must be on the same network. The code carries the server address and the Mac’s encrypted identity.</p></section>}
    <section className="panel stack"><h2>Model connection</h2><dl className="kv"><dt>Vision</dt><dd>{status ? status.vision ? `${status.model} · configured` : "Not configured" : "Checking…"}</dd><dt>Isolated execution</dt><dd>{status ? status.docker && status.image_ready ? "Docker ready" : "Start Docker Desktop and its image" : "Checking…"}</dd></dl><button className="btn" disabled={loading} onClick={()=>void refresh()}><Icon name="refresh"/>{loading ? "Checking…" : "Check engine status"}</button><ErrorNote error={error}/>
      <details><summary>Setup help on the Mac</summary><div className="stack" style={{paddingTop:12}}><p>If vision is not configured, the Mac owner adds the Vultr key to the project’s local <code>.env</code> file as <code>VULTR_INFERENCE_API_KEY</code>, then quits and reopens LedgerFlow. The model is set in <code>config/inference.json</code>.</p><p>If execution is not ready, open Docker Desktop on the Mac. The expected sandbox image is <code>python:3.12-slim</code>. No accounting program runs outside this isolation.</p><p className="small">Never paste a key into the conversation, a server address or a QR code. This page neither shows nor changes the key.</p></div></details>
    </section>
    <section className="panel stack"><h2>Appearance</h2><div className="segmented" aria-label="Appearance">{(["system","light","dark"] as const).map(a=><button key={a} aria-pressed={appearance===a} onClick={()=>setAppearance(a)}>{a==="system"?"System":a==="light"?"Light":"Dark"}</button>)}</div></section>
    <section className="panel stack"><h2>This session</h2><p>{session.role === "employee" ? "Receipt capture, without approval rights." : "Access to the workspace and its approvals."}</p><p className="small">After signing out, sign in again on the Mac with your email and password, or pair the iPhone again.</p><button className="btn" onClick={onSignOut}>Sign out</button></section>
  </div>;
}
