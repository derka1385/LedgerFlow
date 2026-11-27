import { afterEach, expect, it, vi } from "vitest";
import { adoptSession, currentSession, req, signOut, uploadDocument } from "./api";
import type { Session } from "./types";

afterEach(() => vi.unstubAllGlobals());
it("keeps CSRF and idempotency in request headers with same-origin cookie auth", async () => {
  adoptSession({ csrf_token: "csrf-test" } as Session);
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 })); vi.stubGlobal("fetch", fetch);
  await req("POST", "/runs", { body: { document_id: "doc_1" }, idempotencyKey: "stable-key" });
  const [url, options] = fetch.mock.calls[0];
  expect(url).toBe("/api/v1/runs");
  expect(options.credentials).toBe("same-origin");
  expect(options.headers["X-CSRF-Token"]).toBe("csrf-test"); expect(options.headers["Idempotency-Key"]).toBe("stable-key");
  expect(JSON.stringify(options)).not.toContain("Authorization");
});
it("preserves the document upload identity on a retry", async () => {
  const fetch = vi.fn().mockImplementation(() => Promise.resolve(new Response('{"document_id":"doc_1","status":"normalizing","sha256":"hash"}', { status: 202 }))); vi.stubGlobal("fetch", fetch);
  const image = new Blob(["image"], { type: "image/png" });
  await uploadDocument("wb_1", image, "receipt.png", "same-upload");
  await uploadDocument("wb_1", image, "receipt.png", "same-upload");
  expect(fetch.mock.calls.map(c => c[1].headers["Idempotency-Key"])).toEqual(["upload_same-upload", "upload_same-upload"]);
});
it("shows a meaningful proxy error for HTML responses", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>Bad gateway</html>", { status: 502 })));
  await expect(req("GET", "/runs")).rejects.toMatchObject({ code: "INVALID_RESPONSE", status: 502 });
});
it("does not present a backend outage as an unauthenticated session", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response('{"error":{"code":"UNAVAILABLE","message":"Unavailable"}}', { status: 503 })));
  await expect(currentSession()).rejects.toMatchObject({ status: 503 });
});
it("keeps the CSRF token when logout fails, so the user can retry", async () => {
  adoptSession({ csrf_token: "retain-csrf" } as Session);
  const fetch = vi.fn().mockResolvedValueOnce(new Response('{"error":{"message":"Unavailable"}}', { status: 503 })).mockResolvedValueOnce(new Response("{}")); vi.stubGlobal("fetch", fetch);
  await expect(signOut()).rejects.toMatchObject({ status: 503 });
  await req("POST", "/runs", { body: {} });
  expect(fetch.mock.calls[1][1].headers["X-CSRF-Token"]).toBe("retain-csrf");
});
