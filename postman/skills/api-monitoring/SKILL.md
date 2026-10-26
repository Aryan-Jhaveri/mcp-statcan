---
name: api-monitoring
description: Use when setting up recurring API checks, running or diagnosing a Postman Monitor, changing its schedule, or reaching private APIs through a self-hosted runner. Reuses collection assertions to detect live regressions and traces failures to individual run evidence. Use for requests such as "check this API every minute".
---

# API Monitoring

A monitor turns a saved collection into recurring evidence about a live API.
It can catch behavior that changes after deployment or between developer
sessions, but only if its assertions, environment, and execution location
exercise the guarantees users depend on.

1. Reuse the collection's meaningful assertions before scheduling it. A
   request returning 200 is a weak health signal if the response can violate
   the contract. Check auth, target environment, and write side effects; use
   **api-testing** to establish what the collection actually verifies.
2. Choose cadence, timezone, execution location, and alert recipients from
   the operational need. `postman monitor create -c <collection-id>` uses
   the linked workspace unless one is supplied. Inspect command-specific
   `-h` and available service options for supported schedules and limits.
   Creation starts an immediate run by default; `--no-run-now` avoids that
   when only scheduling was requested. A schedule expressed in the host's
   default timezone can fire at the wrong operational time.
3. Choose a Postman region for a reachable public API. Use a self-hosted
   runner when the target is reachable only inside the user's network;
   running one adds infrastructure to maintain. `postman runner regions`
   provides valid hosted locations and `runner list` provides registered
   private runner IDs. `monitor create/update --runner` accepts either;
   multiple locations help distinguish API failures from regional reachability.
4. Preserve monitor identity when updating schedule or run settings.
   `monitor update` cannot change its collection or environment and does not
   pause it; use `pause`/`resume` for that. A different collection/environment
   requires a replacement, so plan the handoff before deleting the old
   monitor and its continuity. Permanent deletion needs explicit intent.
5. Use `postman monitor run <id>` for an immediate verdict, such as after a
   deploy. `--async` returns a job handle when the caller need not wait.
   The CLI timeout caps waiting, not execution; after a timeout, inspect
   the submitted job instead of sending duplicate traffic or reporting failure.
6. Diagnose at the level of the evidence. `monitor jobs list <monitor-id>`
   finds jobs, `monitor jobs get <job-id>` shows terminal state and regional
   outcomes, and `monitor runs get <run-id>` shows assertions within an
   attempt. A failing region, a connection error, and a failed assertion
   imply different fixes. Preserve normal exit-code failures for CI gates.

For discovery, `monitor list` supports workspace and collection filters;
use its returned cursor for pagination rather than offset. Its runner filter
is for a self-hosted ID and cannot be combined with other filters; a page-local
name filter does not establish absence across all pages.

For a private runner, use `runner start` with the registered ID and key and
verify that it connects before assigning runs. Inspect its help for proxy,
private CA, residency, and health-metric options only when the network requires
them. Runner activity is reported by default; `--no-report-events` disables
that reporting when the task requires it. Use **bootstrap** for unresolved
authentication rather than placing runner keys in repository files.

## Verification

Report the actual monitor configuration or terminal job/run outcome, including
where it executed and which checks failed. A created monitor, accepted job,
or connected runner alone does not prove the API passed its health checks.
