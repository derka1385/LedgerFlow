import { useState } from "react";
import { Wordmark } from "./Brand";
import { ScanWithPhone } from "./Continuity";
import Explainer from "./Explainer";
import { MacReceipt, type SetupStep, type WorkspaceProfile } from "./MacWorkspace";
import { req } from "./lib/api";
import type { Session } from "./lib/types";
import Onboarding from "./pages/Onboarding";
import { ErrorNote, Icon } from "./ui";

const steps = [
  ["workbook", "Workbook"],
  ["guide", "How it works"],
  ["iphone", "iPhone (optional)"],
] as const;

export default function MacSetupFlow({ session, profile, onChange }: {
  session: Session; profile: WorkspaceProfile; onChange: (profile: WorkspaceProfile) => void;
}) {
  const [pairing, setPairing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const step = profile.setup_step === "guide" || profile.setup_step === "iphone" ? profile.setup_step : "workbook";
  const advance = async (next: SetupStep) => {
    if (busy) return;
    setBusy(true); setError(null);
    try {
      const response = await req<{profile: WorkspaceProfile}>("POST", "/desktop/workspace-setup", {body: {step: next}});
      if (next === "complete") setFinished(true);
      onChange(response.profile);
    } catch (reason) { setError(reason); }
    finally { setBusy(false); }
  };
  return <main className="mac-connect-workspace stack-lg">
    <header className="mac-setup-header">
      <div className="brand"><MacReceipt size={31}/><Wordmark/></div>
      <ol aria-label="Workspace setup progress">
        {steps.map(([key, label]) => <li key={key} aria-current={key === step ? "step" : undefined}>{label}</li>)}
      </ol>
    </header>
    <ErrorNote error={error}/>
    {finished ? <p role="status">Opening your agent…</p> : step === "workbook" ? <>
      <Onboarding session={session} embedded onContinue={() => void advance("guide")} continuing={busy}/>
      <div><button className="btn ghost" disabled={busy} onClick={() => void advance("guide")}>Continue without a workbook</button></div>
    </> : step === "guide" ? <Explainer manual doneLabel="Continue to iPhone setup" onDone={() => void advance("iphone")}/>
      : <section className="panel stack-lg mac-setup-iphone">
        <div className="mac-setup-device"><Icon name="phone"/></div>
        <div className="stack"><h1>Connect your iPhone</h1><p className="muted">Scan receipts on your iPhone and see the same documents and expenses on your Mac.</p>
          <p className="muted">Keep both devices on the same Wi-Fi. You can connect later from Account &amp; settings.</p></div>
        <div className="row">
          <button className="btn primary" disabled={busy} onClick={() => setPairing(true)}>Show pairing code</button>
          <button className="btn ghost" disabled={busy} onClick={() => void advance("complete")}>{busy ? "Finishing…" : "Skip for now"}</button>
        </div>
      </section>}
    {pairing ? <ScanWithPhone session={session} onClose={() => setPairing(false)}
      onPaired={() => { setPairing(false); void advance("complete"); }}/> : null}
  </main>;
}
