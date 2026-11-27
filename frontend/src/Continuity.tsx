import { useEffect, useRef, useState } from "react";
import QRCode from "qrcode";
import { ApiError, listWorkbooks, req } from "./lib/api";
import { captureLink, pairingLink } from "./lib/experience";
import type { Session, WorkbookView } from "./lib/types";
import { Callout, ErrorNote, Icon } from "./ui";

interface Pairing { pairing_id: string; fragment_token: string; expires_at: string }

export function ScanWithPhone({ session, onClose }: { session: Session; onClose: () => void }) {
  return session.backend === "LOCAL" ? <LocalPhone onClose={onClose} /> : <PublicPhone session={session} onClose={onClose} />;
}

function LocalPhone({ onClose }: { onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [scope, setScope] = useState("workspace");
  const [pairing, setPairing] = useState<{ pairing_id: string; url: string; expires_at: string } | null>(null);
  const current = useRef<string | null>(null);
  const [qr, setQr] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [now, setNow] = useState(Date.now());
  const alive = useRef(true);
  const revoke = (id: string) => req("DELETE", `/desktop/pairings/${encodeURIComponent(id)}`).catch(() => undefined);
  async function generate(mode = scope) {
    setBusy(true); setError(null); setQr(""); setPairing(null);
    try {
      if (current.current) await revoke(current.current);
      const p = await req<{ pairing_id: string; url: string; expires_at: string }>("POST", "/desktop/pairings", { body: { scope: mode } });
      if (!alive.current) { void revoke(p.pairing_id); return; }
      current.current = p.pairing_id;
      setPairing(p);
      setQr(await QRCode.toDataURL(p.url, { width: 280, margin: 3, color: { dark: "#123E34", light: "#FFFFFF" } }));
    } catch (e) { if (alive.current) setError(e); }
    finally { if (alive.current) setBusy(false); }
  }
  useEffect(() => {
    alive.current = true; dialog.current?.showModal();
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => { alive.current = false; clearInterval(timer); if (current.current) void revoke(current.current); };
  }, []);
  const expired = !!pairing && Date.parse(pairing.expires_at) <= now;
  return <dialog ref={dialog} className="phone-dialog local-phone" onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) onClose(); }}><div className="spread"><h2>Votre iPhone, relié au Mac.</h2><button className="btn ghost" aria-label="Fermer" onClick={onClose}><Icon name="x" /></button></div><div className="stack">
    <p>Sur votre iPhone, ouvrez LedgerFlow et touchez <strong>Associer mon Mac</strong>. Scannez ensuite ce code, sur le même Wi-Fi.</p>
    <fieldset className="phone-scope"><legend>Ce que l’iPhone peut faire</legend>{[["workspace", "Retrouver tout mon espace", "Agent, dossiers et validations"], ["capture", "Scanner des pièces uniquement", "Aucun droit de validation"]].map(([key,label,detail]) => <label key={key}><input type="radio" name="phone-scope" checked={scope === key} disabled={busy} onChange={() => { setScope(key); setPairing(null); setQr(""); if (current.current) { void revoke(current.current); current.current = null; } }} /><span><strong>{label}</strong><small>{detail}</small></span></label>)}</fieldset>
    {qr && !expired ? <img className="pairing-qr" src={qr} alt="Code d’association à scanner dans LedgerFlow sur iPhone" /> : <div className="qr-placeholder"><Icon name="phone" /><span>{busy ? "Préparation du code…" : expired ? "Ce code a expiré." : "Générez un code pour associer votre iPhone."}</span></div>}
    <button className="btn primary" disabled={busy} onClick={() => void generate()}>{busy ? "Préparation…" : pairing ? "Générer un nouveau code" : "Afficher le code d’association"}</button>
    {pairing && !expired ? <p className="small">Utilisable une fois · expire dans {Math.max(0, Math.ceil((Date.parse(pairing.expires_at)-now)/1000))} s</p> : null}
    <p className="small">La connexion est chiffrée et associée à ce Mac. Gardez LedgerFlow actif et le Mac éveillé pour synchroniser les dossiers. Fermer cette fenêtre révoque le code inutilisé.</p><ErrorNote error={error} />
  </div></dialog>;
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
