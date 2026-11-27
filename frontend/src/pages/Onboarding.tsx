import { useEffect, useState } from "react";
import { confirmMapping, fixtureFile, getInspection, getMapping, listWorkbooks, newIdempotencyKey, proposeMapping, uploadWorkbook } from "../lib/api";
import { money, shortHash } from "../lib/format";
import type { Session, WorkbookView } from "../lib/types";
import { Callout, ErrorNote, Icon, Pill, Skeleton } from "../ui";

export default function Onboarding({ session, workbookId }: { session: Session; workbookId?: string }) {
  const [wbs, setWbs] = useState<WorkbookView[] | null>(null);
  const [active, setActive] = useState<WorkbookView | null>(null);
  const [inspection, setInspection] = useState<Record<string, any> | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [ack, setAck] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [uploadKey, setUploadKey] = useState(() => newIdempotencyKey("wb"));
  const owner = session.role === "owner";

  const load = async (select?: string) => {
    const r = await listWorkbooks();
    setWbs(r.items);
    const pick = r.items.find((w) => w.workbook_id === select) ?? r.items[r.items.length - 1] ?? null;
    setActive(pick);
    setInspection(pick ? await getInspection(pick.workbook_id).catch(() => null) : null);
  };
  useEffect(() => { load(workbookId).catch(setError); }, [workbookId]);

  const upload = async () => {
    if (!file) return;
    setBusy("upload");
    setError(null);
    try {
      const r = await uploadWorkbook(file, name || file.name.replace(/\.xlsx$/i, ""), uploadKey);
      await load(r.workbook_id);
      setFile(null);
    } catch (e) { setError(e); } finally { setBusy(null); }
  };

  const confirm = async () => {
    if (!active) return;
    setBusy("confirm");
    setError(null);
    try {
      const p = await proposeMapping(active.workbook_id, active.current_version_id, active.current_sha256);
      const m = await getMapping(active.workbook_id, p.mapping_id);
      await confirmMapping(active.workbook_id, p.mapping_id, {
        expected_mapping_version: m.mapping_version, expected_mapping_sha256: m.mapping_sha256, policy_version: "policy_nordvik_v1",
        confirmed_bindings: {}, baseline_acknowledgement: inspection?.baseline?.acknowledgement_required
          ? "Pre-existing exceptions reviewed; LedgerFlow will not change existing entries." : null,
      });
      await load(active.workbook_id);
    } catch (e) { setError(e); } finally { setBusy(null); }
  };

  if (wbs === null) return error ? <ErrorNote error={error} /> : <Skeleton lines={5} />;
  const base = inspection?.baseline;
  const compat = inspection?.compatibility;
  const ready = active?.status === "ready";

  return (
    <div className="stack-lg">
      {wbs.length > 1 ? <label>Workbook<select value={active?.workbook_id ?? ""} onChange={e => { window.location.hash = `#/workbook/${e.target.value}`; }}>{wbs.map(w => <option key={w.workbook_id} value={w.workbook_id}>{w.display_name}</option>)}</select></label> : null}
      <div className="spread">
        <div className="stack" style={{ gap: 4 }}>
          <h1>{active ? active.display_name : "Connect your Excel ledger"}</h1>
          <p className="muted">LedgerFlow writes into your existing workbook. It never changes its structure, formulas or opening balances,
            and every change needs your approval.</p>
        </div>
        {active ? <span className="hashchip" title={active.current_sha256}>v{active.version_count} · {shortHash(active.current_sha256)}</span> : null}
      </div>

      {owner ? (
        <section className="panel stack workbook-drop" aria-labelledby="up-h" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); if (busy) return; const f = e.dataTransfer.files[0]; if (!f) return; if (!f.name.toLowerCase().endsWith(".xlsx")) { setError(new Error("Choose an .xlsx workbook.")); return; } setFile(f); setName(f.name.replace(/\.xlsx$/i, "")); setUploadKey(newIdempotencyKey("wb")); }}>
          <h2 id="up-h">{active ? "Connect another workbook" : "Upload the workbook"}</h2>
          <div className="row">
            <input type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" aria-label="Workbook file"
              onChange={(e) => { const f = e.target.files?.[0] ?? null; setFile(f); setName(f ? f.name.replace(/\.xlsx$/i, "") : ""); setUploadKey(newIdempotencyKey("wb")); }}
              style={{ maxWidth: 360 }} />
            <input aria-label="Display name" placeholder="Display name" value={name} onChange={(e) => setName(e.target.value)} style={{ maxWidth: 280 }} />
            <button className="btn primary" onClick={upload} disabled={!file || !!busy}><Icon name="upload" />{busy === "upload" ? "Reading…" : "Upload and inspect"}</button>
          </div>
          {session.backend === "DEV-MOCK" ? (
            <div className="row small">Development backend:
              {["nordvik_t_accounts.xlsx", "nordvik_t_accounts_error.xlsx"].map((n) => (
                <button key={n} className="btn ghost" onClick={() => fixtureFile(n).then((f) => { setFile(f); setName(n.includes("error") ? "Nordvik Trading AB (with a pre-existing error)" : "Nordvik Trading AB"); }).catch(setError)}>
                  Use sample {n.includes("error") ? "with a pre-existing error" : "workbook"}</button>))}
              {file ? <span>Selected: <code>{file.name}</code></span> : null}
            </div>
          ) : null}
          <p className="small">Drop an .xlsx file here or choose a file above. {file ? `Selected: ${file.name}. ` : ""}The original stays as version 1. Every approved change creates a new version.</p>
        </section>
      ) : !active ? <Callout tone="info" title="No workbook yet.">An owner connects the company workbook.</Callout> : null}

      <ErrorNote error={error} />

      {active && compat && !compat.supported ? (
        <Callout tone="bad" title="LedgerFlow can't safely write to this workbook yet.">
          <p>{compat.message}</p>
          <p>Supported today: T-account workbooks (SSE style, with account dropdowns) and, next, journal tables with Date / Account / Debit / Credit columns.</p>
        </Callout>
      ) : null}

      {active && compat?.supported ? (
        <>
          <section className="grid2">
            <div className="panel stack">
              <h2>What LedgerFlow found</h2>
              <dl className="kv">
                <dt>Layout</dt><dd>T-accounts on sheet <code>{compat.sheet}</code></dd>
                <dt>Accounts</dt><dd>{compat.accounts}</dd>
                <dt>Entry slots</dt><dd>{compat.slot_count} ({compat.used_slots} used, {compat.slot_count - compat.used_slots} free)</dd>
                <dt>Formulas</dt><dd>{compat.formulas} (never edited)</dd>
                <dt>Dropdown lists</dt><dd>{compat.validation_ranges} ranges (preserved byte for byte)</dd>
                <dt>Sheets</dt><dd>{(compat.sheets as string[]).join(" · ")}</dd>
              </dl>
            </div>
            <div className="panel stack">
              <h2>Balances (trial balance of every slot)</h2>
              {base ? (
                <>
                  <dl className="kv">
                    <dt>Opening balances</dt>
                    <dd className="mono">{money(base.opening_debits_minor)} = {money(base.opening_credits_minor)}{" "}
                      {base.opening_debits_minor === base.opening_credits_minor ? <Pill tone="ok">balanced</Pill> : <Pill tone="bad">unbalanced</Pill>}</dd>
                    <dt>All debits</dt><dd className="mono">{money(base.debits_minor)}</dd>
                    <dt>All credits</dt><dd className="mono">{money(base.credits_minor)}</dd>
                  </dl>
                  {base.difference_minor === 0 && !base.contra_exceptions.length ? (
                    <Callout tone="ok">The ledger balances and every posting has its mirror in the contra account.</Callout>
                  ) : (
                    <Callout tone="warn" title={`The ledger is out by SEK ${money(Math.abs(base.difference_minor))}.`}>
                      <p>{base.contra_exceptions.length} line(s) have no mirror in their contra account:{" "}
                        {base.contra_exceptions.map((x: any) => <code key={x.amount_cell} style={{ marginRight: 6 }}>{x.amount_cell}</code>)}
                        ({base.contra_exceptions.map((x: any) => `${x.account_id} ${x.side} ${money(x.amount_minor)}`).join("; ")}).</p>
                      <p>LedgerFlow will not change existing entries. These stay listed as pre-existing exceptions, and every new entry is checked
                        not to make them worse.</p>
                    </Callout>
                  )}
                </>
              ) : <Skeleton />}
            </div>
          </section>

          <section className="stack" aria-labelledby="acc-h">
            <h2 id="acc-h">Accounts and write areas</h2>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Account</th><th>Role</th><th>Header</th><th>Debit slots</th><th>Credit slots</th><th>Opening balance</th></tr></thead>
                <tbody>
                  {inspection!.accounts.map((a: any) => (
                    <tr key={a.account_id}>
                      <td><span className="mono">{a.account_id}</span> {a.name}</td>
                      <td className="muted">{a.role}</td>
                      <td className="mono">{a.header_cell}</td>
                      <td className="mono">{a.debit.first_row ? `${a.debit.reference_column}${a.debit.first_row}:${a.debit.amount_column}${a.debit.last_row}` : "—"}</td>
                      <td className="mono">{a.credit.first_row ? `${a.credit.reference_column}${a.credit.first_row}:${a.credit.amount_column}${a.credit.last_row}` : "—"}</td>
                      <td className="mono">{a.debit.opening_balance_cell ?? a.credit.opening_balance_cell ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {ready ? (
            <Callout tone="ok" title="Mapping confirmed.">
              <p>Mapping <code>{active.mapping?.mapping_id}</code> · {shortHash(active.mapping?.mapping_sha256)}. Employees can now submit receipts.
                Share <code>{window.location.origin}/#/capture</code> with your team.</p>
            </Callout>
          ) : owner ? (
            <section className="panel stack">
              <h2>Confirm the mapping</h2>
              <p className="muted">You confirm that these account blocks and write areas are right. LedgerFlow will only ever write into the slots listed above.</p>
              {base?.acknowledgement_required ? (
                <label style={{ display: "flex", gap: 8, alignItems: "flex-start", fontWeight: 400 }}>
                  <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} style={{ width: 18, minHeight: 18, marginTop: 2 }} />
                  I have seen the pre-existing exceptions. LedgerFlow should leave them as they are.
                </label>
              ) : null}
              <div><button className="btn primary" onClick={confirm} disabled={!!busy || (base?.acknowledgement_required && !ack)}>
                <Icon name="check" />{busy === "confirm" ? "Confirming…" : "Confirm mapping"}</button></div>
            </section>
          ) : <Callout tone="info">Waiting for the owner to confirm the mapping.</Callout>}
        </>
      ) : null}
    </div>
  );
}
