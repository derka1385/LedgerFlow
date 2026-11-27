# Cost and latency analysis

All prices are USD, excluding tax and unverified account-specific billing. Catalog observations were fetched on **26 November 2026**; costs/latencies below are theoretical estimates, not workload measurements. Raw catalog responses and provenance are in `research/`.

## Verified public rates and uncertainty

The [live model catalog](https://api.vultrinference.com/v1/models) returned these per-million token rates:

| Exact catalog model ID | Input / 1M | Output / 1M | Candidate role |
|---|---:|---:|---|
| `glm-5.3-flash` | 0.10 | 0.35 | Default extraction and ordinary plan/code, pending probe |
| `glm-5.3` | 0.75 | 3.00 | Difficult-case repair, pending probe |
| `qwen3.8-flash-next` | 0.10 | 0.20 | Cheaper alternative, untested |
| `deepseek-v4.1-flash-1017` | 0.15 | 0.60 | Alternative, untested |

The `:free` DeepSeek entry has no explicit pricing entries in this snapshot; absence is not a billing guarantee. Do not choose a free tier as a reliability foundation.

A [Vultr monitoring article](https://docs.vultr.com/support/products/compute/serverless-inference/how-do-i-monitor-the-usage-and-cost-of-my-vultr-serverless-inference-subscription) still quotes a generic 0.55 input / 2.75 output rate. It conflicts with model-specific catalog rates. Treat catalog rates as current published model metadata and confirm actual charges in the account console before forecasting spend. Image tokenization and reasoning-token charging are not established by this preparation.

The [public plans API](https://api.vultr.com/v2/plans?per_page=500) lists `vc2-4c-8gb` at 40/month, 0.055/hour, and `vc2-2c-4gb` at 20/month, 0.027/hour; `sto` is in both location lists. Catalog availability does not reserve capacity. Optional high-performance AMD 4c/8g lists 48/month, 0.066/hour. No GPU VM is needed.

## Per-transaction model

Assumed billable tokens, including an **estimated image-token equivalent**:

| Step | Input | Output | Model | Estimated cost |
|---|---:|---:|---|---:|
| Receipt extraction | 3,500 | 450 | GLM Flash | 0.0005075 |
| Journal, plan and Python | 2,500 | 1,800 | GLM Flash | 0.0008800 |
| Normal total | 6,000 | 2,250 | GLM Flash | **0.0013875** |
| Optional repair | 3,500 | 1,800 | GLM | 0.0080250 |

Assume 10% of transactions need the single stronger repair: expected variable cost = `0.0013875 + 0.10 × 0.008025 = 0.00219` per receipt. This is a planning assumption, not a measured error rate. One extra slot-binding code call using 3,000 input / 1,600 output Flash tokens adds 0.00086 when needed; at 15% incidence it adds 0.000129/receipt. Avoiding that call with deterministic slot conventions is worthwhile for latency, even though dollar savings are small.

One-time onboarding assumption: 9,000 input + 1,500 output Flash tokens = 0.001425 per workbook mapping. Layout-compatible transactions reuse it; structural change requires a new mapping/confirmation. There is no assumed provider prompt-cache discount.

## 10 / 100 / 1,000 transactions per day

Thirty-day month, expected two-call path plus 10% stronger repair; excludes optional slot-binding calls, onboarding, extra format conversions and backup storage.

| Transactions/day | Expected LLM/day | Expected LLM/30 days | One 40/month VM + LLM | If all calls used stronger 0.75/3 pricing, VM + LLM |
|---|---:|---:|---:|---:|
| 10 | 0.0219 | 0.657 | **40.66** | 43.62 |
| 100 | 0.2190 | 6.570 | **46.57** | 76.16 |
| 1,000 | 2.1900 | 65.700 | **105.70** | 401.58 |

Stronger-rate sensitivity uses `6,000×0.75/1M + 2,250×3/1M + 0.10×0.008025 = 0.0120525/receipt`. At the monitoring article's generic 0.55/2.75 rate for all calls, the equivalent expected variable estimate is 0.010175/receipt. These scenarios make the pricing conflict visible instead of silently choosing the cheapest figure.

A 12-hour VM planning estimate is 0.66, or 1.32 for 24 hours, using the published hourly rate; verify actual billing granularity and retained-resource charges. Budget **5–15 total USD for the event** including retries, a spare runner, storage and rehearsal headroom, without treating credits as permission for unlimited usage.

At an assumed 2 MiB total retained payload per transaction, a conservative 30-day storage scenario is approximately 0.59 / 5.86 / 58.59 GiB for the three volumes. The demo receipt policy retains seven days, while committed workbook versions last longer, so actual storage depends strongly on workbook size and version retention. No off-VM backup/object-store cost has been verified; obtain a quote before adding it to a production forecast.

## Latency and capacity targets

| Stage | Unmeasured planning range |
|---|---|
| Normalize image | 0.2–2 s |
| VSI extraction | 5–20 s |
| VSI plan/code | 5–25 s |
| Warm sandbox creation | 0.3–2 s |
| Small workbook execution | 0.1–3 s |
| Verification/export/cleanup | 0.5–5 s |

Plan for roughly **15–60 seconds** to review-ready for a small warm run; repair, account throttling, cold image pulls and queueing can add substantially more. A 300-second active deadline is a failure bound, not an acceptable normal UX target. Human review time is separate. Measure request-to-review p50/p95, not only Python execution time.

An illustrative 40-second pipeline yields 90 runs/hour serially, or a theoretical 180/hour with two independent async runs before contention. The one worker process may manage two async pipelines, but at most two isolation jobs total and one active execution per workbook. At 1,000/day over eight hours, 125/hour consumes about 69% of that optimistic two-pipeline capacity; it is **not a supported capacity claim**. Shared-workbook approvals and stale-base reruns can dominate.

At an assumed 30 seconds per human approval, review alone takes about 5 minutes/day for 10, 50 minutes for 100 and 8.3 hours for 1,000. Higher volume needs a future, carefully designed batch approval/rebase workflow or more reviewers. Do not hide this bottleneck behind cheap token costs.

## Optimization order

Persist mapping and compact evidence, normalize one readable image, use two normal LLM calls, cap code length/context, avoid duplicate jobs, keep pinned images warm and validate deterministically. Cache extraction by tenant + normalized image hash + model/prompt version; cache mapping by confirmed layout/policy revision. Never cache a candidate across different base versions or assume validation survives policy changes. Security and reliable approval matter more than optimizing a fraction of a cent.
