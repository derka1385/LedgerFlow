import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { adoptSession, currentSession, isLocalBackend, isMockBackend, req, signOut } from "./lib/api";
import type { Session } from "./lib/types";
import { BrandMark, Wordmark } from "./Brand";
import { ErrorNote, Icon, Skeleton } from "./ui";
import { ScanWithPhone } from "./Continuity";
import Login from "./pages/Login";
import Capture from "./pages/Capture";
import Onboarding from "./pages/Onboarding";
import Overview from "./pages/Overview";
import MacSignIn from "./MacSignIn";
import MacSetupFlow from "./MacSetupFlow";
import { WorkbookChecks } from "./pages/MacFinance";
import ExpensesTracker from "./pages/ExpensesTracker";
import Agent from "./pages/Agent";
import Transactions from "./pages/Transactions";
import Versions from "./pages/Versions";
import Security from "./pages/Security";
import { ExpenseDetail, ExpenseHistory } from "./pages/Employee";
import Settings, { type Appearance } from "./pages/Settings";
import Home from "./pages/Home";
import Explainer from "./Explainer";
import { MacReceipt, MacIntro, WorkspaceSetup, sourceName, type WorkspaceProfile } from "./MacWorkspace";
import { LANGS, useT } from "./lib/i18n";

export function useHashRoute(): string[] {
  const read = () => (window.location.hash.replace(/^#\/?/, "").split("?")[0] || "").split("/").filter(Boolean);
  const [parts, setParts] = useState(read);
  useEffect(() => { const on = () => setParts(read()); window.addEventListener("hashchange", on); return () => window.removeEventListener("hashchange", on); }, []);
  return parts;
}
export const go = (path: string) => { window.location.hash = `#/${path}`; };
const FINANCE_NAV = [["agent", "Agent", "message"], ["overview", "Overview", "overview"], ["transactions", "Transactions", "transactions"], ["receipts", "Receipts", "file"], ["workbook", "Excel Workbooks", "grid"], ["activity", "Agent Activity", "terminal"], ["security", "Security", "shield"], ["audit", "Audit History", "clock"], ["settings", "Settings", "settings"]];
const MAC_NAV = [["agent", "Agent", "message"], ["overview", "Dashboard", "overview"], ["receipts", "Receipts", "file"], ["expenses", "Expenses", "transactions"], ["workbook", "Workbooks", "grid"], ["security", "Workbook checks", "shield"], ["activity", "Activity", "terminal"], ["audit", "Audit history", "clock"]];
const EMPLOYEE_NAV = [["home", "Home", "overview"], ["capture", "Scan", "camera"], ["expenses", "Expenses", "file"], ["requests", "Requests", "flag"], ["profile", "Profile", "user"]];
const PHONE_OWNER_NAV = [["home", "nav.home", "overview"], ["agent", "nav.agent", "message"], ["capture", "nav.capture", "camera"], ["overview", "nav.files", "file"], ["settings", "nav.settings", "settings"]];
const isPhone = () => typeof matchMedia !== "undefined" && matchMedia("(max-width: 760px)").matches;
const HOW_SEEN = "ledgerflow.howSeen";

export function LangSwitch() {
  const [t, lang, setLang] = useT();
  return <div className="lang-switch" role="group" aria-label={t("shell.language")}>{LANGS.map(l => <button key={l.id} type="button" lang={l.id} aria-pressed={lang === l.id} title={l.label} onClick={() => setLang(l.id)}>{l.short}</button>)}</div>;
}

type NativeConnection = { session: Session; profile?: WorkspaceProfile | null };
const connectionPromises = new Map<string, Promise<NativeConnection>>();
function NativeConnectionGate({ token, bootstrap, onSignedIn }: {
  token: string; bootstrap: boolean; onSignedIn: (s: Session, profile?: WorkspaceProfile | null) => void;
}) {
  const [error, setError] = useState<unknown>(null);
  const [connection, setConnection] = useState<NativeConnection>();
  const [intro, setIntro] = useState<"holding" | "ready" | "done">(bootstrap ? "holding" : "done");
  const handedOff = useRef(false);
  useEffect(() => {
    let active = true;
    history.replaceState(null, "", "/");
    const key = `${bootstrap}:${token}`;
    let promise = connectionPromises.get(key);
    if (!promise) {
      promise = req<Session>("POST", bootstrap ? "/desktop/bootstrap" : "/desktop/pairings/exchange", { body: { token: decodeURIComponent(token) } })
        .then(async session => {
          if (!bootstrap || window.location.hostname !== "127.0.0.1") return { session };
          try {
            const { profile } = await req<{ profile: WorkspaceProfile | null }>("GET", "/desktop/workspace-profile");
            return { session, profile };
          } catch { return { session }; }
        });
      connectionPromises.set(key, promise);
    }
    promise.then(result => { if (active) setConnection(result); }).catch(e => { if (active) setError(e); });
    const motion = matchMedia("(prefers-reduced-motion: reduce)");
    const useMotionPreference = () => { if (motion.matches) setIntro("done"); };
    useMotionPreference();
    motion.addEventListener("change", useMotionPreference);
    return () => { active = false; motion.removeEventListener("change", useMotionPreference); };
  }, [token, bootstrap]);
  useLayoutEffect(() => {
    if (connection && intro === "done" && !handedOff.current) {
      handedOff.current = true;
      adoptSession(connection.session);
      onSignedIn(connection.session, connection.profile);
    }
  }, [connection, intro, onSignedIn]);
  if (bootstrap && !error) return <MacIntro
    leaving={intro === "ready" && !!connection}
    waiting={intro === "done"}
    onHoldEnd={() => setIntro(phase => phase === "holding" ? "ready" : phase)}
    onSkip={() => setIntro("done")}
    onExit={() => setIntro("done")}/>;
  return <main className="native-connection"><BrandMark size={64} /><h1>{error ? "The connection failed." : bootstrap ? "Your agent is on its way…" : "Pairing with your Mac…"}</h1>{error ? <><ErrorNote error={error} /><p>Reopen the Mac app or scan a new code.</p></> : <p>Your workspace opens automatically.</p>}</main>;
}

function PairingGate({ token, onSignedIn }: { token: string; onSignedIn: (s: Session) => void }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState<unknown>(null);
  async function exchange() {
    setBusy(true); setError(null);
    try { const session = await req<Session>("POST", "/pairings/exchange", { body: { token: decodeURIComponent(token) } }); adoptSession(session); history.replaceState(null, "", "/#/capture"); onSignedIn(session); }
    catch (e) { setError(e); } finally { setBusy(false); }
  }
  return <main className="narrow stack-lg"><BrandMark size={56} /><h1>Send a receipt to finance.</h1><p>This temporary link opens an upload-only session for the selected company workbook. It cannot approve accounting entries.</p><button className="btn primary big" disabled={busy} onClick={exchange}>{busy ? "Connecting…" : "Continue to receipt capture"}</button><ErrorNote error={error} /><a href="#/">Use my own invite instead</a></main>;
}

export default function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [profile, setProfile] = useState<WorkspaceProfile | null | undefined>();
  const [profileError, setProfileError] = useState<unknown>(null);
  const [revealDashboard, setRevealDashboard] = useState(false);
  const [authError, setAuthError] = useState<unknown>(null);
  const [scan, setScan] = useState(false), [menu, setMenu] = useState(false);
  const [sidebarHidden, setSidebarHidden] = useState(false);
  const [compactSidebar, setCompactSidebar] = useState(() => matchMedia("(max-width: 900px)").matches);
  useEffect(() => {
    const media = matchMedia("(max-width: 900px)");
    const update = () => setCompactSidebar(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  const [online, setOnline] = useState(navigator.onLine);
  const [appearance, updateAppearance] = useState<Appearance>(() => { try { const v = localStorage.getItem("ledgerflow.appearance"); return v === "light" || v === "dark" ? v : "system"; } catch { return "system"; } });
  const route = useHashRoute();
  const [t] = useT();
  const finance = !!session && session.role !== "employee";
  const mac = session?.backend === "LOCAL" && session.role === "owner" && window.location.hostname === "127.0.0.1";
  const loadProfile = () => {
    setProfileError(null);
    req<{profile: WorkspaceProfile | null}>("GET", "/desktop/workspace-profile").then(result => setProfile(result.profile)).catch(setProfileError);
  };
  useEffect(() => { if (mac && profile === undefined) loadProfile(); }, [mac, profile]);
  const aliases: Record<string, string> = { inbox: "transactions", runs: "transactions", versions: "workbook" };
  const page = route[0] ?? (mac ? "agent" : session?.backend === "LOCAL" ? "agent" : finance ? "overview" : "home");
  const resolvedPage = aliases[page] ?? page;
  const activePage = mac && resolvedPage === "transactions" ? "receipts" : resolvedPage;
  const loadSession = () => { setAuthError(null); currentSession().then(setSession).catch(setAuthError); };
  useEffect(() => { if (!["bootstrap", "associate", "pair"].includes(route[0])) loadSession(); }, []);
  useEffect(() => {
    if (!session) return;
    const remaining = Date.parse(session.expires_at) - Date.now();
    if (!Number.isFinite(remaining)) return;
    const expire = () => { setSession(null); setScan(false); };
    if (remaining <= 0) { expire(); return; }
    const timer = window.setTimeout(expire, Math.min(remaining, 2147483647));
    return () => clearTimeout(timer);
  }, [session]);
  useEffect(() => {
    document.documentElement.dataset.appearance = appearance;
    const media = matchMedia("(prefers-color-scheme: dark)");
    const sync = () => document.querySelector('meta[name="theme-color"]')?.setAttribute("content", appearance === "dark" || (appearance === "system" && media.matches) ? "#171c19" : "#FCFCFA");
    sync(); media.addEventListener("change", sync); return () => media.removeEventListener("change", sync);
  }, [appearance]);
  useEffect(() => { setMenu(false); setScan(false); }, [page]);
  useEffect(() => { if (page === "overview") return () => setRevealDashboard(false); }, [page]);
  useEffect(() => {
    if (!session || mac || !isPhone() || page === "how" || page === "capture") return;
    let seen = "1"; try { seen = localStorage.getItem(HOW_SEEN) ?? ""; } catch { /* no storage: do not loop */ }
    if (!seen) go("how");
  }, [session?.user_id, mac]);
  const finishHow = () => { try { localStorage.setItem(HOW_SEEN, "1"); } catch { /* fine */ } go(isPhone() ? "home" : finance ? "agent" : "home"); };
  useEffect(() => { const up = () => setOnline(true), down = () => setOnline(false), expired = () => { setSession(null); setScan(false); }; window.addEventListener("online", up); window.addEventListener("offline", down); window.addEventListener("ledgerflow:unauthenticated", expired); return () => { window.removeEventListener("online", up); window.removeEventListener("offline", down); window.removeEventListener("ledgerflow:unauthenticated", expired); }; }, []);
  useEffect(() => {
    if (!finance) return;
    const key = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey) || e.altKey || (e.target instanceof HTMLElement && (e.target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)))) return;
      if (/^[1-9]$/.test(e.key)) { const shortcut = (mac ? MAC_NAV : FINANCE_NAV)[Number(e.key) - 1]; if (shortcut) { e.preventDefault(); go(shortcut[0]); } }
      if (e.key.toLowerCase() === "n") { e.preventDefault(); go("capture"); }
      if (e.key.toLowerCase() === "k") { e.preventDefault(); if (!document.getElementById("workspace-search")) go(mac ? "receipts" : "transactions"); setTimeout(() => document.getElementById("workspace-search")?.focus(), 100); }
    };
    window.addEventListener("keydown", key); return () => window.removeEventListener("keydown", key);
  }, [finance, mac]);
  async function logout() { try { await signOut(); setSession(null); setScan(false); go(""); } catch (e) { setAuthError(e); } }
  const signedIn = (s: Session, preparedProfile?: WorkspaceProfile | null) => {
    setSession(s);
    if (preparedProfile !== undefined) setProfile(preparedProfile);
    if (page === "bootstrap") setRevealDashboard(true);
    if (page !== "capture" && page !== "pair") go(s.backend === "LOCAL" ? (s.role === "employee" && page === "associate" ? "capture" : "agent") : s.role === "employee" ? "home" : "overview");
  };
  const setAppearance = (value: Appearance) => { updateAppearance(value); try { localStorage.setItem("ledgerflow.appearance", value); } catch { /* preference still applies */ } };
  // The Mac opens on its own sign-in screen (accounts), not an automatic session.
  if (page === "bootstrap") return session ? null : <IntroThenSignIn launchToken={route[1]} onSignedIn={signedIn} />;
  if (page === "associate" && route[1]) return <NativeConnectionGate token={route[1]} bootstrap={false} onSignedIn={signedIn} />;
  if (page === "pair" && route[1]) return <PairingGate token={route[1]} onSignedIn={signedIn} />;
  if (authError && session === undefined) return <main className="narrow stack-lg"><BrandMark size={48} /><h1>Connect to your workspace.</h1><ErrorNote error={authError} /><button className="btn" onClick={loadSession}>Try again</button></main>;
  if (session === undefined) return <main className="narrow"><Skeleton /></main>;
  if (!session && isLocalBackend() && location.hostname === "127.0.0.1") return <MacSignIn onSignedIn={signedIn} />;
  if (!session && isLocalBackend()) return <main className="native-connection"><BrandMark size={64}/><h1>You are signed out.</h1><p>On iPhone, tap the gear and pair with your Mac again.</p><p className="muted">Your files and approved entries stay saved on the Mac.</p></main>;
  if (!session) return <Login onSignedIn={signedIn} />;
  if (mac && profileError) return <main className="narrow stack"><h1>Open your workspace</h1><ErrorNote error={profileError}/><button className="btn" onClick={loadProfile}>Try again</button></main>;
  if (mac && profile === undefined) return <main className="narrow"><Skeleton /></main>;
  if (mac && (!profile?.agent_name || page === "workspace-profile")) return <WorkspaceSetup key={profile ? "edit" : "create"} profile={profile ?? null}
    onSave={next => { setProfile(next); go(profile ? profile.agent_name ? "settings" : "agent" : "connect-workspace"); }} onCancel={profile?.agent_name ? () => go("settings") : undefined}/>;
  const label = (path: string) => mac ? MAC_NAV.find(([id]) => id === path)?.[1] ?? (path === "settings" ? "Account & settings" : t(`nav.${path}`)) : t(`nav.${path}`);
  if (mac && profile && (page === "connect-workspace" || (profile.setup_step && profile.setup_step !== "complete"))) {
    return <MacSetupFlow session={session} profile={profile} onChange={next => {
      setProfile(next);
      if (next.setup_step === "complete") go("agent");
    }}/>;
  }
  let body;
  if (page === "how") body = <Explainer onDone={finishHow} />;
  else if (page === "home") body = <Home session={session} />;
  else if (page === "agent") body = <Agent session={session} agentName={mac ? profile?.agent_name ?? "LedgerFlow" : undefined} onPhone={mac ? () => go("settings") : () => setScan(true)} />;
  else if (page === "capture") body = <Capture session={session} mac={mac} />;
  else if (page === "settings" || page === "profile") body = <Settings session={session} appearance={appearance} setAppearance={setAppearance} onSignOut={logout} mac={mac} onPhone={() => setScan(true)} />;
  else if (!finance && page === "expenses" && route[1]) body = <ExpenseDetail key={route[1]} id={route[1]} />;
  else if (!finance && (page === "expenses" || page === "requests")) body = <ExpenseHistory questionsOnly={page === "requests"} />;
  else if (!finance) body = <Home session={session} />;
  else if (page === "workbook") body = <div className="stack-lg"><div className="tabs"><a className="btn ghost" href={`#/workbook${route[1] ? `/${route[1]}` : ""}`} aria-current="page">Structure & accounts</a><a className="btn ghost" href={`#/versions${route[1] ? `/${route[1]}` : ""}`}>Version history</a></div><Onboarding key={route[1] ?? "latest"} session={session} workbookId={route[1]} /></div>;
  else if (page === "versions") body = <div className="stack-lg"><a href="#/workbook">Back to workbook structure</a><Versions key={route[1] ?? "latest"} workbookId={route[1]} /></div>;
  else if (mac && page === "expenses") body = <ExpensesTracker />;
  else if (page === "security") body = mac ? <WorkbookChecks /> : <Security />;
  else if (["transactions", "inbox", "runs", "receipts", "activity", "audit"].includes(page)) body = <Transactions key={page} session={session} selected={route[1]} mode={activePage} />;
  else body = <Overview mac={mac} workspace={profile?.name} reveal={mac && revealDashboard} />;
  const nav = mac ? MAC_NAV : finance ? FINANCE_NAV : EMPLOYEE_NAV;
  return <div className={`app-shell ${finance ? "finance-shell" : "employee-shell"} ${menu ? "sidebar-open" : ""} ${mac ? `mac-shell${sidebarHidden ? " mac-sidebar-hidden" : ""}` : ""}`}>
    <a href="#main-content" className="skip-link" onClick={e => { e.preventDefault(); document.getElementById("main-content")?.focus(); }}>Skip to content</a>
    {finance ? <aside id="workspace-sidebar" className="sidebar">
      <a className="brand" href="#/agent">{mac ? <MacReceipt size={30}/> : <BrandMark size={34} />}<Wordmark /></a>
      {mac && profile ? <a className="mac-company" href="#/workspace-profile"><Icon name="box"/><span><strong>{profile.name}</strong><small>{sourceName(profile.source)}</small></span><Icon name="settings"/></a> : <p className="sidebar-label">{t("shell.workspace")}</p>}
      <nav aria-label="Main">{nav.map(([p, , icon]) =>
        <a key={p} href={`#/${p}`} className={p === "agent" && mac ? "mac-agent-nav" : p === (mac ? "workbook" : "security") ? "nav-group-start" : undefined} aria-current={activePage === p ? "page" : undefined}>
          <Icon name={icon} /><span>{label(p)}{mac && p === "agent" && profile?.agent_name ? <small>{profile.agent_name}</small> : null}</span></a>)}</nav>
      <div className="sidebar-foot"><a href="#/settings"><span className="account-avatar"><Icon name="user" /></span><span><strong>{mac ? "Account & settings" : session.display_name ?? session.role}</strong><small>{mac ? "Local profile" : t("shell.account")}</small></span></a><button type="button" className="sidebar-signout" onClick={() => void logout()} aria-label="Sign out"><Icon name="logout" /><span>Sign out</span></button></div>
    </aside> : null}
    <div className="app-body"><header className="workspace-toolbar"><div className="toolbar-location">{finance ? <button className="btn ghost menu-toggle" aria-label="Toggle sidebar" aria-controls="workspace-sidebar" aria-expanded={mac && !compactSidebar ? !sidebarHidden : menu} onClick={() => { if (mac && !compactSidebar) setSidebarHidden(v => !v); else setMenu(v => !v); }}><Icon name="menu" /></button> : <a className="brand" href="#/home"><BrandMark /><Wordmark /></a>}{finance ? <><span className="muted">{t("shell.workspace")}</span><span className="toolbar-slash">/</span><strong>{nav.some(n => n[0] === activePage) ? label(activePage) : activePage === "how" ? t("how.title") : activePage === "home" ? t("nav.home") : t("nav.capture")}</strong></> : null}</div><div className="row">{!mac ? <LangSwitch /> : <a href="#/capture" className="btn mac-new-receipt"><Icon name="upload"/>Add receipt</a>}{finance && !mac ? <><button className="btn phone-association-action" onClick={() => setScan(true)}><Icon name="phone" /><span>{t("shell.scanIphone")}</span></button>{session.backend === "LOCAL" ? <a className="btn phone-direct-capture" href="#/capture"><Icon name="camera"/>Scanner</a> : null}</> : null}<a className="account-button" href={finance ? "#/settings" : "#/profile"} aria-label="Account settings"><Icon name="user" /><span>{session.display_name ?? session.role}</span></a></div></header>
    {session.backend === "DEV-MOCK" || isMockBackend() ? <details className="mockbar" role="note"><summary><Icon name="alert" /><span>Development environment <span className="environment-separator">/</span> {session.inference === "vultr" ? "Vultr inference" : "Mock inference"}</span></summary><p>Execution, verification and approval follow the development service. This is not the public Vultr deployment.</p></details> : null}
    {!online ? <div className="offline-banner" role="status">You’re offline. Reconnect to upload receipts or change your workbook. No financial actions are queued.</div> : null}
    <main id="main-content" tabIndex={-1} className={finance ? (page === "capture" ? "workspace-content capture-content" : "workspace-content") : "employee-content"}><ErrorNote error={authError} />{body}</main></div>
    {!finance ? <nav className="employee-tabs" aria-label="Main">{nav.map(([p, , icon]) => <a key={p} href={`#/${p}`} aria-current={activePage === p ? "page" : undefined}><Icon name={icon} /><span>{t(`nav.${p}`)}</span></a>)}</nav> : session.backend === "LOCAL" && !mac ? <nav className="mobile-finance-tabs" aria-label="iPhone">{PHONE_OWNER_NAV.map(([p, key, icon]) => <a key={p} href={`#/${p}`} aria-current={activePage === p ? "page" : undefined}><Icon name={icon}/><span>{t(key)}</span></a>)}</nav> : null}
    {scan ? <ScanWithPhone session={session} onClose={() => setScan(false)} /> : null}
  </div>;
}


/** Mac launch: the brand intro (waves, receipt, wordmark) plays, then hands over to the sign-in screen. */
function IntroThenSignIn({ onSignedIn, launchToken }: { onSignedIn: (s: Session) => void; launchToken?: string }) {
  const [token] = useState(launchToken);
  useEffect(() => { if (token) history.replaceState(null, "", "/#/bootstrap"); }, [token]);
  const [phase, setPhase] = useState<"holding" | "leaving" | "signin">(() => matchMedia("(prefers-reduced-motion: reduce)").matches ? "signin" : "holding");
  if (phase === "signin") return <MacSignIn launchToken={token} onSignedIn={onSignedIn} />;
  return <MacIntro leaving={phase === "leaving"} waiting={false}
    onHoldEnd={() => setPhase("leaving")} onSkip={() => setPhase("signin")} onExit={() => setPhase("signin")} />;
}
