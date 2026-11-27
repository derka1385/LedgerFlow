import { MacReceipt } from "../MacWorkspace";
import { money, STATE_LABEL } from "../lib/format";
import type { ExecutionEvent, RunSnapshot, RunState } from "../lib/types";
import { Icon } from "../ui";

const reviewStates: RunState[] = ["NEEDS_REVIEW", "DUPLICATE_REVIEW", "STALE_BASE"];
const stoppedStates: RunState[] = ["FAILED", "CANCELLED", "REJECTED", "EXPIRED"];

const fieldNames: Record<string, string> = {
  merchant_name: "Supplier", supplier_org_no: "Seller registration or VAT number", gross_minor: "Total",
  document_date: "Document date", supplier_reference: "Invoice number", tax_minor: "VAT amount",
  tax_lines: "VAT rate or breakdown", tax_treatment: "VAT treatment", payment_source: "Payment account",
  payment_status: "Payment status", currency: "Currency", category_account_id: "Expense account", kind: "Document type",
};

export default function ReceiptProgress({ run, events, onReset }: { run: RunSnapshot; events: ExecutionEvent[]; onReset: () => void }) {
  const { state, transaction } = run;
  const needsReview = reviewStates.includes(state);
  const stopped = stoppedStates.includes(state);
  const awaiting = state === "AWAITING_APPROVAL";
  const booked = state === "COMMITTED";
  const extracting = state === "QUEUED" || state === "EXTRACTING";
  const processing = !needsReview && !stopped && !awaiting && !booked;
  const lastRead = [...events].reverse().find(event => event.event_type.startsWith("extraction."));
  const rereading = state === "EXTRACTING" && lastRead?.event_type === "extraction.rechecking";
  const title = needsReview ? "This receipt needs a check" : booked ? "Receipt booked" : awaiting ? "Ready for your approval"
    : stopped ? STATE_LABEL[state] : rereading ? "Re-reading unclear fields" : extracting ? "Reading your receipt" : "Preparing the entry";
  const reviewFields = [...new Set((run.review_items ?? []).flatMap(item => item.field && fieldNames[item.field] ? [fieldNames[item.field]] : []))];
  const fields = transaction ? [
    ["Supplier", transaction.merchant_name],
    ["Total", transaction.gross_minor == null ? null : `${money(transaction.gross_minor)} ${transaction.currency ?? ""}`],
    ["VAT", transaction.tax_minor == null ? null : `${money(transaction.tax_minor)} ${transaction.currency ?? ""}`],
  ].filter((row): row is [string, string] => !!row[1]) : [];
  return <section className="receipt-progress panel" aria-label="Receipt progress">
    <header className="receipt-progress-head">
      <div className={`receipt-progress-art${processing ? " is-reading" : ""}`} aria-hidden="true"><MacReceipt size={52}/><span/></div>
      <div className="receipt-progress-copy" aria-live="polite">
        <h2 key={title}>{title}</h2>
        <p className="muted">{needsReview ? reviewFields.length ? `Please verify: ${reviewFields.join(", ")}.` :
          "Open the receipt to see why it was held for review." : awaiting ? "You can inspect the proposed changes before approving." :
          stopped ? "Open the receipt to check what happened." : booked ? "The approved entry is in your workbook." : rereading ?
          "The agent is checking the original again for evidence it missed." : "You can leave this screen while the agent works."}</p>
      </div>
    </header>
    <ol className="receipt-progress-stages" aria-label="Processing steps">
      {[
        { label: "Received", mark: "done" },
        { label: "Read and check", mark: extracting ? "current" : transaction ? "done" : "pending" },
        { label: "Prepare entry", mark: awaiting || booked ? "done" : processing && !extracting ? "current" : "pending" },
        { label: needsReview ? "Review needed" : "Approval", mark: booked ? "done" : awaiting || needsReview ? "current" : "pending" },
      ].map(({label, mark}) => <li key={label} data-mark={mark} aria-current={mark === "current" ? "step" : undefined}><Icon name={mark === "done" ? "checkCircle" : "clock"}/>{label}</li>)}
    </ol>
    {fields.length ? <dl className="receipt-progress-facts">{fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl> : null}
    <div className="row receipt-progress-actions"><a className="btn primary" href={`#/receipts/${run.run_id}`}>{needsReview ? "Review receipt" : "Open receipt"}<Icon name="arrow"/></a>
      <button className="btn ghost" onClick={onReset}>Add another receipt</button>
    </div>
    <details className="small"><summary>Receipt reference</summary><code>{run.run_id}</code></details>
  </section>;
}
