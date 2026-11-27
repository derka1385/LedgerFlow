# Sandbox storage remediation and independent configuration review

## Evidence status — 2026-11-27

The original benchmark records **12/13 on Docker Desktop**, with P13 successfully
writing 256 MiB into a host-backed `/work`. It is historical evidence, not a
measurement of this patch. Neither Docker nor Podman is installed on the current
Mac. Vultr console/browser access and a Vultr SSH destination have not been
provided to this session. **13/13 on Vultr is not established.**

Local verification of the patch:

```text
$ python3 -m pytest -q -rs frontend/dev-mock-api/test_sandbox.py benchmark/test_bench.py accounting/tests/test_accounting.py
38 passed, 7 skipped in 2.37s
```

Six skips require a real Docker daemon/image; one accounting comparison requires
`openpyxl`, absent here. These are source-level/unit and deterministic accounting
results, not runtime containment or Excel application compatibility evidence.
`python3 benchmark/security_evidence.py --help` also completed successfully.

Reviewed implementation: `frontend/dev-mock-api/sandbox.py`, which is the runner
imported by `benchmark/bench.py`. The production supervisor described elsewhere
in the handoff is a specification; it is not present in this workspace. Applying
this patch does not establish that a separately deployed backend uses this policy.

## Implemented storage policy

| Writable area | Enforcement |
|---|---|
| `/work` | Fresh Docker tmpfs per container, 128 MiB aggregate, 4,096 inodes, uid/gid 10001, mode 0700, noexec/nodev/nosuid |
| Python temporary files | `TMPDIR=/work/.tmp`; share the same 128 MiB/inode budget rather than an independent allowance |
| `/tmp`, `/var/tmp`, root filesystem | Read-only; no host temporary-directory bind mounts |
| `/dev/shm` | Separate private Docker shared-memory tmpfs, explicitly 1 MiB |
| `/input` | Read-only per-run copies; 32 MiB/1,024-file input budget; reject path traversal |
| stdout/stderr | Drained continuously, retaining 20,000-byte tails per stream; Docker persistent logging disabled |

The quota is enforced by the kernel on allocation, across files and processes,
including files that are unlinked while still open. It is not a periodic `du`
check or a per-file size limit. Exhausting it returns `ENOSPC`; a program may
catch that exception and continue within its remaining quota. An uncaught write
failure exits Python. Whole-container removal enforces the deadline and releases
tmpfs. This does **not** promise automatic immediate termination of code that
catches `ENOSPC`; storage containment is enforced regardless.

Tmpfs pages also consume the container's 512 MiB memory allowance. Memory+swap is
explicitly limited to 512 MiB. Default Docker device/runtime mounts remain;
inspect the recorded mountinfo rather than describing all mounts as `/work`.

Artifacts are collected while the tmpfs container is alive using isolated Python,
no-follow/nonblocking opens, regular-file checks, and bounded reads: candidate
16 MiB, report 1 MiB. No output directory is bind-mounted back to the host. A
`finally` block removes the whole container and staging directory; cleanup failure
discards artifacts. The former environment-enabled unsandboxed fallback is removed.

## Independent findings

1. **Fixed:** unlimited host `/work` writes; missing aggregate/inode quota;
   Python tempfile incompatibility with read-only `/tmp`; implicitly larger shared
   memory allowance; unlimited in-memory log capture; unsafe host-side artifact
   path reads; host input traversal; optional unsandboxed execution.
2. **Benchmark integrity improved:** P13 now requires explicit `ENOSPC`, not any
   unrelated nonzero exit. Runtime/setup errors cannot count as containment.
   P01 requires a successful network-positive control. Linux control uses
   `host-gateway`; listener binds to host interfaces on Linux for that control.
   Run this test only on the intended runner: the listener is temporarily
   reachable on its randomly allocated TCP port, subject to firewall rules.
3. **Runtime still weaker than the production specification:** this runner uses
   Docker's configured default runtime, not explicit gVisor. The default image is
   a mutable tag. Capture its digest and supply a vetted digest through
   `LEDGERFLOW_SANDBOX_IMAGE`; default seccomp/AppArmor/runtime must be inspected
   on the target. No gVisor claim is justified by these source changes.
4. **Lifecycle/concurrency gaps remain:** no independent host reaper or global
   concurrency admission exists in this development runner. The keepalive has a
   finite lifetime, but a killed supervisor may leave a stopped container record
   and input staging directory. Per-sandbox limits do not bound aggregate host
   consumption across unlimited simultaneous jobs.
5. **Collector isolation limitation:** generated background processes can remain
   alive during in-container collection. Bounded collection prevents host path
   traversal and FIFO/size attacks but is not the specified kill-all-then-export
   production supervisor. Candidate bytes returned to the caller are detached
   bytes, and must still pass the independent verifier and approval protocol.
6. **Legitimate Excel compatibility requires measurement:** the existing policy
   permits 10 MiB uploaded XLSX and up to 100 MiB decompressed content; 128 MiB
   workspace and 512 MiB RAM are plausible budgets, not proof for every such
   workbook. The existing real-sandbox template/writer/verifier suite and
   preservation checks must pass. Test larger representative workbooks before
   expanding the supported envelope.

## Reproduce on the actual Vultr VM

Copy the reviewed source and fixtures to the target runner; install its normal
Python test dependencies (`pytest` and the dependencies used by the accounting
benchmark). Use the existing configured Docker daemon and a vetted Python image;
do not grant the public application Docker access to run this command.

```sh
export LEDGERFLOW_SANDBOX_IMAGE='python@sha256:REPLACE_WITH_VETTED_DIGEST'
python3 -m pytest -q -rs frontend/dev-mock-api/test_sandbox.py benchmark/test_bench.py
python3 benchmark/security_evidence.py --host-label vultr-INSTANCE_ID --output benchmark/results/security-evidence.vultr.json
```

The evidence command refuses to run without Docker/image. It records timestamps,
source SHA-256 values, Docker/daemon versions, image ID/digests, actual live
container HostConfig/mounts, uid/gid, filesystem capacity/inodes, mountinfo,
capability/seccomp process status, the positive network control, all 13 probe
details, quota/inode/temp isolation/artifact regressions, legitimate Excel
execution, and workbook preservation. It leaves historical benchmark results
untouched. Review the JSON before sharing: Docker host configuration contains
operator paths and infrastructure identifiers.

The host label is operator-supplied, **not provider attestation**. Pair the JSON
with the Vultr instance ID/region/OS from the operator's console and an SSH
terminal recording showing the same machine and command. Publish source hashes
and raw JSON alongside any 13/13 headline. Do not treat skipped tests, an
unreachable positive control, an empty suite, or a mocked runtime as proof.
