import { describe, expect, it, vi } from "vitest";
import { captureLink, employeeStatus, executionMetrics, pairingLink, safeDocumentUrl } from "./experience";
import { STATE_LABEL } from "./format";
import type { ExecutionEvent, RunState } from "./types";

describe("employee presentation", () => {
  it("covers every accounting state without requiring bookkeeping knowledge", () => {
    for (const state of Object.keys(STATE_LABEL) as RunState[]) expect(employeeStatus(state)).toBeTruthy();
    expect(employeeStatus("NEEDS_REVIEW")).toBe("Additional information needed");
    expect(employeeStatus("COMMITTED")).toBe("Booked");
    expect(employeeStatus("GENERATING_CODE")).toBe("Processing");
  });
});
describe("capture continuity", () => {
  it("never puts a pairing bearer in a query or HTTP path", () => {
    const url = new URL(pairingLink("https://ledger.example/", "secret /?&token"));
    expect(url.pathname).toBe("/"); expect(url.search).toBe("");
    expect(decodeURIComponent(url.hash.slice(7))).toBe("secret /?&token");
    expect(() => pairingLink("http://localhost:5173", "token")).toThrow("HTTPS");
    expect(() => captureLink("http://finance.example", "book")).toThrow("HTTPS");
  });
  it("includes a workbook hint without granting access or preserving old query secrets", () => {
    const url = new URL(captureLink("https://ledger.example/path?old=secret", "wb_123"));
    expect(url.pathname).toBe("/"); expect(url.search).toBe("");
    expect(url.hash).toBe("#/capture?workbook=wb_123");
  });
  it("keeps document previews on the authenticated API origin", () => {
    vi.stubGlobal("location", new URL("https://ledger.example"));
    expect(safeDocumentUrl("/api/v1/artifacts/art_1/download")).toBe("https://ledger.example/api/v1/artifacts/art_1/download");
    expect(safeDocumentUrl("https://attacker.example/receipt")).toBeNull();
    expect(safeDocumentUrl("javascript:alert(1)")).toBeNull();
    expect(safeDocumentUrl("/offline.html")).toBeNull();
    vi.unstubAllGlobals();
  });
});
describe("measured telemetry", () => {
  const event = (sequence: number, event_type: string, data: Record<string, unknown>) => ({ sequence, event_type, data }) as ExecutionEvent;
  it("leaves missing telemetry missing instead of showing zero", () => {
    expect(executionMetrics([])).toEqual({ durationMs: null, tokens: null });
    expect(executionMetrics([event(1, "sandbox.exited", { duration_ms: "150" })])).toEqual({ durationMs: null, tokens: null });
  });
  it("deduplicates SSE replay and sums actual attempts / model calls", () => {
    const rows = [event(1, "sandbox.exited", { duration_ms: 250 }), event(2, "sandbox.exited", { duration_ms: 750 }), event(3, "code.generated", { usage: { total_tokens: 70 } }), event(4, "extraction.completed", { usage: { prompt_tokens: 30, completion_tokens: 20 } })];
    expect(executionMetrics([...rows, rows[0], rows[2]])).toEqual({ durationMs: 1000, tokens: 120 });
  });
});
