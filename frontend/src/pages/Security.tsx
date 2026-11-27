import { useEffect, useState } from "react";
import { getContainmentTest, startContainmentTest } from "../lib/api";
import { Callout, ErrorNote, Icon, Pill } from "../ui";

const PROBES: [string, string, string, (s: string) => boolean][] = [
  ["network", "Outbound connection to the internet", "refused", (s) => /unreachable|refused|Errno/i.test(s) && !/CONNECTED/.test(s)],
  ["filesystem", "Write outside the work folder", "denied", (s) => /Read-only file system|Permission denied/i.test(s) && !/WRITTEN/.test(s)],
  ["run_secrets_exists", "Look for credentials (/run/secrets, environment)", "nothing found", (s) => /False/.test(s)],
  ["infinite_loop", "Infinite loop", "killed at the time limit", () => true],
];

export default function Security() {
  const [test, setTest] = useState<Record<string, any> | null>(null);
  const [error, setError] = useState<unknown>(null);
  const run = async () => {
    setError(null);
    try { const t = await startContainmentTest(); setTest({ test_id: t.test_id, state: "RUNNING", lines: [] }); } catch (e) { setError(e); }
  };
  useEffect(() => {
    if (!test || test.state !== "RUNNING") return;
    const t = setInterval(() => getContainmentTest(test.test_id).then(setTest).catch(setError), 1000);
    return () => clearInterval(t);
  }, [test?.test_id, test?.state]);
  const lines: string[] = test?.lines ?? [];
  const r = test?.result;
  return (
    <div className="stack-lg">
      <div className="stack" style={{ gap: 4 }}>
        <h1>Containment test</h1>
        <p className="muted">Runs a deliberately hostile script in the same sandbox type used for your workbook. Safe: the sandbox gets no data and no
          credentials. Every line below is the runtime's own output.</p>
      </div>
      <div><button className="btn primary" onClick={run} disabled={test?.state === "RUNNING"}><Icon name="shield" />
        {test?.state === "RUNNING" ? "Running… (the loop is killed after 10 s)" : "Run containment test"}</button></div>
      <ErrorNote error={error} />
      {test ? (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Probe</th><th>Expected</th><th>Observed (raw runtime output)</th><th>Result</th></tr></thead>
            <tbody>
              {PROBES.map(([key, label, expect, ok]) => {
                const secrets = key === "run_secrets_exists";
                const obs = lines.filter((l) => l.includes(key) || (secrets && l.includes("env_names")));
                const judged = secrets ? obs.filter((l) => l.includes(key)) : obs;
                const done = test.state === "DONE";
                const passed = key === "infinite_loop" ? r?.termination_reason === "timeout" : judged.length > 0 && judged.every((l) => ok(l));
                return (
                  <tr key={key}>
                    <td>{label}</td><td className="muted">{expect}</td>
                    <td><pre className="log" style={{ margin: 0, maxHeight: 120 }}>{key === "infinite_loop" && done
                      ? `killed: ${r?.termination_reason} after ${(r?.duration_ms / 1000).toFixed(1)} s, exit ${r?.exit_code}` : obs.join("\n") || "…"}</pre></td>
                    <td>{!done ? <Pill tone="busy">running</Pill> : passed ? <Pill tone="ok">contained</Pill> : <Pill tone="bad">not contained</Pill>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
      {r ? (
        <Callout tone={r.destroyed ? "ok" : "bad"} title={r.destroyed ? "Sandbox destroyed." : "Sandbox destruction not confirmed."}>
          <p className="mono small">runtime {r.runtime} · {r.sandbox_id} · limits {r.limits ? `${r.limits.cpus} CPU, ${r.limits.memory_mb} MB, ${r.limits.timeout_s} s, ${r.limits.pids} pids, network ${r.limits.network}` : "none (UNSANDBOXED dev fallback)"}</p>
        </Callout>
      ) : null}
    </div>
  );
}
