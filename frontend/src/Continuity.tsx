import { useEffect, useRef, useState } from "react";
import QRCode from "qrcode";
import { ApiError, listWorkbooks, req } from "./lib/api";
import { captureLink, pairingLink } from "./lib/experience";
import type { Session, WorkbookView } from "./lib/types";
import { Callout, ErrorNote, Icon } from "./ui";

interface Pairing { pairing_id: string; fragment_token: string; expires_at: string }

export function ScanWithPhone({ session, onClose, onPaired }: { session: Session; onClose: () => void; onPaired?: () => void }) {
  return session.backend === "LOCAL" ? <LocalPhone onClose={onClose} onPaired={onPaired} /> : <PublicPhone session={session} onClose={onClose} />;
}

function LocalPhone({ onClose, onPaired }: { onClose: () => void; onPaired?: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [attempt, setAttempt] = useState(0);
  const [pairing, setPairing] = useState<{ pairing_id: string; expires_at: string; qr: string }>();
  const [linked, setLinked] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const modal = dialog.current;
    modal?.showModal();
    return () => modal?.close();
  }, []);
  useEffect(() => {
    let active = true;
    let id: string | undefined;
    const revoke = (value: string) => void req("DELETE", `/desktop/pairings/${encodeURIComponent(value)}`).catch(() => undefined);
    req<{ pairing_id: string; url: string; expires_at: string }>("POST", "/desktop/pairings", {body: {scope: "workspace"}})
      .then(async result => {
        id = result.pairing_id;
        if (!active) { revoke(id); return; }
        const qr = await QRCode.toDataURL(result.url, { width: 280, margin: 4, errorCorrectionLevel: "M", color: { dark: "#123E34", light: "#FFFFFF" } });
        if (active) setPairing({pairing_id: id, expires_at: result.expires_at, qr});
      }).catch(reason => { if (active) setError(reason); });
    return () => { active = false; if (id) revoke(id); };
  }, [attempt]);

  useEffect(() => {
    if (!pairing || linked) return;
    let active = true;
    const tick = setInterval(() => {
      setNow(Date.now());
      req<{state: string}>("GET", `/desktop/pairings/${encodeURIComponent(pairing.pairing_id)}`)
        .then(result => { if (active && result.state === "linked") setLinked(true); })
        .catch(() => undefined);
    }, 1400);
    return () => { active = false; clearInterval(tick); };
  }, [pairing, linked]);

  const expiresIn = pairing ? Math.max(0, Math.ceil((Date.parse(pairing.expires_at) - now) / 1000)) : 0;
  return <dialog ref={dialog} className="phone-dialog local-phone mac-pair-dialog" aria-labelledby="mac-pair-title" onCancel={onClose} onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="spread"><h2 id="mac-pair-title">{linked ? "iPhone paired" : "Connect your iPhone"}</h2><button className="btn ghost" type="button" aria-label="Close" onClick={onClose}><Icon name="x" /></button></div>
    {linked ? <div className="stack"><p role="status"><Icon name="checkCircle"/> Your iPhone now shares this workspace, including receipts and expenses.</p><button className="btn primary" onClick={onPaired ?? onClose}>{onPaired ? "Finish setup" : "Done"}</button></div> : <div className="stack">
      <p>On the same Wi-Fi, open LedgerFlow on the iPhone and tap <strong>Connect to your Mac</strong>. Scan this code to link your workspace.</p>
      {pairing && expiresIn ? <div className="mac-pair-code"><img className="pairing-qr" src={pairing.qr} alt="LedgerFlow pairing QR code"/><p className="small">Waiting for your iPhone · {expiresIn}s</p></div> :
        <p className="qr-placeholder" role="status">{error ? "A pairing code could not be created." : pairing ? "This code expired." : "Preparing your code…"}</p>}
      {error || (pairing && !expiresIn) ? <button type="button" className="btn" onClick={() => {setError(null); setPairing(undefined); setNow(Date.now()); setAttempt(n => n + 1);}}>Get a new code</button> : null}
      <ErrorNote error={error}/>
      <p className="small">This single-use code grants full access to this workspace. Use it with your own iPhone. Keep LedgerFlow running on your Mac to sync.</p>
    </div>}
  </dialog>;
}

function PublicPhone({ session, onClose }: { session: Session; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [workbooks, setWorkbooks] = useState<WorkbookView[]>([]);
  const [wid, setWid] = useState("");
  const [pairing, setPairing] = useState<Pairing | null>(null);
  const [qr, setQr] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [copied, setCopied] = useState(false);
  const pairingRef = useRef<Pairing | null>(null);
  useEffect(() => { dialog.current?.showModal(); listWorkbooks().then(r => { const ready = r.items.filter(w => w.status === "ready"); setWorkbooks(ready); setWid(ready[0]?.workbook_id ?? ""); }).catch(setError); const t = setInterval(() => setNow(Date.now()), 1000); return () => { clearInterval(t); const p = pairingRef.current; if (p) void req("DELETE", `/pairings/${encodeURIComponent(p.pairing_id)}`).catch(() => undefined); }; }, []);
  const expired = !!pairing && Date.parse(pairing.expires_at) <= now;
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
  let link = "";
  try { link = expired ? "" : pairing ? pairingLink(location.origin, pairing.fragment_token) : captureLink(location.origin, wid || undefined); } catch { /* show the HTTPS requirement below */ }
  useEffect(() => { let active = true; setQr(""); if (link) QRCode.toDataURL(link, { width: 256, margin: 3, errorCorrectionLevel: "M", color: { dark: "#0F5C4A", light: "#FFFFFF" } }).then(s => { if (active) setQr(s); }).catch(setError); return () => { active = false; }; }, [link]);
  async function createPairing() {
    setBusy(true); setError(null);
    try {
      if (pairingRef.current) await req("DELETE", `/pairings/${encodeURIComponent(pairingRef.current.pairing_id)}`);
      pairingRef.current = null; setPairing(null);
      const p = await req<Pairing>("POST", "/pairings", { body: { workbook_id: wid } });
      pairingRef.current = p;
      const duration = Date.parse(p.expires_at) - Date.now();
      if (!p.pairing_id || !p.fragment_token || !Number.isFinite(duration) || duration <= 0 || duration > 125000) throw new Error("The server did not return a valid short-lived pairing. Ask the infrastructure owner to check the pairing endpoint.");
      setPairing(p);
    } catch (e) { setError(e instanceof ApiError && [404, 405, 501].includes(e.status) ? new Error("This backend does not support temporary pairing yet. The QR below opens authenticated employee capture; it does not grant access.") : e); }
    finally { setBusy(false); }
  }
  return <dialog ref={dialog} className="phone-dialog" onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) onClose(); }}><div className="spread"><h2>Scan with iPhone</h2><button className="btn ghost" aria-label="Close" onClick={onClose}><Icon name="x" /></button></div><div className="stack">
    <p className="muted">Open your iPhone camera and scan the code. Your receipt will appear in the desktop document list automatically.</p>
    {workbooks.length ? <label>Workbook<select value={wid} disabled={!!pairing || busy} onChange={e => setWid(e.target.value)}>{workbooks.map(w => <option key={w.workbook_id} value={w.workbook_id}>{w.display_name}</option>)}</select></label> : <Callout tone="info">Connect and confirm a workbook first.</Callout>}
    {qr && link && wid && !local ? <img className="pairing-qr" src={qr} alt="QR code to open receipt capture on your iPhone" /> : null}
    {expired ? <Callout tone="warn" title="This pairing has expired.">Generate another code to continue.</Callout> : pairing ? <Callout tone="info" title={`Expires in ${Math.max(0, Math.ceil((Date.parse(pairing.expires_at) - now) / 1000))} seconds`}>Single use, upload-only workbook access. Closing this dialog requests revocation.</Callout> : <p className="small">This is an application link, not an access token. The employee signs in with their own invite. Temporary upload-only pairing requires backend support.</p>}
    {!link || local ? <Callout tone="warn">Use the public HTTPS application for phone access. A localhost link points to the phone itself.</Callout> : <button className="btn" disabled={!wid} onClick={() => navigator.clipboard.writeText(link).then(() => setCopied(true)).catch(setError)}>{copied ? "Copied" : "Copy capture link"}</button>}
    {session.role === "owner" && location.protocol === "https:" ? <button className="btn primary" disabled={!wid || busy} onClick={createPairing}>{busy ? "Generating…" : "Generate temporary upload access"}</button> : null}
    <ErrorNote error={error} />
  </div></dialog>;
}
