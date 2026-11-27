import { useEffect, useState } from "react";
import { artifactUrl, listVersions, listWorkbooks } from "../lib/api";
import { localTime, shortHash } from "../lib/format";
import type { WorkbookView } from "../lib/types";
import { ErrorNote, Icon, Pill, Skeleton } from "../ui";

export default function Versions({ workbookId }: { workbookId?: string }) {
  const [wb, setWb] = useState<WorkbookView | null | undefined>(undefined);
  const [items, setItems] = useState<Record<string, any>[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    listWorkbooks().then(async (r) => {
      const w = r.items.find(w => w.workbook_id === workbookId) ?? r.items[r.items.length - 1] ?? null;
      setWb(w);
      if (w) setItems((await listVersions(w.workbook_id)).items);
    }).catch(setError);
  }, [workbookId]);
  if (error) return <ErrorNote error={error} />;
  if (wb === undefined || (wb && !items)) return <Skeleton lines={4} />;
  if (!wb) return <p className="muted">No workbook connected yet.</p>;
  return (
    <div className="stack-lg">
      <div className="stack" style={{ gap: 4 }}>
        <h1>Workbook versions</h1>
        <p className="muted">{wb.display_name}. Every approved entry creates a new version. Earlier versions, including the original upload, stay downloadable.</p>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Version</th><th>Created</th><th>Source</th><th>SHA-256</th><th></th></tr></thead>
          <tbody>
            {items!.map((v) => (
              <tr key={v.version_id}>
                <td><strong>v{v.number}</strong> {v.is_current ? <Pill tone="ok">current</Pill> : null}</td>
                <td className="mono">{localTime(v.created_at)}</td>
                <td>{v.source === "upload" ? "Original upload (never modified)" : <>Approved entry <a href={`#/runs/${v.run_id}`} className="mono">{v.run_id}</a></>}</td>
                <td><span className="hashchip" title={v.sha256}>{shortHash(v.sha256)}</span></td>
                <td><a className="btn" href={artifactUrl(v.artifact_id)} download><Icon name="download" />.xlsx</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
