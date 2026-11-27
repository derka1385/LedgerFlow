import { useState } from "react";
import { listRuns } from "../lib/api";
import { money } from "../lib/format";
import type { RunListItem } from "../lib/types";
import { usePolling } from "../lib/usePolling";
import { ErrorNote, Icon, Skeleton, StatePill } from "../ui";

type Period = "week" | "month";
type Expense = { id: string; supplier: string; date: string; category: string; amount: number | null; run?: RunListItem };
const colors = ["#78a979", "#527f9d", "#caa464", "#927cb0", "#c67365", "#5b9e97", "#83927f"];
const closed = new Set(["REJECTED", "CANCELLED", "FAILED", "EXPIRED"]);
const dateLabel = new Intl.DateTimeFormat("en-GB", { month: "short", day: "numeric", timeZone: "UTC" });
const monthLabel = new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });
const monthShort = new Intl.DateTimeFormat("en-GB", { month: "short", timeZone: "UTC" });
const day = (key: string) => new Date(key + "T00:00:00Z");
const keyOf = (date: Date) => date.toISOString().slice(0, 10);
const todayKey = () => new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Stockholm", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
const total = (rows: Expense[]) => rows.reduce((amount, item) => amount + (item.amount ?? 0), 0);
const asDate = (date: string | null, createdAt: string) => date && Number.isFinite(day(date).getTime()) ? date : createdAt.slice(0, 10);

function startOf(key: string, period: Period) {
  const date = day(key);
  if (period === "week") date.setUTCDate(date.getUTCDate() - (date.getUTCDay() + 6) % 7);
  else date.setUTCDate(1);
  return keyOf(date);
}

function shift(key: string, period: Period, by: number) {
  const date = day(key);
  if (period === "week") date.setUTCDate(date.getUTCDate() + by * 7);
  else date.setUTCMonth(date.getUTCMonth() + by);
  return keyOf(date);
}

function demoExpenses(today: string): Expense[] {
  const examples = [
    ["Coworking day pass", "Workspace", 56000],
    ["Airport train", "Travel", 32000],
    ["Project software", "Software", 44900],
    ["Team lunch", "Meals", 92000],
    ["Office supply order", "Supplies", 73000],
    ["Studio equipment", "Equipment", 185000],
  ] as const;
  const rows: Expense[] = [];
  for (let week = 0; week < 24; week += 1) {
    const base = day(shift(startOf(today, "week"), "week", -week));
    for (let index = 0; index < 3 + week % 2; index += 1) {
      const [supplier, category, amount] = examples[(index + week * 2) % examples.length];
      const date = new Date(base);
      date.setUTCDate(date.getUTCDate() + index);
      rows.push({id: `demo-${week}-${index}`, supplier, category,
        date: keyOf(date) > today ? today : keyOf(date), amount: amount + (week % 5) * 1800});
    }
  }
  return rows;
}

export default function ExpensesTracker() {
  const { data, error } = usePolling(listRuns, 4000);
  const [period, setPeriod] = useState<Period>("month");
  const [anchor, setAnchor] = useState(todayKey);
  const [view, setView] = useState<"workspace" | "demo" | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const today = todayKey();
  const workspace = (data?.items ?? []).filter(run => !closed.has(run.state));
  const demo = view === "demo" || (view === null && !!data && workspace.length === 0);
  const rows: Expense[] = demo ? demoExpenses(today) : workspace.map(run => ({
    id: run.run_id, supplier: run.merchant_name ?? "Receipt",
    date: asDate(run.document_date, run.created_at), category: run.expense_category ?? "Uncategorized",
    amount: run.gross_minor, run,
  }));
  const start = startOf(anchor, period);
  const end = shift(start, period, 1);
  const inRange = (from: string) => {
    const until = shift(from, period, 1);
    return rows.filter(row => row.date >= from && row.date < until);
  };
  const current = inRange(start);
  const periodTotal = total(current);
  const booked = total(current.filter(row => row.run?.state === "COMMITTED"));
  const groupAmounts = new Map<string, number>();
  for (const row of current) groupAmounts.set(row.category, (groupAmounts.get(row.category) ?? 0) + (row.amount ?? 0));
  const groups = [...groupAmounts].filter(([, value]) => value > 0).sort((a, b) => b[1] - a[1]);
  const palette = new Map([...new Set(rows.map(row => row.category))].sort().map((name, index) => [name, colors[index % colors.length]]));
  const visible = current.filter(row => !category || row.category === category).sort((a, b) => b.date.localeCompare(a.date));
  const groupTotal = groups.reduce((sum, [, amount]) => sum + amount, 0);
  const trend = Array.from({length: 6}, (_, index) => {
    const from = shift(start, period, index - 5);
    return { from, amount: total(inRange(from)) };
  });
  const maxTrend = Math.max(1, ...trend.map(bar => bar.amount));
  const currentWeek = startOf(today, "week");
  const recentWeeks = Array.from({length: 4}, (_, index) => shift(currentWeek, "week", -index - 1));
  const firstKnownDate = rows.reduce((first, row) => row.date < first && row.amount != null ? row.date : first, today);
  const completeWeeks = recentWeeks.filter(week => week >= firstKnownDate);
  const pace = completeWeeks.length ? total(rows.filter(row => row.date >= completeWeeks[completeWeeks.length - 1] && row.date < currentWeek))
    / completeWeeks.length : null;
  const circumference = 2 * Math.PI * 41;
  let offset = 0;

  function choosePeriod(next: string) { setAnchor(next); setCategory(null); }

  return <div className="stack-lg expense-tracker">
    <header className="page-heading">
      <div><h1>Expenses</h1><p className="muted">Follow supplier expenses by period and category.</p></div>
      <a className="btn primary" href="#/capture"><Icon name="upload"/>Add receipt</a>
    </header>
    <ErrorNote error={error}/>
    {!data && view !== "demo" && !error ? <Skeleton/> : null}
    <div className="expense-controls">
      <div className="segmented" aria-label="Expense data">
        <button type="button" aria-pressed={!demo} onClick={() => {setView("workspace"); choosePeriod(today);}}>Workspace</button>
        <button type="button" aria-pressed={demo} onClick={() => {setView("demo"); choosePeriod(today);}}>Demo expenses</button>
      </div>
      <div className="segmented" aria-label="Time period">
        <button type="button" aria-pressed={period === "week"} onClick={() => {setPeriod("week"); setCategory(null);}}>Week</button>
        <button type="button" aria-pressed={period === "month"} onClick={() => {setPeriod("month"); setCategory(null);}}>Month</button>
      </div>
      <div className="expense-period-navigation" aria-label="Browse periods">
        <button className="btn ghost" aria-label="Previous period" onClick={() => choosePeriod(shift(start, period, -1))}>‹</button>
        <strong role="status">{period === "month" ? monthLabel.format(day(start)) : `${dateLabel.format(day(start))} – ${dateLabel.format(new Date(day(end).getTime() - 86400000))}`}</strong>
        <button className="btn ghost" aria-label="Next period" disabled={start >= startOf(today, period)} onClick={() => choosePeriod(shift(start, period, 1))}>›</button>
        <button className="btn ghost" onClick={() => choosePeriod(today)}>Today</button>
      </div>
    </div>
    {demo ? <p className="expense-demo-note" role="status"><strong>Demo data</strong> · Sample expenses for the walkthrough.</p> : null}
    <section className="expense-overview panel" aria-label="Period summary">
      <div><span>{demo ? "Sample spending" : "Total for the period"}</span><strong>{money(periodTotal)} <small>SEK</small></strong></div>
      <dl>
        {demo ? <div><dt>Categories</dt><dd>{groups.length}</dd></div> : <><div><dt>Booked</dt><dd>{money(booked)} SEK</dd></div><div><dt>Open</dt><dd>{money(periodTotal - booked)} SEK</dd></div></>}
        <div><dt>Expenses</dt><dd>{current.length}</dd></div>
      </dl>
    </section>
    <div className="expense-workspace">
      <section className="expense-breakdown panel">
        <h2>Spending by category</h2>
        {groups.length ? <div className="expense-breakdown-grid">
          <div className="expense-ring">
            <svg viewBox="0 0 100 100" aria-hidden="true">
              <circle cx="50" cy="50" r="41" className="expense-ring-track"/>
              {groups.map(([name, amount]) => {
                const length = amount / groupTotal * circumference;
                const from = -offset;
                offset += length;
                return <circle key={name} cx="50" cy="50" r="41" stroke={palette.get(name)} className="expense-ring-segment"
                  strokeDasharray={`${Math.max(length - 1, 0)} ${circumference - Math.max(length - 1, 0)}`}
                  strokeDashoffset={from} opacity={category && category !== name ? .26 : 1} onClick={() => setCategory(category === name ? null : name)}/>;
              })}
            </svg>
            <div><strong>{money(category ? groupAmounts.get(category) ?? 0 : groupTotal)}</strong><small>SEK</small></div>
          </div>
          <div className="expense-legend" aria-label="Filter expenses by category">
            {groups.map(([name, amount]) => <button type="button" key={name} aria-pressed={category === name} onClick={() => setCategory(category === name ? null : name)}>
              <i style={{background: palette.get(name)}} aria-hidden="true"/><span>{name}</span><strong>{money(amount)}<small>{Math.round(amount / groupTotal * 100)}%</small></strong>
            </button>)}
          </div>
        </div> : <p className="muted">No expenses with known amounts for this period.</p>}
      </section>
      <section className="expense-activity panel">
        <div className="spread"><h2>{category ?? "Activity"}</h2>{category ? <button className="btn ghost" onClick={() => setCategory(null)}>Show all</button> : null}</div>
        {visible.length ? <ul className="expense-rows">
          {visible.map(row => <li key={row.id}>
            <div>{row.run ? <a href={`#/receipts/${row.run.run_id}`}>{row.supplier}</a> : <strong>{row.supplier}</strong>}
              <small>{row.category} · <time dateTime={row.date}>{dateLabel.format(day(row.date))}</time>{row.run?.capture_origin ? ` · ${row.run.capture_origin}` : ""}</small></div>
            <div><strong>{row.amount == null ? "—" : `${money(row.amount)} SEK`}</strong>{row.run ? <StatePill state={row.run.state}/> : null}</div>
          </li>)}
        </ul> : <p className="muted">No expenses in this selection.</p>}
      </section>
    </div>
    <div className="expense-insights">
    <section className="expense-trend panel">
      <h2>{period === "week" ? "Weekly spending" : "Monthly spending"}</h2>
      <div className="expense-bars">
        {trend.map(({from, amount}) => <button key={from} type="button" onClick={() => choosePeriod(from)} aria-pressed={from === start}
          aria-label={`${period === "week" ? `Week of ${dateLabel.format(day(from))}` : monthLabel.format(day(from))}, ${money(amount)} SEK`}>
          <span>{money(amount)}</span><i style={{height: `${Math.max(amount ? 5 : 1, amount / maxTrend * 100)}%`}}/><small>{period === "week" ? dateLabel.format(day(from)) : monthShort.format(day(from))}</small>
        </button>)}
      </div>
    </section>
    <section className="expense-pace panel stack">
      <h2>Spending pace</h2>
      {pace == null ? <p className="muted">An average is available once a full week is covered.</p> : <>
        <p className="muted">Average over {completeWeeks.length} completed {completeWeeks.length === 1 ? "week" : "weeks"}.</p>
        <dl className="kv"><dt>Per week</dt><dd><strong>{money(Math.round(pace))} SEK</strong></dd>
          <dt>Monthly equivalent</dt><dd><strong>{money(Math.round(pace * 52 / 12))} SEK</strong></dd></dl>
      </>}
    </section>
    </div>
    {!demo && (data?.items.length ?? 0) >= 100 ? <p className="small">Charts use the latest 100 receipts returned by the workspace.</p> : null}
  </div>;
}
