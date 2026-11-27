import { useState } from "react";
import { artifactUrl, listRuns, listVersions, listWorkbooks } from "../lib/api";
import { money } from "../lib/format";
import type { RunListItem, WorkbookView } from "../lib/types";
import { usePolling } from "../lib/usePolling";
import { ErrorNote, Icon, Skeleton } from "../ui";

function WorkbookCheck({ book, latest }: { book: WorkbookView; latest?: RunListItem }) {
  const [result, setResult] = useState<"checking" | "match" | "mismatch">();
  const [error, setError] = useState<unknown>(null);
  const verify = async () => {
    setResult("checking"); setError(null);
    try {
      const versions = await listVersions(book.workbook_id);
      const version = versions.items.find(item => item.version_id === book.current_version_id);
      if (!version) throw new Error("The workbook version has changed. Refresh and try again.");
      const response = await fetch(artifactUrl(version.artifact_id));
      if (!response.ok) throw new Error("Unable to read this workbook version.");
      const digest = await crypto.subtle.digest("SHA-256", await response.arrayBuffer());
      const actual = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
      setResult(actual === book.current_sha256 ? "match" : "mismatch");
    } catch (reason) { setResult(undefined); setError(reason); }
  };
  const baseline = book.baseline_summary;
  return <section className="panel stack workbook-check">
    <div className="spread"><h2>{book.display_name}</h2><a href={`#/workbook/${book.workbook_id}`}>Open workbook</a></div>
    <dl className="kv">
      <dt>Structure</dt><dd>{book.compatibility?.supported ? "Supported" : book.status === "unsupported" ? "Unsupported" : "Awaiting inspection"}</dd>
      <dt>Account mapping</dt><dd>{book.status === "ready" ? "Confirmed" : "Not confirmed"}</dd>
      <dt>Opening balance</dt><dd>{baseline ? baseline.difference_minor === 0 ? "Balanced" : `${money(baseline.difference_minor)} SEK difference` : "Not checked yet"}</dd>
      <dt>Latest entry verification</dt><dd>{latest?.validation_summary ? <a href={`#/receipts/${latest.run_id}`}>{latest.validation_summary.checks_passed}/{latest.validation_summary.checks_total} checks passed</a> : "No verification report yet"}</dd>
    </dl>
    <div className="row"><button className="btn" disabled={result === "checking"} onClick={() => void verify()}><Icon name="shield"/>{result === "checking" ? "Checking…" : `Verify file integrity · v${book.version_count}`}</button>
      {result === "match" || result === "mismatch" ? <span role="status">{result === "match" ? "File matches the stored SHA-256." : "File differs from the stored SHA-256."}</span> : null}</div>
    <ErrorNote error={error}/>
  </section>;
}

export function WorkbookChecks() {
  const { data, error } = usePolling(async () => {
    const [books, runs] = await Promise.all([listWorkbooks(), listRuns()]);
    return { books: books.items, runs: runs.items };
  });
  return <div className="stack-lg">
    <header className="page-heading"><div><h1>Workbook checks</h1><p className="muted">Check workbook structure, account mapping, balance and stored file integrity.</p></div></header>
    <ErrorNote error={error}/>
    {!data && !error ? <Skeleton/> : null}
    {data && !data.books.length ? <section className="panel stack"><h2>No workbook connected</h2><a href="#/workbook">Connect a workbook</a></section> : null}
    {data?.books.map(book => <WorkbookCheck key={book.current_version_id} book={book} latest={data.runs.find(run => run.workbook_id === book.workbook_id && run.validation_summary !== null)}/>)}
  </div>;
}
