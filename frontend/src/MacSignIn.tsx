import { useEffect, useRef, useState } from "react";
import { Wordmark } from "./Brand";
import { MacReceipt, MacWaves } from "./MacWorkspace";
import { adoptSession, req } from "./lib/api";
import type { Session } from "./lib/types";
import { ErrorNote, Icon } from "./ui";

type GoogleFlow = { url: string; poll: string };
type MacWindow = Window & { webkit?: { messageHandlers?: { openGoogleSignIn?: { postMessage: (url: string) => void } } } };

export default function MacSignIn({ onSignedIn, launchToken }: {
  onSignedIn: (s: Session) => void; launchToken?: string;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [google, setGoogle] = useState<GoogleFlow | null>(null);
  const [error, setError] = useState<unknown>(null);
  const completion = useRef(onSignedIn);
  useEffect(() => { completion.current = onSignedIn; }, [onSignedIn]);

  function finish(session: Session) {
    adoptSession(session);
    completion.current(session);
  }

  useEffect(() => {
    if (!google) return;
    let active = true;
    let timer = 0;
    async function poll() {
      try {
        const result = await req<Session | {pending: true}>("POST", "/desktop/google/finish", {body: {poll: google?.poll}});
        if (!active) return;
        if ("pending" in result) timer = window.setTimeout(poll, 1500);
        else finish(result);
      } catch (reason) {
        if (active) { setError(reason); setGoogle(null); }
      }
    }
    timer = window.setTimeout(poll, 1500);
    return () => { active = false; window.clearTimeout(timer); };
  }, [google]);

  async function authenticate(path: string, body: Record<string, unknown>) {
    if (busy) return;
    setBusy(true); setError(null);
    try {
      finish(await req<Session>("POST", path, {body}));
    } catch (reason) { setError(reason); }
    finally { setBusy(false); }
  }

  async function prepareGoogle() {
    setBusy(true); setError(null);
    try {
      const flow = await req<GoogleFlow>("POST", "/desktop/google/start", {body: {launch_token: launchToken}});
      setGoogle(flow);
      (window as MacWindow).webkit?.messageHandlers?.openGoogleSignIn?.postMessage(flow.url);
    }
    catch (reason) { setError(reason); }
    finally { setBusy(false); }
  }

  return <main className="mac-setup mac-setup-first mac-signin-page">
    <section className="mac-setup-art"><MacWaves/><div><MacReceipt/><Wordmark/></div></section>
    <form className="mac-setup-form mac-signin-form" onSubmit={event => {
      event.preventDefault();
      void authenticate("/desktop/login", {email, password, launch_token: launchToken});
    }}>
      <div className="mac-setup-heading"><h1>Welcome back</h1><p className="muted">Sign in with your Orvect account to open LedgerFlow on this Mac.</p></div>
      {google ? <div className="stack">
        <p className="muted" role="status">Waiting for Google to finish signing you in…</p>
        <a className="google-signin-button" href={google.url} onClick={event => {
          if (!document.documentElement.classList.contains("mac-shell")) { event.preventDefault(); window.open(google.url, "_blank", "noopener"); }
        }}><img src="/icons/google-g.png" alt="" width="18" height="18"/>Reopen Google sign-in</a>
        <button type="button" className="btn ghost" onClick={() => setGoogle(null)}>Cancel</button>
      </div> : <>
        <div className="mac-setup-name"><label htmlFor="mac-email">Email</label>
          <input id="mac-email" type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} required/></div>
        <div className="mac-setup-name"><label htmlFor="mac-password">Password</label>
          <input id="mac-password" type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required/></div>
        <div className="mac-setup-actions stack">
          <ErrorNote error={error}/>
          <button className="btn primary" disabled={busy || !email || !password}>Sign in<Icon name="arrow"/></button>
          <button type="button" className="google-signin-button" disabled={busy} onClick={() => void prepareGoogle()}>
            <img src="/icons/google-g.png" alt="" width="18" height="18"/>Continue with Google
          </button>
          {launchToken ? <button type="button" className="btn ghost" disabled={busy} onClick={() => void authenticate("/desktop/bootstrap", {token: launchToken})}>Open local workspace</button> : null}
          {busy ? <div className="setup-bar signin-bar" role="status" aria-label="Signing in"><i/></div> : null}
        </div>
      </>}
    </form>
  </main>;
}
