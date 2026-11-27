import { useEffect, useRef, useState } from "react";
import { listRuns, listWorkbooks, newIdempotencyKey, req } from "../lib/api";
import { ATTENTION_STATES } from "../lib/experience";
import { money } from "../lib/format";
import { usePolling } from "../lib/usePolling";
import type { Session } from "../lib/types";
import { MacReceipt } from "../MacWorkspace";
import { BrandMark } from "../Brand";
import { ErrorNote, Icon, StatePill } from "../ui";
import { useT } from "../lib/i18n";

interface Message { id: string; role: "user" | "assistant"; text: string; actions: string[]; created_at: string; model?: string }
interface RuntimeStatus { vision: boolean; model: string | null; docker: boolean; image_ready: boolean; persistent: boolean; phone_available: boolean }
const ACTIONS: Record<string, [string, string, string]> = {
  capture: ["Add a receipt", "camera", "capture"], workbook: ["Connect my Excel", "grid", "workbook"],
  transactions: ["Review receipts", "file", "transactions"], activity: ["See the agent’s work", "terminal", "activity"],
  overview: ["Ouvrir les dossiers", "overview", "overview"], phone: ["Associer mon iPhone", "phone", ""],
};

export default function Agent({ session, onPhone, agentName }: { session: Session; onPhone: () => void; agentName?: string }) {
  const [t, lang] = useT();
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [optimistic, setOptimistic] = useState("");
  const pendingKey = useRef(newIdempotencyKey("chat"));
  const lastText = useRef("");
  const end = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const finance = session.role !== "employee";
  const { data, error: loadError } = usePolling(async () => {
    const [runs, books] = await Promise.all([listRuns(), listWorkbooks()]);
    const status = session.backend === "LOCAL" ? await req<RuntimeStatus>("GET", "/desktop/status") : null;
    return { runs: runs.items, books: books.items, status };
  }, 8000);
  useEffect(() => {
    let active = true;
    const load = () => req<{ items: Message[] }>("GET", "/assistant/messages").then(r => { if (active) setMessages(r.items); }).catch(e => { if (active && session.backend === "LOCAL") setError(e); });
    void load(); const timer = setInterval(load, 5000);
    return () => { active = false; clearInterval(timer); };
  }, [session.user_id]);
  useEffect(() => { if (messages.length || sending) end.current?.scrollIntoView({ block: "nearest", behavior: "auto" }); }, [messages.length, sending]);

  async function send(value = text) {
    const cleaned = value.trim();
    if (!cleaned || sending) return;
    if (lastText.current !== cleaned) pendingKey.current = newIdempotencyKey("chat");
    lastText.current = cleaned;
    setSending(true); setError(null); setOptimistic(cleaned);
    try {
      const result = await req<{ items: Message[] }>("POST", "/assistant/messages", { body: { text: cleaned, language: lang }, idempotencyKey: pendingKey.current });
      setMessages(previous => [...new Map([...previous, ...result.items].map(m => [m.id, m])).values()]);
      setText(""); pendingKey.current = newIdempotencyKey("chat"); lastText.current = "";
    } catch (e) { setError(e); setText(cleaned); }
    finally { setSending(false); setOptimistic(""); input.current?.focus(); }
  }
  function action(key: string) {
    if (key === "phone") { onPhone(); return; }
    const target = ACTIONS[key]?.[2]; if (target) location.hash = `#/${target}`;
  }
  const books = data?.books ?? [], runs = data?.runs ?? [];
  const ready = runs.filter(r => r.state === "AWAITING_APPROVAL");
  const attention = runs.filter(r => ATTENTION_STATES.includes(r.state));
  const hasBook = books.some(w => w.status === "ready");
  const status = data?.status;
  return <div className="agent-workspace">
    <section className="conversation" aria-label={t("agent.conversation")}>
      <header className="conversation-header"><div><h1>{agentName || t("agent.title")}</h1><p>{t("agent.sub")}</p></div><span className={`agent-availability ${status?.vision || session.inference === "vultr" ? "available" : ""}`} title={status?.model ?? t("agent.noModel")}><span />{status?.vision || session.inference === "vultr" ? t("agent.vision") : t("agent.checkConn")}</span></header>
      <div className={`conversation-flow ${messages.length ? "has-messages" : ""}`}>
        {data && !messages.length && !sending ? <div className="agent-welcome">{agentName ? <MacReceipt size={58}/> : <BrandMark size={56} />}<h2>{hasBook ? t("agent.welcomeReady") : t("agent.welcomeStart")}</h2><p>{hasBook ? t("agent.welcomeReadyBody") : t("agent.welcomeStartBody")}</p><div className="agent-starters">{(hasBook ? ["capture", ...(finance && !agentName ? ["phone"] : [])] : finance ? ["workbook", ...(!agentName ? ["phone"] : [])] : ["capture"]).map(key => <button key={key} className={`btn ${key === "phone" ? "agent-phone-action" : ""}`} onClick={() => action(key)}><Icon name={ACTIONS[key][1]} />{t(`agent.a.${key}`)}<Icon name="arrow" /></button>)}</div><div className="agent-guide-links"><button className="conversation-prompt" disabled={sending} onClick={() => send(t("agent.explainPrompt"))}>{t("agent.explain")}<Icon name="arrow" /></button><a className="conversation-prompt" href="#/how">{t("home.how")}<Icon name="play" /></a></div></div> : null}
        {messages.map(m => <article className={`agent-message ${m.role}`} key={m.id}><div className="message-author">{m.role === "assistant" ? (agentName ? <MacReceipt size={22}/> : <BrandMark size={22} />) : <Icon name="user" />}<strong>{m.role === "assistant" ? agentName ?? "LedgerFlow" : t("agent.you")}</strong><time>{new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit" }).format(new Date(m.created_at))}</time></div><p>{m.text}</p>{m.actions.length ? <div className="message-actions">{m.actions.filter(a => ACTIONS[a]).map(a => <button className={`btn ${a === "phone" ? "agent-phone-action" : ""}`} key={a} onClick={() => action(a)}><Icon name={ACTIONS[a][1]} />{t(`agent.a.${a}`)}</button>)}</div> : null}</article>)}
        {sending ? <><article className="agent-message user pending"><div className="message-author"><Icon name="user" /><strong>{t("agent.you")}</strong></div><p>{optimistic}</p></article><div className="agent-thinking" role="status">{agentName ? <MacReceipt size={22}/> : <BrandMark size={22} />}<span>{t("agent.thinking")}</span></div></> : null}
        <ErrorNote error={error ?? loadError} /><div ref={end} />
      </div>
      <form className="agent-composer" onSubmit={e => { e.preventDefault(); void send(); }}><label className="sr-only" htmlFor="agent-message">{t("agent.messageLabel")}</label><textarea ref={input} id="agent-message" placeholder={t("agent.placeholder")} rows={2} maxLength={3000} value={text} disabled={sending} onChange={e => setText(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); } }} /><div className="composer-tools"><button className="btn ghost" type="button" onClick={() => action("capture")}><Icon name="upload" /><span>{t("agent.attach")}</span></button><span className="composer-hint">{t("agent.enter")}</span><button className="send-message" aria-label="Send message" disabled={!text.trim() || sending}><Icon name="arrow" /></button></div></form>
      <p className="agent-approval-note"><Icon name="shield" />{t("agent.note")}</p>
    </section>
    <aside className="agent-dossier" aria-label={t("agent.dossier")}>
      <div className="dossier-title"><h2>{t("agent.dossier")}</h2><a href="#/overview" aria-label={t("agent.openFile")}><Icon name="arrow" /></a></div>
      <section className="dossier-ledger"><div className="dossier-section-label"><Icon name="grid" /><h3>{t("agent.workbook")}</h3></div>{books.length ? books.map(w => <a href={`#/workbook/${w.workbook_id}`} className="dossier-workbook" key={w.workbook_id}><strong>{w.display_name}</strong><span>{w.status === "ready" ? t("agent.ready") : t("agent.structure")} · v{w.version_count}</span></a>) : data ? <><p>{t("agent.noWorkbook")}</p><a className="dossier-link" href="#/workbook">{t("agent.a.workbook")}<Icon name="arrow" /></a></> : null}</section>
      <section className="dossier-decisions"><div className="dossier-section-label"><Icon name="checkCircle" /><h3>{t("agent.attention")}</h3><span>{ready.length + attention.length}</span></div>{ready.length + attention.length ? [...ready,...attention].slice(0,4).map(r => <a className="dossier-document" href={`#/transactions/${r.run_id}`} key={r.run_id}><span><strong>{r.merchant_name ?? t("agent.toReview")}</strong><StatePill state={r.state} /></span><span>{money(r.gross_minor)}</span></a>) : <p>{t("agent.noDecisions")}</p>}</section>
      <section className="dossier-recent"><div className="dossier-section-label"><Icon name="file" /><h3>{t("agent.recent")}</h3><span>{runs.length}</span></div>{runs.length ? runs.slice(0,4).map(r => <a href={`#/${finance ? "transactions" : "expenses"}/${r.run_id}`} className="dossier-document" key={r.run_id}><span><strong>{r.merchant_name ?? t("agent.reading")}</strong><StatePill state={r.state} /></span><Icon name="arrow" /></a>) : <p>{t("agent.noReceipts")}</p>}</section>
      {finance && !agentName ? <button className="dossier-phone" onClick={onPhone}><Icon name="phone" /><span><strong>{t("agent.phoneTitle")}</strong><span>{t("agent.phoneBody")}</span></span><Icon name="arrow" /></button> : null}
      {status ? <details className="runtime-details"><summary><Icon name="terminal" />{t("agent.engine")}</summary><dl><dt>Vision</dt><dd>{status.model ?? t("agent.notConfigured")}</dd><dt>{t("agent.isolated")}</dt><dd>{status.docker && status.image_ready ? t("agent.dockerReady") : t("agent.dockerStart")}</dd><dt>{t("agent.dossier")}</dt><dd>{t("agent.recordsHere")}</dd><dt>iPhone</dt><dd>Same Wi-Fi, Mac awake</dd></dl></details> : null}
    </aside>
  </div>;
}
