import { useEffect, useRef, useState } from "react";
import { ApiError, createRun, fixtureFile, getDocument, getRun, listFixtures, subscribeRunEvents, uploadDocument, uploadTargets } from "../lib/api";
import { isTerminal, mergeEvents, STATE_LABEL } from "../lib/format";
import type { ExecutionEvent, RunSnapshot, Session, UploadTarget } from "../lib/types";
import { Callout, ErrorNote, Icon, Skeleton, StatePill } from "../ui";
import { ReceiptSummary } from "./Employee";

type Phase = "pick" | "preview" | "sending" | "sent";
const STEPS: [string, string[]][] = [
  ["Uploaded", ["QUEUED"]],
  ["Reading the document", ["EXTRACTING"]],
  ["Entry prepared", ["PLANNING", "GENERATING_CODE", "SANDBOX_STARTING", "EXECUTING", "VERIFYING", "RETRY_PENDING"]],
  ["Waiting for finance approval", ["AWAITING_APPROVAL", "NEEDS_REVIEW", "DUPLICATE_REVIEW"]],
  ["Booked", ["COMMITTED"]],
];

export default function Capture({ session }: { session: Session }) {
  const [targets, setTargets] = useState<UploadTarget[] | null>(null);
  const [target, setTarget] = useState<UploadTarget | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [small, setSmall] = useState(false);
  const [progress, setProgress] = useState(0);
  const [sendStage, setSendStage] = useState("Uploading photo");
  const [phase, setPhase] = useState<Phase>("pick");
  const [error, setError] = useState<unknown>(null);
  const [run, setRun] = useState<RunSnapshot | null>(null);
  const [, setEvents] = useState<ExecutionEvent[]>([]);
  const uploadId = useRef<string>("");
  const documentId = useRef<string | null>(null);
  const sending = useRef(false);
  const abort = useRef<AbortController | null>(null);
  const camera = useRef<HTMLInputElement>(null);
  const [samples, setSamples] = useState<{ case_id: string; title: string; file: string }[]>([]);
  useEffect(() => { if (session.backend === "DEV-MOCK") listFixtures().then((f) => setSamples(f.receipts)).catch(() => undefined); }, []);
  const picker = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const requested = new URLSearchParams(location.hash.split("?")[1] ?? "").get("workbook");
    uploadTargets().then((r) => { setTargets(r.items); setTarget(r.items.find(t => t.workbook_id === requested) ?? r.items[0] ?? null); }).catch(setError);
  }, []);

  useEffect(() => () => abort.current?.abort(), []);
  useEffect(() => {
    if (!file) { setPreview(null); return; }
    const url = URL.createObjectURL(file); setPreview(url); setSmall(false);
    const img = new Image();
    img.onload = () => setSmall(Math.min(img.naturalWidth, img.naturalHeight) < 1000);
    img.onerror = () => setError(new Error("This image could not be decoded. Retake it or choose a JPEG / PNG."));
    img.src = url;
    return () => { img.onload = null; img.onerror = null; URL.revokeObjectURL(url); };
  }, [file]);

  useEffect(() => {
    if (!run || isTerminal(run.state)) return;
    const refresh = () => getRun(run.run_id).then(setRun).catch(() => undefined);
    const close = subscribeRunEvents(run.run_id, 0, (e) => { setEvents((p) => mergeEvents(p, [e])); if (e.event_type === "run.state_changed") refresh(); });
    const poll = setInterval(refresh, 4000); // SSE is a hint; the snapshot is the truth
    return () => { close(); clearInterval(poll); };
  }, [run?.run_id, run && isTerminal(run.state)]);

  const choose = (f: File | undefined) => {
    if (!f) return;
    setError(null);
    if (f.size > 10 * 1024 * 1024) { setError(new ApiError(413, "IMAGE_TOO_LARGE", "This file can't be used (max 10 MB, JPG or PNG).")); return; }
    if (!/^image\/(jpeg|png)$/.test(f.type)) {
      setError(new ApiError(415, "IMAGE_UNREADABLE", "Use a JPG or PNG photo. On iPhone, set Camera > Formats > Most Compatible, or upload a screenshot."));
      return;
    }
    uploadId.current = `cap_${crypto.randomUUID().replace(/-/g, "").slice(0, 20)}`;
    documentId.current = null;
    setFile(f);
    setPhase("preview");
  };

  const send = async () => {
    if (!file || !target || sending.current) return;
    sending.current = true;
    abort.current = new AbortController();
    setPhase("sending");
    setProgress(0); setSendStage(documentId.current ? "Preparing submission" : "Uploading photo");
    setError(null);
    try {
      if (!documentId.current) {
        const doc = await uploadDocument(target.workbook_id, file, file.name || "receipt.jpg", uploadId.current, setProgress, abort.current.signal);
        documentId.current = doc.document_id;
      }
      setSendStage("Checking uploaded image");
      // Upload acceptance is not normalization success. Wait for the authoritative document status.
      const deadline = Date.now() + 30000;
      for (;;) {
        if (abort.current.signal.aborted) return;
        const doc = await getDocument(documentId.current);
        if (["ready", "normalized"].includes(doc.status)) break;
        if (["failed", "rejected", "unreadable"].includes(doc.status)) throw new Error("The server could not read this image. Retake the receipt.");
        if (Date.now() > deadline) throw new Error("The image is still being prepared. Retry this submission in a moment.");
        await new Promise(resolve => setTimeout(resolve, 700));
      }
      setSendStage("Submitting to finance");
      const available = await uploadTargets();
      const latest = available.items.find(t => t.workbook_id === target.workbook_id);
      if (!latest) throw new Error("This workbook is no longer accepting receipts. Ask finance to reconnect it.");
      const r = await createRun(latest, documentId.current, uploadId.current);
      if (abort.current.signal.aborted) return;
      setRun(await getRun(r.run_id));
      setPhase("sent");
    } catch (e) {
      if (abort.current?.signal.aborted) return;
      setError(e);
      setPhase("preview"); // retry keeps the same client_upload_id, so the server dedupes
    } finally { sending.current = false; }
  };

  const reset = () => { setFile(null); setPreview(null); setRun(null); setEvents([]); documentId.current = null; setPhase("pick"); setError(null); if (camera.current) camera.current.value = ""; if (picker.current) picker.current.value = ""; };

  if (targets === null) return error ? <ErrorNote error={error} /> : <Skeleton />;
  if (!targets.length) {
    return <Callout tone="info" title="No workbook is ready yet.">
      <p>An owner has to connect and confirm the company workbook first{session.role === "owner" ? <> (<a href="#/workbook">connect it now</a>)</> : ""}.</p>
    </Callout>;
  }

  return (
    <div className="stack-lg">
      <div className="stack" style={{ gap: 6 }}>
        <h1>{phase === "sent" ? "Receipt submitted." : "New receipt"}</h1><p className="capture-workbook">{target?.display_name}</p>
        <p className="muted">Photograph a receipt or invoice. Finance takes it from there.</p>
      </div>
      {targets.length > 1 ? (
        <label htmlFor="target">Company workbook
          <select id="target" disabled={phase !== "pick"} value={target?.workbook_id} onChange={(e) => setTarget(targets.find((t) => t.workbook_id === e.target.value) ?? null)}>
            {targets.map((t) => <option key={t.workbook_id} value={t.workbook_id}>{t.display_name}</option>)}
          </select>
        </label>
      ) : null}

      <input ref={camera} type="file" accept="image/jpeg,image/png" capture="environment" hidden onChange={(e) => choose(e.target.files?.[0])} />
      <input ref={picker} type="file" accept="image/jpeg,image/png" hidden onChange={(e) => choose(e.target.files?.[0])} />

      {phase === "pick" ? (
        <div className="stack">
          <div className="capture-guide"><div className="capture-framing"><Icon name="file" /></div><h2>Keep the whole receipt in frame.</h2><p>Use good light and a flat surface. Check that the total and date are readable.</p></div>
          <button className="btn primary big" onClick={() => camera.current?.click()}><Icon name="camera" />Take photo</button>
          <button className="btn" onClick={() => picker.current?.click()}><Icon name="upload" />Upload a file</button>
          <p className="small">JPEG or PNG, up to 10 MB. Convert PDF or HEIC to an image before uploading.</p>
          {samples.length ? (
            <label htmlFor="sample">Development backend: use a sample document
              <select id="sample" defaultValue="" onChange={(e) => e.target.value && fixtureFile(e.target.value).then(choose).catch(setError)}>
                <option value="">Choose a sample…</option>
                {samples.map((s) => <option key={s.file} value={s.file}>{s.case_id} · {s.title}</option>)}
              </select>
            </label>
          ) : null}
        </div>
      ) : null}

      {(phase === "preview" || phase === "sending") && preview ? (
        <div className="stack">
          <img className="capture-preview" src={preview} alt="Photo you are about to send" />
          {small ? <Callout tone="warn">This photo looks small. Small text may be unreadable.</Callout> : null}
          {phase === "sending" ? <div className="stack" aria-live="polite"><label htmlFor="upload-progress">{sendStage}{sendStage === "Uploading photo" ? ` · ${progress}%` : ""}</label><progress id="upload-progress" max={100} value={progress} /></div> : null}
          <button className="btn primary big" onClick={send} disabled={phase === "sending" || !navigator.onLine}>
            <Icon name="upload" />{phase === "sending" ? "Sending…" : "Use this photo"}
          </button>
          <button className="btn" onClick={reset} disabled={phase === "sending"}>Retake</button>
        </div>
      ) : null}

      <ErrorNote error={error} />

      {phase === "sent" && run ? (
        <div className="panel stack">
          <div className="spread">
            <div>
              <div className="small">Submitted as</div>
              <div className="mono" style={{ fontSize: 15 }}>{run.run_id}</div>
            </div>
            <StatePill state={run.state} />
          </div>
          <ReceiptSummary run={run} />
          {preview ? <img src={preview} alt="" style={{ width: 72, height: 72, objectFit: "cover", borderRadius: 6, border: "1px solid var(--grid)" }} /> : null}
          <ol className="steps" aria-live="polite">
            {STEPS.map(([label], i) => {
              const cur = STEPS.findIndex(([, s]) => s.includes(run.state));
              const cls = cur > i || run.state === "COMMITTED" ? "done" : cur === i ? "now" : "";
              return <li key={label} className={cls}><Icon name={cls === "done" ? "checkCircle" : "clock"} />{label}</li>;
            })}
          </ol>
          {run.state === "NEEDS_REVIEW" ? <p className="muted">A detail needs checking. <a href={`#/expenses/${run.run_id}`}>See the request</a>.</p> :
            <p className="muted">You can close this page. Nothing else is needed from you.</p>}
          {["FAILED", "REJECTED"].includes(run.state) ? <p className="small">Status: {STATE_LABEL[run.state]}</p> : null}
          <button className="btn" onClick={reset}><Icon name="camera" />Photograph another</button>
          {session.role === "employee" ? <a href={`#/expenses/${run.run_id}`}>View receipt status</a> : <a href={`#/transactions/${run.run_id}`}>Open in financial workspace</a>}
        </div>
      ) : null}
    </div>
  );
}
