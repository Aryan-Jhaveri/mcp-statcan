---
name: flows
description: Use when running, deploying, or debugging an existing Postman Flow. Distinguishes local graph execution from a deployed webhook, reuses named input scenarios, and follows a run to the failing block rather than treating an HTTP response as whole-flow success. Use for requests such as "why did this flow fail".
---

# Postman Flows

A Flow saves an API workflow as a graph of blocks. Named inputs make runs
repeatable, deployment makes the workflow callable by other systems, and
block-level run evidence shows where it failed. These benefits come from
different execution paths; choosing the wrong path can produce a passing
result that says nothing about the caller's actual workflow.

1. Choose the artifact the user means. `postman flows run <path>` executes a
   local JSON file; `postman flows trigger <flow-id>` calls the deployed
   webhook, including trigger auth and configuration. Local View and Cloud
   View artifacts are isolated: local files cannot be assumed deployable,
   and `workspace pull` does not download them. The desktop app's Git-connected
   Local View produces those files. Check current local-run entitlement before
   building CI around it; a deployed flow is not a substitute for a different
   local artifact.
2. Resolve hosted IDs through `flows list --workspace <id>`; there is no
   local flow mapping in `.postman/resources.yaml`. Reuse its `workspace.id`
   when applicable or use **api-discovery** for cross-workspace search.
   Resolve ambiguous names before mutating a flow. Use returned flow/run IDs
   verbatim; their spelling is not a reliable validation rule.
3. Reuse a Start-block scenario when the same payload should travel with the
   flow. `-s` supplies payload, headers, and query; explicit headers/query and
   `-i`/`-f` override those values. One-off inputs belong on the invocation.
   For deployed flows with side effects, `trigger --dry-run` lets you inspect
   the resolved call first; keep secrets masked.
4. Deploy when the workflow needs a callable URL. The hosted flow needs a
   Start block configured for an API request trigger and a Response block;
   changing CLI flags cannot repair missing canvas configuration. Resolve
   the path suffix and intended authentication before deploying. Deploy/auth
   changes affect other callers; a scoped user request authorizes that change,
   while unrequested public exposure or auth removal needs consent.
5. Inspect the deployed URL and whether its trigger is enabled. A deployed
   but disabled flow is not ready to receive calls; `flows update <id>
   --trigger on` enables it when intended. If deployment is part of a requested
   run, continue through triggering and capture the Run ID. A request only to
   deploy does not authorize executing unrelated downstream writes.
6. Diagnose from run evidence. A trigger response is the Response block's
   output: HTTP 200 can coexist with another failed block. Use
   `flows get-run --run-id <id>` and add `--logs` or a block filter when the
   summary does not explain it. `flows list-runs --workspace <id> --flow <id>`
   recovers missing run IDs; widen its time range before concluding absence.
7. In CI, preserve the local run's failure exit code and persist its result
   and reports. Connector blocks need `--workspace` even for a local file;
   otherwise failure occurs inside the graph. An access denial across several
   workspaces points toward credentials or entitlement, not an empty flow list.
   Use **bootstrap** for unresolved CLI/authentication setup.

Read [command options](reference/flow_cli_flags.md) for inputs, reporters,
dataset iteration, and flag collisions; check installed subcommand `-h` before
carrying an option between commands.

## Verification

Report which artifact and path executed, its inputs/scenario without secrets,
and the actual result. For a trigger, retain the Run ID; for a failure, name
the failing block and cause. For a deployment, report URL, auth, and enabled
state separately from any execution result.
