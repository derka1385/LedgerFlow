import { useState } from "react";
import { Wordmark } from "./Brand";
import { MacReceipt, MacWaves } from "./MacWorkspace";
import { adoptSession, req } from "./lib/api";
import type { Session } from "./lib/types";
import { ErrorNote, Icon } from "./ui";

/** Sign-in on the Mac after a sign-out: email + password, then a short staged loading like the first setup. */
export default function MacSignIn({ onSignedIn }: { onSignedIn: (s: Session) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  return <main className="mac-setup mac-setup-first mac-signin-page">
    <section className="mac-setup-art"><div className="lf-clouds" aria-hidden="true"><i/><i/><i/><i/><i/></div><MacWaves/><div><MacReceipt/><Wordmark/></div></section>
    <form className="mac-setup-form mac-signin-form" onSubmit={async e => {
      e.preventDefault(); if (busy) return;
      setBusy(true); setError(null);
      const started = performance.now();
      try {
        const s = await req<Session>("POST", "/desktop/login", { body: { email, password } });
        const wait = 1400 - (performance.now() - started);
        if (wait > 0 && !matchMedia("(prefers-reduced-motion: reduce)").matches) await new Promise(r => window.setTimeout(r, wait));
        adoptSession(s); onSignedIn(s); location.replace("#/agent");
      } catch (err) { setError(err); setBusy(false); }
    }}>
      <div className="mac-setup-heading">
        <h1>{busy ? "Opening your workspace…" : "Welcome back"}</h1>
        <p className="muted">{busy ? "Loading your workbooks, receipts and agent." : "Sign in to your LedgerFlow account on this Mac."}</p>
      </div>
      {busy ? <div className="setup-bar signin-bar" role="status" aria-label="Signing in"><i/></div> : <>
        <div className="mac-setup-name"><label htmlFor="mac-email">Email</label>
          <input id="mac-email" type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} required autoFocus/></div>
        <div className="mac-setup-name"><label htmlFor="mac-password">Password</label>
          <input id="mac-password" type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required/></div>
        <div className="mac-setup-actions"><ErrorNote error={error}/>
          <button className="btn primary" disabled={!email || !password}>Sign in<Icon name="arrow"/></button></div>
      </>}
    </form>
  </main>;
}
