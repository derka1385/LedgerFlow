import type { Session } from "../lib/types";
import { useEffect, useState } from "react";
import { req } from "../lib/api";
import { Callout, ErrorNote, Icon } from "../ui";

export type Appearance = "system" | "light" | "dark";
export default function Settings({ session, appearance, setAppearance, onSignOut }: { session: Session; appearance: Appearance; setAppearance: (a: Appearance) => void; onSignOut: () => void }) {
  if (session.backend === "LOCAL") return <LocalSettings session={session} appearance={appearance} setAppearance={setAppearance} onSignOut={onSignOut}/>;
  return <div className="stack-lg settings"><div><h1>{session.role === "employee" ? "Profile" : "Settings"}</h1></div><section className="panel stack"><h2>Signed in as</h2><dl className="kv"><dt>Name</dt><dd>{session.display_name ?? session.user_id}</dd><dt>Role</dt><dd>{session.role}</dd><dt>Session expires</dt><dd>{new Date(session.expires_at).toLocaleString()}</dd></dl><div><button className="btn" onClick={onSignOut}>Sign out</button></div></section>
    <section className="panel stack"><h2>Appearance</h2><div className="segmented" aria-label="Appearance">{(["system", "light", "dark"] as const).map(a => <button key={a} aria-pressed={appearance === a} onClick={() => setAppearance(a)}>{a === "system" ? "Use device setting" : a === "light" ? "Light" : "Dark"}</button>)}</div><p className="small">Appearance is saved on this device. Financial data and credentials are not stored in local storage.</p></section>
    <section className="panel stack"><h2><Icon name="download" /> Install LedgerFlow</h2><p><strong>Mac:</strong> open the public HTTPS app in Safari, then choose Share → Add to Dock.</p><p><strong>iPhone:</strong> open it in Safari, choose Share → Add to Home Screen. Sign in with your employee invite.</p><p className="muted">The browser app has the same workflows. An internet connection is required to submit, process and approve receipts.</p></section>
    {session.role !== "employee" ? <section className="panel stack"><h2>Keyboard shortcuts</h2><dl className="kv"><dt>⌘ / Ctrl + 1–9</dt><dd>Switch workspace</dd><dt>⌘ / Ctrl + K</dt><dd>Find a document</dd><dt>⌘ / Ctrl + N</dt><dd>Submit a receipt</dd><dt>Escape</dt><dd>Close a dialog or execution monitor</dd></dl></section> : null}
    <Callout tone="info" title="One shared service">Mac, iPhone and browser use the same authenticated API. Generated accounting programs execute on the server’s isolated infrastructure.</Callout>
  </div>;
}

function LocalSettings({ session, appearance, setAppearance, onSignOut }: { session: Session; appearance: Appearance; setAppearance: (a: Appearance) => void; onSignOut: () => void }) {
  const [status,setStatus]=useState<{vision:boolean;model:string|null;docker:boolean;image_ready:boolean}|null>(null);
  const [error,setError]=useState<unknown>(null);
  const [loading,setLoading]=useState(false);
  const refresh=async()=>{setLoading(true);setError(null);try{setStatus(await req("GET","/desktop/status"));}catch(e){setError(e);}finally{setLoading(false);}};
  useEffect(()=>{void refresh();},[]);
  return <div className="stack-lg settings"><h1>Réglages</h1>
    <section className="panel stack"><h2>Votre espace local</h2><p>Les classeurs, les pièces et la conversation sont conservés sur votre Mac. Le modèle de vision utilise le service Vultr configuré pour ce projet.</p><p className="muted">Fermer la fenêtre laisse LedgerFlow actif en arrière-plan. Quitter l’application ou mettre le Mac en veille interrompt l’accès depuis l’iPhone.</p></section>
    <section className="panel stack"><h2>Mac et iPhone</h2><p>Ouvrez l’application LedgerFlow sur l’iPhone, puis <strong>Associer mon Mac</strong>. Scannez le code proposé sur le Mac avec « Scan with iPhone ».</p><p className="muted">Les deux appareils doivent être sur le même réseau. L’adresse du serveur est transmise dans le code, avec l’identité chiffrée du Mac. Aucune invitation de démonstration n’est nécessaire.</p></section>
    <section className="panel stack"><h2>Connexion du modèle</h2><dl className="kv"><dt>Vision</dt><dd>{status ? status.vision ? `${status.model} · configuré` : "Non configurée" : "Vérification…"}</dd><dt>Exécution isolée</dt><dd>{status ? status.docker && status.image_ready ? "Docker prêt" : "Docker Desktop ou son image doit être démarré" : "Vérification…"}</dd></dl><button className="btn" disabled={loading} onClick={()=>void refresh()}><Icon name="refresh"/>{loading ? "Vérification…" : "Vérifier l’état du moteur"}</button><ErrorNote error={error}/>
      <details><summary>Aide à la configuration sur le Mac</summary><div className="stack" style={{paddingTop:12}}><p>Si la vision n’est pas configurée, le responsable du Mac doit renseigner sa clé Vultr dans le fichier local <code>.env</code> du projet, sous <code>VULTR_INFERENCE_API_KEY</code>, puis quitter et rouvrir LedgerFlow. Le modèle est choisi dans <code>config/inference.json</code>.</p><p>Si l’exécution n’est pas prête, ouvrez Docker Desktop sur le Mac. L’image de sandbox attendue est <code>python:3.12-slim</code>. Aucun programme comptable ne sera exécuté hors de cette isolation.</p><p className="small">Ne collez jamais de clé dans la conversation, une adresse de serveur ou un code QR. Cette page n’affiche ni ne modifie la clé.</p></div></details>
    </section>
    <section className="panel stack"><h2>Apparence</h2><div className="segmented" aria-label="Appearance">{(["system","light","dark"] as const).map(a=><button key={a} aria-pressed={appearance===a} onClick={()=>setAppearance(a)}>{a==="system"?"Comme l’appareil":a==="light"?"Clair":"Sombre"}</button>)}</div></section>
    <section className="panel stack"><h2>Cette session</h2><p>{session.role === "employee" ? "Capture de pièces, sans droit d’approbation." : "Accès au dossier et aux validations de votre espace."}</p><p className="small">Une session fermée se rouvre en relançant l’application Mac, ou en associant de nouveau l’iPhone.</p><button className="btn" onClick={onSignOut}>Fermer cette session</button></section>
  </div>;
}
