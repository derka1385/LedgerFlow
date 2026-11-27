import { useEffect, useRef, useState } from "react";
import { BrandMark } from "./Brand";
import { Icon } from "./ui";
import { useT } from "./lib/i18n";

const STEPS = 4;
const DWELL_MS = 5200;
const reduced = () => typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Four-step animated explanation of the real pipeline. Figures are sample values and labelled as such. */
export default function Explainer({ onDone, manual = false, doneLabel }: { onDone: () => void; manual?: boolean; doneLabel?: string }) {
  const [t] = useT();
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(() => !reduced());
  const start = useRef<number | null>(null);
  useEffect(() => {
    if (manual || !playing || step === STEPS - 1) return;
    const id = window.setTimeout(() => setStep(s => Math.min(STEPS - 1, s + 1)), DWELL_MS);
    return () => clearTimeout(id);
  }, [manual, playing, step]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") setStep(s => Math.min(STEPS - 1, s + 1));
      if (e.key === "ArrowLeft") setStep(s => Math.max(0, s - 1));
      if (e.key === "Escape") onDone();
    };
    window.addEventListener("keydown", key); return () => window.removeEventListener("keydown", key);
  }, [onDone]);
  const go = (n: number) => setStep(Math.max(0, Math.min(STEPS - 1, n)));
  const last = step === STEPS - 1;
  return <section className={`explainer ${playing ? "is-playing" : "is-paused"}`} aria-labelledby="explainer-title"
    onPointerDown={e => { start.current = e.clientX; }}
    onPointerUp={e => { if (start.current === null) return; const dx = e.clientX - start.current; start.current = null; if (Math.abs(dx) > 48) go(step + (dx < 0 ? 1 : -1)); }}>
    <header className="explainer-head">
      <BrandMark size={28} />
      <h1 id="explainer-title">{t("how.title")}</h1>
      <button className="btn ghost" onClick={onDone}>{t("how.skip")}</button>
    </header>
    <ol className="explainer-progress" aria-label={t("how.title")}>
      {Array.from({ length: STEPS }, (_, i) => <li key={i}><button onClick={() => go(i)} aria-current={i === step ? "step" : undefined} className={i < step ? "done" : i === step ? "active" : ""}>
        <span className="num">{String(i + 1).padStart(2, "0")}</span><span className="bar"><i style={!manual && i === step && playing && !last ? { animationDuration: `${DWELL_MS}ms` } : undefined} /></span>
      </button></li>)}
    </ol>
    <div className="explainer-stage" key={step}>
      <div className={`scene scene-${step + 1}`} aria-hidden="true">{[<SceneSnap key={0} />, <SceneRead key={1} t={t} />, <SceneProve key={2} />, <SceneApprove key={3} t={t} />][step]}</div>
      <div className="explainer-copy" aria-live="polite">
        <h2>{t(`how.s${step + 1}.t`)}</h2>
        <p>{t(`how.s${step + 1}.b`)}</p>
        <p className="explainer-sample">{t("how.demo")}</p>
      </div>
    </div>
    <footer className="explainer-foot">
      <button className="btn ghost icon-btn" onClick={() => setPlaying(p => !p)} aria-pressed={!playing} aria-label={playing ? t("how.pause") : t("how.play")}><Icon name={playing ? "pause" : "play"} /></button>
      <span className="explainer-spacer" />
      <div className="row">
        {step > 0 ? <button className="btn" onClick={() => go(step - 1)}>{t("how.back")}</button> : null}
        <button className="btn primary" onClick={() => (last ? onDone() : go(step + 1))}>{last ? doneLabel ?? t("how.done") : t("how.next")}<Icon name="arrow" /></button>
      </div>
    </footer>
  </section>;
}

function SceneSnap() {
  return <div className="snap">
    <div className="viewfinder"><span className="corner tl" /><span className="corner tr" /><span className="corner bl" /><span className="corner br" />
      <div className="paper-receipt"><b>PAPPERSKOMPANIET SÖDER AB</b><span>Org.nr 559999-1212</span><span className="rule" /><span>PAPPER A4 5x500 <em>1 187,50</em></span><span>HÄFTKLAMMER <em>375,00</em></span><span className="rule" /><strong>TOTALT SEK <em>1 562,50</em></strong><span>Moms 25 % <em>312,50</em></span></div>
      <span className="flash" />
    </div>
    <div className="shutter-ring"><span /></div>
  </div>;
}

const READ_ROWS: [string, string, string][] = [["A2", "how.l.supplier", "Papperskompaniet Söder AB"], ["A3", "how.l.date", "2026-11-27"], ["A4", "how.l.total", "1 562,50"], ["A5", "how.l.vat", "312,50"], ["A6", "how.l.paid", "****4821"]];
function SceneRead({ t }: { t: (k: string) => string }) {
  return <div className="read">
    <div className="mini-receipt"><span /><span /><span className="hot" /><span /><span className="hot" /><span /></div>
    <div className="beam" />
    <div className="sheet read-sheet" role="presentation">
      <div className="sheet-cols"><i /><b>A</b><b>B</b></div>
      {READ_ROWS.map(([addr, label, value], i) => <div className="sheet-row" key={addr} style={{ ["--i" as string]: i }}>
        <i>{i + 2}</i><span className="cell label">{t(label)}</span><span className="cell value"><span className="typed">{value}</span></span>
      </div>)}
      <span className="selection-frame travelling"><i /></span>
    </div>
  </div>;
}

const CODE = ["writes = plan.cells()", "patch_cells(book, \"T-Accounts\", writes)", "assert reread(book) == plan"];
const CHECKS = ["exact_write_set", "formulas_unchanged", "features_preserved", "new_entry_balanced", "no_new_active_content"];
function SceneProve() {
  return <div className="prove">
    <pre className="code-card">{CODE.map((l, i) => <code key={i} style={{ ["--i" as string]: i }}>{l}</code>)}</pre>
    <div className="sandbox-box"><span className="sandbox-label"><Icon name="lock" />sandbox · offline · 128 MiB</span><span className="sandbox-run" /></div>
    <ul className="check-list">{CHECKS.map((c, i) => <li key={c} style={{ ["--i" as string]: i }}><Icon name="check" /><code>{c}</code></li>)}</ul>
  </div>;
}

const CELLS: [string, string][] = [["R7", "[6110]"], ["S7", "1 250,00"], ["R8", "[2640]"], ["S8", "312,50"], ["K24", "[1940]"], ["L24", "312,50"], ["A57", "[1940]"], ["B57", "1 250,00"]];
function SceneApprove({ t }: { t: (k: string) => string }) {
  return <div className="approve">
    <div className="sheet approve-sheet" role="presentation">
      {CELLS.map(([a, v], i) => <div className="approve-cell" key={a} style={{ ["--i" as string]: i }}><code>{a}</code><span>{v}</span></div>)}
      <span className="selection-frame wide"><i /></span>
    </div>
    <div className="approve-bar"><span className="hash"><Icon name="lock" />sha256 fea407e9…</span><span className="approve-btn"><Icon name="check" />{t("how.l.approve")}</span></div>
    <div className="versions"><span>v1</span><span className="arrow" /><span className="new">v2</span></div>
  </div>;
}
