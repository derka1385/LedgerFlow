import { listRuns } from "../lib/api";
import { money } from "../lib/format";
import { useT } from "../lib/i18n";
import type { RunState, Session } from "../lib/types";
import { usePolling } from "../lib/usePolling";
import { ErrorNote, Icon } from "../ui";

type Status = "reading" | "writing" | "approve" | "booked" | "held" | "failed";
export function statusOf(state: RunState): Status {
  if (state === "COMMITTED") return "booked";
  if (state === "AWAITING_APPROVAL") return "approve";
  if (state === "NEEDS_REVIEW" || state === "DUPLICATE_REVIEW" || state === "STALE_BASE") return "held";
  if (state === "FAILED" || state === "REJECTED" || state === "CANCELLED" || state === "EXPIRED") return "failed";
  if (state === "QUEUED" || state === "EXTRACTING") return "reading";
  return "writing";
}
const LABEL: Record<Status, string> = { reading: "state.reading", writing: "state.writing", approve: "state.approve", booked: "state.booked", held: "state.held", failed: "state.failed" };

/** Phone home: a live mini-sheet of real runs, the scan action, and the explainer. */
export default function Home({ session }: { session: Session }) {
  const [t] = useT();
  const { data, error } = usePolling(listRuns, 6000);
  const finance = session.role !== "employee";
  const runs = data?.items ?? [];
  const count = (s: Status) => runs.filter(r => statusOf(r.state) === s).length;
  const open = (id: string) => `#/${finance ? "transactions" : "expenses"}/${id}`;
  const rows = runs.slice(0, 5);
  return <div className="home">
    <header className="home-head">
      <h1>{t("home.hello")}</h1>
    </header>

    <section className="live-sheet" aria-label={t("home.sheet")}>
      <div className="live-sheet-cols" aria-hidden="true"><i /><b>A</b><b>B</b><b>C</b><b>D</b></div>
      <div className="live-sheet-row head" aria-hidden="true"><i>1</i><span>{t("home.sheet")}</span><span className="num">{t("home.date")}</span><span className="num">SEK</span><span>{t("home.status")}</span></div>
      {rows.length ? rows.map((r, i) => {
        const st = statusOf(r.state);
        const proven = st === "approve" || st === "booked";
        return <a key={r.run_id} href={open(r.run_id)} className={`live-sheet-row ${i === 0 ? "is-newest" : ""} ${proven ? "is-proven" : "is-pending"}`} style={{ ["--i" as string]: i }}>
          <i>{i + 2}</i>
          <span className="who">{r.merchant_name ?? "…"}</span>
          <span className="num date">{r.document_date ? r.document_date.slice(5) : "–"}</span>
          <span className="num">{r.gross_minor != null ? money(r.gross_minor) : "–"}</span>
          <span className={`status status-${st}`}><b />{t(LABEL[st])}</span>
          {i === 0 ? <span className="selection-frame"><i /></span> : null}
        </a>;
      }) : <div className="live-sheet-row empty"><i>2</i><span>{data ? t("home.sheetEmpty") : "…"}</span></div>}
      {Array.from({ length: Math.max(0, 3 - Math.max(rows.length, 1)) }, (_, k) => <div className="live-sheet-row filler" aria-hidden="true" key={k}><i>{Math.max(rows.length, 1) + 2 + k}</i><span /><span /><span /><span /></div>)}
    </section>

    {runs.length ? <p className="home-tally">
      <a href={finance ? "#/transactions" : "#/expenses"}><b>{count("approve")}</b> {t("home.toApprove")}</a>
      <a href={finance ? "#/transactions" : "#/requests"}><b>{count("held")}</b> {t("home.needInfo")}</a>
      <span><b>{count("booked")}</b> {t("home.booked")}</span>
    </p> : null}

    <ErrorNote error={error} />

    <a className="shutter" href="#/capture" aria-label={`${t("home.scan")}. ${t("home.scanSub")}`}>
      <span className="shutter-lens" aria-hidden="true"><span><Icon name="camera" /></span></span>
      <span className="shutter-label">{t("home.scan")}</span>
    </a>

    <a className="how-link" href="#/how">
      <span className="how-mini" aria-hidden="true"><i /><i /><i /><i /></span>
      <span><strong>{t("home.how")}</strong><span>{t("home.howSub")}</span></span>
      <Icon name="arrow" />
    </a>
  </div>;
}
