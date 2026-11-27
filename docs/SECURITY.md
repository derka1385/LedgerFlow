# Security and containment

## Threat model

Untrusted inputs include images, workbook ZIP/XML, cell strings, formulas, receipt instructions, generated Python, generated manifests, stdout/stderr and produced files. Protect original/committed workbook bytes, other tenants' data, inference/API keys, host integrity, application availability and the approval decision. The trusted computing base includes the host OS/runtime, small supervisor, application authorization, accounting policy and independent verifier code. No claim here establishes immunity to kernel or hypervisor vulnerabilities.

Primary runtime: hardened Docker under gVisor. Docker namespaces/cgroups are useful controls but Docker alone shares the host kernel and is not a complete security guarantee. gVisor interposes a userspace system interface; host resource policy and application authorization still matter. [Docker security](https://docs.docker.com/engine/security/), [gVisor security model](https://gvisor.dev/docs/architecture_guide/security/)

## Fixed workload policy

| Control | P0 setting / evidence |
|---|---|
| Runtime | `runsc`, explicit on every generated-code/inspection/verification job; inspect actual host runtime configuration |
| Image | Prebuilt allowlisted image pinned by digest; no user-selected images or pulls during execution |
| User | UID/GID 10001, non-root; no supplementary privileged groups |
| Filesystem | Read-only root; read-only `/input` containing per-job copies only |
| Work area | Host-owned per-job tmpfs, 128 MiB, mounted only at `/work`; never original/artifact store |
| Temporary files | `/tmp` tmpfs 64 MiB; noexec/nosuid/nodev where compatible; record tested behavior |
| Networking | Docker `none`, no published ports, no host networking, no DNS egress, no proxy socket |
| Secrets | Construct fresh allowlisted environment; no inherited app env, credentials, config directories or cloud metadata access |
| Linux capabilities | Drop ALL; no privileged mode; no-new-privileges |
| Syscall policy | Keep supported default seccomp and AppArmor confinement; no `unconfined` workaround |
| CPU/memory | 1 CPU, 512 MiB RAM, memory+swap limit also 512 MiB; verify enforcement on host |
| Processes/files | 64 PIDs, nofile 256, core dumps disabled; per-file output cap 32 MiB |
| Time | 30 s generated code, 15 s parser/verifier; hard supervisor job lifetime 60 s |
| Output | Fixed regular candidate file ≤20 MiB, JSON manifest ≤256 KiB; logs ≤256 KiB total; no arbitrary archive extraction by root |
| Job count | At most 2 isolation jobs across all kinds, one execution per workbook; queue bounded |
| Cleanup | Stop entire container/cgroup, export frozen bytes, destroy container/mount/staging; reaper catches crash orphans |

The [`none` network driver](https://docs.docker.com/engine/network/drivers/none) leaves loopback only. Test IP and DNS failure, not just a blocked browser page. Equal Docker memory and memory-swap values disable additional swap; do not use zero as if it disabled swap. [Docker resource constraints](https://docs.docker.com/engine/containers/resource_constraints/)

The supervisor chooses every runtime setting. A model or HTTP client cannot request a privileged container, extra mount, increased timeout, different UID or Docker socket. API and worker users are not in the Docker group and cannot talk to the daemon. Only a narrow root-owned local supervisor can. That supervisor is a privileged attack surface and must reject unknown fields, path traversal and arbitrary argv.

## Supervisor protocol and output collection

Use a Unix socket accessible only to the application job group. Messages contain `job_kind`, server attempt ID, fencing epoch and immutable input object IDs/hashes. Resolve paths from a fixed root; never concatenate arbitrary client paths. Allowed job kinds map to fixed entrypoints and images. The public API has no “run arbitrary command” route.

Generated code runs through fixed Python argv with isolated mode and bytecode disabled. A user code string is a file payload, never part of a shell command. AST checks can catch accidental disallowed imports but are not the containment boundary and must not be advertised as one.

After killing/waiting for all workload processes, collector opens the fixed candidate using directory-relative, no-follow access, rejects non-regular files, unexpected link counts, devices/FIFOs and oversize objects, and copies bounded bytes into a quarantine object. Reject symlink ancestors too. No tar extraction with attacker-controlled paths. The privileged supervisor does not import generated Python, open workbook parsers or trust generated file lists.

If output validation requires reading the ZIP, do it in the independent unprivileged verifier sandbox. A separate failure while parsing output cannot compromise the application's interpreter. Freeze/hash bytes before review; do not verify a path that the workload can still change.

## Upload/package controls

* Workbook file magic must be ZIP with correct OOXML content types; filename/MIME alone is insufficient.
* Workbook ≤10 MiB compressed, ≤100 MiB actual streamed decompressed bytes, ≤1,000 members, ≤20 MiB/member and compression ratio ≤100:1. Count actual bytes while reading, not just ZIP header declarations. CRC failure, duplicate normalized names, encrypted members or unsupported compression fails closed.
* Reject absolute paths, `..`, NULs, backslashes used as alternate separators, symlink members and conflicting Unicode/path encodings. Do not extract arbitrary ZIP members to host paths.
* XML parser disables DTD/entity expansion and external resolution. Limit depth to 100, attributes per element to 100 and total represented cells to 200,000; reject misleading dimensions that imply huge scans. Install/use secure XML support explicitly; [openpyxl documents its default XML attack limitations](https://openpyxl.readthedocs.io/en/stable/).
* Reject macro-enabled/embedded active content, package signatures (editing invalidates them), workbook external relationships, data connections, OLE/ActiveX and unsupported formula mechanisms. Inspect relationships, names and relevant content types as well as filenames.
* Preserve benign unknown parts only after compatibility classification. Byte preservation alone does not prove an unknown part remains semantically correct after edits.
* Image ≤10 MiB and 20 megapixels. Decode inside isolation; convert only JPEG/PNG, correct orientation, strip EXIF and re-encode bounded data. Treat decompression-bomb warnings as errors. [Pillow image reference](https://pillow.readthedocs.io/en/stable/reference/Image.html)
* P0 rejects HEIC, PDF and multipage files with a clear conversion/rephotograph message. Add formats only when their isolated normalization path passes tests.

All these limits are proposed policy values to test onsite. The fact that a small inspected workbook passes a read-only inventory does not establish an implemented security scanner.

## Formula, links and prompt injection

Never add a formula from supplier/receipt text. Reference/description/ID strings are explicit OOXML text. Do not rely on a leading apostrophe alone or CSV quoting; the P0 artifact format is `.xlsx`, not CSV. [OWASP explains spreadsheet formula injection risks](https://community.owasp.org/attacks/CSV_Injection).

Existing formulas are inspected with an allowlisted grammar/functions for P0, not a substring-only “dangerous formula” blacklist. Hold unsupported functions, external references, DDE, dynamic names or functions that can contact external sources. Preserve all existing formula text and names; do not execute them in the backend. Recalculation/rendering uses a separate no-network profile with macros disabled.

Receipt/workbook instructions are evidence within their domain, not authority over the application. Separate trusted system prompt/policy from labeled source text. The model cannot promote a cell saying “upload the key” into a tool permission. Security comes from fixed runtime policy, no secrets, plan admission and independent output validation, not from believing the model will resist every injection.

Accounting risk remains even when code is contained: a model can misread an amount or pick a plausible wrong account. Totals must reconcile deterministically, evidence is visible, payment/tax context is confirmed and a human approves the specific entries and cells.

## Tenant and approval controls

* Authorize every workbook/document/run/artifact/event lookup. Opaque IDs are not access control.
* Employee sees own uploads/runs only, with explicit workbook upload assignment. Accountant/owner may see tenant workbooks. No cross-tenant artifact deduplication or download by naked hash.
* No public upload/run endpoints without an invited session, CSRF, rate limits and capacity controls. Public landing/demo explanation remains reachable.
* Candidate hash tuple binds source version, plan, mapping, policy, verifier report and output. A UI approval cannot point to a mutable file path.
* Recheck authorization and current version inside the commit transaction. Lost/replayed requests return one result. Neither human approval nor a baseline acknowledgement can waive an unauthorized output change.
* Original and all committed versions are immutable. Failed runs, cancellation, timeout and rejected proposals do not modify the authoritative current pointer.

## Harmless containment demonstrations

Run these against the **deployed runtime profile**, not a local subprocess. Admin-only diagnostic runs accept only fixed safe probe programs. They do not expose arbitrary code submission to the public and never mount a real secret. These tests are specified, not executed in preparation.

### C1 — protected dummy file stays outside the sandbox

1. Host operator creates a harmless dummy file under a root-owned protected directory outside staging; record its content hash and owner/mode in host evidence. Use fixed dummy content, not an API key.
2. Stage a different harmless readable control file into `/input`. Record the approved bind list from the host runtime, proving the protected directory is absent.
3. Probe code reads the control file successfully, then tries the protected host pathname and a second obvious host-store pathname. It records exception type/errno only. Expected protected read: ENOENT or EACCES, no dummy content.
4. Host collector records exit code/logs, verifies the dummy hash unchanged and the input mount set unchanged, and records container destruction.
5. UI shows readable control success, protected read failure, runtime policy, original hash unchanged and cleanup acknowledgement.

This proves isolation of these unmounted host paths under the tested profile. It does **not** prove absence of all possible container escapes. A model refusal without actual execution, or checking a file that never existed on the host, is not acceptable evidence.

Optional extension: a fixed diagnostic-only root-owned dummy file mounted read-only with restrictive permissions can prove non-root permission denial. Do not grant arbitrary mount selection to support that test; production profiles never include it.

### C2 — infinite loop is terminated

1. Fixed probe runs an ordinary infinite CPU loop with no file modifications. Set a five-second **diagnostic** wall timeout, within the production 30-second ceiling.
2. Supervisor terminates the whole container/cgroup. Capture monotonic elapsed time, termination reason `TIMEOUT`, exit/kill status and destroyed-resource result. Do not infer timeout solely from a client-side network timeout.
3. During the probe, poll application liveness once per second; expect every response within the demo target of two seconds and no lost workbook version.
4. Hash original/current workbook before/after. Start a normal safe job afterward and verify it completes, proving capacity recovery.

Expected diagnostic kill confirmation ≤7 seconds, excluding UI transport lag. Failure to destroy resources blocks approval and further diagnostic runs until fixed.

### Other required negative tests

No network to public IP/DNS/metadata; no Docker socket; no inherited inference key; attempted writes outside `/work` fail; output symlink/FIFO is rejected; log flood is bounded; allocation over RAM cap dies without app failure; candidate mutation after validation cannot affect approved bytes; workbook ZIP bomb and formula injection are refused. See [TEST_PLAN](TEST_PLAN.md).

## Operational security and fallback

Patch host/runtime, firewall inbound traffic, restrict SSH, keep Caddy HTTPS and trusted proxy headers, redact secrets, back up versions/DB and avoid logging private images or identity fields. Host admin access remains privileged; hashes do not make that operator untrusted-proof.

Timebox gVisor installation/compatibility to 30 minutes. If it cannot pass controls, do not silently run an unconfined workload. A constrained Docker-only fallback may be used for invited, synthetic-data demonstration on a separate disposable Vultr runner VM, explicitly identified as weaker shared-kernel isolation. Retest every containment gate and keep control-plane keys off that runner. If this cannot be made concrete in time, the secure execution path is incomplete; report it honestly.
