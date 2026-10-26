# What Postman performance testing supports (the import target)

Grounded in the `postman-cli`, `performance-test-api`, and `postman-performance-test` source — not the marketing docs. This is the ceiling an import maps onto. When JMeter asks for something not here, it is reported, never faked.

## `postman performance run` CLI flags that matter for import

| Concern | Flag | Notes |
|---------|------|-------|
| Virtual users | `--vu-count <n>` | default 20; cloud runs enforce a **minimum of 10** |
| Duration | `-d, --duration <minutes>` | **minutes**, not seconds; default 1; cloud ceiling ~120 min (plan-gated) |
| Load profile | `-p, --load-profile <p>` | one of `fixed`, `ramp-up`, `spike`, `peak`; default `ramp-up` |
| Data file | `--data-file <path>` | JSON array or CSV; **local runs only**; distribution is forced to `random` |
| Dataset | `--dataset-id` + `--dataset-view-id` + `--dataset-distribution` | cloud path; distribution `round-robin`/`fixed`/`random` |
| Pass/fail | `--pass-if "<fn>(<metric>, <value>)"` | **single, not repeatable** |
| Environment | `-e, --environment <id>` | |
| Setup/teardown | `--setup-collection` / `--teardown-collection` | run **once** before/after — not concurrent load |

There is **no** `--load-segments`, no `--stages`, no `--iterations`, no think-time flag. A latent YAML "stages" schema exists in the CLI repo but is not wired to the command — do not target it.

## Load profiles

Four named shapes only, each derived from `(vu-count, duration)`:

- `fixed` — constant VUs.
- `ramp-up` — ramps from 25% to full over the first quarter.
- `spike` — low baseline, one spike to full mid-run, back down.
- `peak` — baseline, ramp up, hold, ramp down.

JMeter custom ramp curves, stepping schedules, and arrival-rate shapes **cannot be reproduced**. Pick the closest of the four and report the approximation. Rule: any ramp/stepping/concurrency/ultimate/arrivals group → `ramp-up`; a flat group with zero ramp → `fixed`.

## `--pass-if` metrics and operators

- Functions (operators): `less_than`, `greater_than`, `less_than_eq`, `greater_than_eq`.
- Metrics (CLI): `avg`, `p90`, `p95`, `p99` (ms); `error_rate`, `failure_rate` (%); `rps`.
- **Server-side (cloud) accepts a narrower set**: `responseTime.average/p90/p95/p99`, `throughput`, `errorRate`. `failure_rate` is local-only — if you emit it, note it won't gate a cloud run.
- Only one condition per run. A JMeter Duration Assertion is the only clean source (→ `less_than(p95, <ms>)`); otherwise suggest `less_than(error_rate, 5)` and tell the user it's a default.

## Scripts under load

- Pre-request / test scripts run per VU per iteration via `postman-runtime`.
- `postman.setNextRequest(...)` **is supported** — flow control within one VU's iteration works.
- Vault access **in scripts** is disabled; per-request timeouts are forced to infinite; each VU gets its own cookie jar.
- Known engine caveat: mutating `pm.request` inside a script can bleed across VUs. `pm.iterationData` / `pm.variables` are correctly isolated. Avoid importing JMeter logic into `pm.request` mutation.

## Data

- One `--data-file` (JSON array of objects, or CSV) per run. Multiple JMeter CSV Data Sets must be merged or a primary chosen.
- Rows map to VUs/iterations; rows < VUs repeat. The CLI CSV parser is a naive comma split — **no quoted-field/escape support**, so JMeter CSVs with embedded commas/quotes need cleaning.

## Hard limits to encode in every import

1. One collection, repeated across VUs. **No concurrent thread groups.**
2. Time-based, not iteration-based. **Loop counts → duration.**
3. One `--pass-if`.
4. **No think time** — timers are not reproduced; each one is reported.
5. **HTTP(S) only.**
