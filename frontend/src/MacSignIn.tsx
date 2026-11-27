import { useState } from "react";
import { BrandMark, Wordmark } from "./Brand";
import { adoptSession, req } from "./lib/api";
import type { Session } from "./lib/types";
import { ErrorNote, Icon } from "./ui";

/** Sign-in on the Mac after a sign-out: email + password, then a short staged loading like the first setup. */
export default function MacSignIn({ onSignedIn }: { onSignedIn: (s: Session) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  return <main className="mac-signin">
    <form className="mac-signin-card stack" onSubmit={async e => {
      e.preventDefault(); if (busy) return;
      setBusy(true); setError(null);
      const started = performance.now();
      try {
        const s = await req<Session>("POST", "/desktop/login", { body: { email, password } });
        const wait = 1400 - (performance.now() - started);
        if (wait > 0 && !matchMedia("(prefers-reduced-motion: reduce)").matches) await new Promise(r => window.setTimeout(r, wait));
        adoptSession(s); history.replaceState(null, "", "/#/agent"); onSignedIn(s);
      } catch (err) { setError(err); setBusy(false); }
    }}>
      <BrandMark size={52}/>
      <Wordmark/>
      <h1>{busy ? "Opening your workspace…" : "Sign in"}</h1>
      {busy ? <div className="setup-bar signin-bar" role="status" aria-label="Signing in"><i/></div> : <>
        <p className="muted">Use your LedgerFlow account on this Mac.</p>
        <label htmlFor="mac-email">Email</label>
        <input id="mac-email" type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} required autoFocus/>
        <label htmlFor="mac-password">Password</label>
        <input id="mac-password" type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required/>
        <ErrorNote error={error}/>
        <button className="btn primary" disabled={!email || !password}>Sign in<Icon name="arrow"/></button>
      </>}
    </form>
  </main>;
}
