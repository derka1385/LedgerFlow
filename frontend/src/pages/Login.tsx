import { useState } from "react";
import { signIn } from "../lib/api";
import type { Session } from "../lib/types";
import { ErrorNote, Icon } from "../ui";
import { BrandMark, Wordmark } from "../Brand";

const DEMO = [["employee-demo", "Employee", "Photograph receipts"], ["accountant-demo", "Accountant", "Review and approve"],
  ["owner-demo", "Owner", "Connect the workbook"]] as const;

export default function Login({ onSignedIn }: { onSignedIn: (s: Session) => void }) {
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const submit = async (t: string) => {
    setBusy(true);
    setError(null);
    try { onSignedIn(await signIn(t.trim())); } catch (e) { setError(e); } finally { setBusy(false); }
  };
  return (
    <main className="login-page">
      <div className="login-heading">
        <div className="brand"><BrandMark size={38} /><Wordmark /></div>
        <h1>Sign in to your workspace</h1>
        <p className="muted">Use the invite provided by your team.</p>
      </div>
      <form className="login-form stack" onSubmit={(e) => { e.preventDefault(); submit(token); }}>
        <label htmlFor="invite">Invite code
          <input id="invite" autoComplete="one-time-code" autoCapitalize="none" autoCorrect="off" spellCheck={false} value={token} onChange={(e) => setToken(e.target.value)} placeholder="Paste your invite" />
        </label>
        <button className="btn primary" disabled={!token.trim() || busy}>{busy ? "Signing in…" : "Sign in"}</button>
        <ErrorNote error={error} />
      </form>
      {import.meta.env.DEV || import.meta.env.VITE_DEV_DEMO === "1" ? <section className="login-demo stack" aria-labelledby="demo-h">
        <h2 id="demo-h">Demo invites (development backend)</h2>
        <div className="demo-role-list">
          {DEMO.map(([t, role, what]) => (
            <button key={t} className="btn" disabled={busy} onClick={() => submit(t)}>
              <span><strong>{role}</strong> <span className="muted">· {what}</span></span><Icon name="play" />
            </button>
          ))}
        </div>
      </section> : null}
      <footer className="login-footer"><p>Your Excel. Your business. Our agent.</p><details><summary>How LedgerFlow works</summary><p>Employees photograph receipts. LedgerFlow prepares the double entry, edits a copy of your own workbook in an isolated sandbox, and shows you every changed cell before you approve.</p></details></footer>
    </main>
  );
}
