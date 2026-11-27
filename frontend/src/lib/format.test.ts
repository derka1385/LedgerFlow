import { describe, expect, it } from "vitest";
import { approvalRequest, mergeEvents, money, parseMoney } from "./format";
import type { DiffResponse, ExecutionEvent } from "./types";

describe("money", () => {
  it("formats integer öre without floats", () => {
    expect(money(125000)).toBe("1,250.00");
    expect(money(1)).toBe("0.01");
    expect(money(8797600)).toBe("87,976.00");
    expect(money(null)).toBe("—");
  });
  it("parses Swedish and English amounts exactly", () => {
    expect(parseMoney("1 250,00")).toBe(125000);
    expect(parseMoney("1,250.00")).toBe(125000);
    expect(parseMoney("1.250,50")).toBe(125050);
    expect(parseMoney("437,5")).toBe(43750);
    expect(parseMoney("0.1")).toBe(10);
    expect(parseMoney("12.345")).toBeNull(); // ambiguous: thousands or decimals
    expect(parseMoney("1,250")).toBeNull(); // ambiguous
    expect(parseMoney("1 250")).toBe(125000);
    expect(parseMoney("12,345.60")).toBe(1234560);
    expect(parseMoney("abc")).toBeNull();
    expect(parseMoney("")).toBeNull();
  });
});

const ev = (sequence: number): ExecutionEvent => ({
  schema_version: "ledgerflow.event.v1", event_id: `evt_${sequence}`, sequence, run_id: "run_1", attempt_id: null,
  event_type: "run.state_changed", state: "EXECUTING", occurred_at: "2026-11-27T10:00:00Z", message: "", data: {},
});

describe("mergeEvents", () => {
  it("dedupes replayed events and keeps sequence order", () => {
    const a = mergeEvents([], [ev(3), ev(1)]);
    const b = mergeEvents(a, [ev(1), ev(2), ev(3), ev(4)]);
    expect(b.map((e) => e.sequence)).toEqual([1, 2, 3, 4]);
    expect(mergeEvents(b, [ev(2)])).toBe(b);
  });
});

describe("approvalRequest", () => {
  it("copies the exact hash tuple from the server diff", () => {
    const diff = {
      base_version_id: "ver_1", base_sha256: "a".repeat(64), candidate_sha256: "b".repeat(64), plan_sha256: "c".repeat(64),
      mapping_sha256: "d".repeat(64), policy_version: "policy_1", validation: { report_sha256: "e".repeat(64) },
    } as unknown as DiffResponse;
    expect(approvalRequest(diff, "approve")).toEqual({
      decision: "approve", base_version_id: "ver_1", base_sha256: "a".repeat(64), candidate_sha256: "b".repeat(64),
      plan_sha256: "c".repeat(64), mapping_sha256: "d".repeat(64), validation_report_sha256: "e".repeat(64), policy_version: "policy_1",
    });
    expect(approvalRequest(diff, "reject", "x".repeat(600)).comment?.length).toBe(500);
  });
});
