---
name: application-testing
description: Sets up, runs, debugs, and interprets results from `postman application test` — the Postman layer that runs your Playwright tests, captures their network traffic, matches it against a collection contract, runs pm.test assertions, and publishes results to Application Inventory. Covers the Postman side of the integration only — not Playwright test authoring or Playwright failures unrelated to capture. Use when the user asks to "set up application testing," "test my application with Postman," "connect my Playwright tests to Postman," "capture network traffic from Playwright," "Playwright tests are running but nothing shows up in Postman," "why isn't application testing capturing anything," "exclude certain requests from capture," "generate a collection from my app's traffic," "set up application testing in CI," "what API coverage do my e2e tests have," "which APIs are my Playwright tests not hitting."
---

# Application Test

## Overview

**Requires a Playwright project in the repository.** Without Playwright e2e tests there is nothing to capture — Playwright is the only supported runner.

`postman application test` does not send its own requests. It:
1. Spawns your Playwright test command (e.g. `npx playwright test`)
2. The capture plugin intercepts network traffic and writes it as artifacts
3. The CLI reads those artifacts, matches each request against your collections, and runs any `pm.test` assertions saved in the matched items
4. Publishes results to Application Inventory in your Postman workspace

The question it answers: **did my app's actual HTTP calls conform to the collection contract?** Not "does this endpoint respond correctly" — for that, use `postman collection run`.

**Application Inventory** is where results are published — a Postman dashboard that records each run's Playwright test results alongside captured/matched/assertion counts, giving you a combined view of test health and API contract conformance across runs.

---

## Prerequisites

**All `postman app` commands must be run from the repository root** — that is where `postman.config.cjs`, `.postman/resources.yaml`, and `postman/collections/` are expected to live.

Assess each prerequisite against the current state of the repository before taking any action. Most will already be satisfied in an established project; only act on what is actually missing.

### Playwright project

This skill applies only when the repository has Playwright e2e tests. Verify that a `playwright.config.*` file exists and `@playwright/test` is listed as a project dependency. If neither is present, stop — there is nothing to capture and this skill does not cover Playwright setup.

### Authentication

Publishing results to Postman requires credentials. Authenticate only when workspace publishing is needed:

- If `POSTMAN_API_KEY` is in the environment, run `postman login --with-api-key "$POSTMAN_API_KEY"`. This is the expected path in CI and agentic contexts.
- If the key is not available, surface the gap to the user — do not initiate `postman login` in an agentic context, as it requires a human to complete a browser flow.

If this run does not need to publish results (local debugging, dry run), authentication can be skipped by passing `--report-events false`.

### Workspace link

Publishing to Application Inventory requires a workspace binding. Check `.postman/resources.yaml` for a `workspace.id`. Reason about whether publishing is actually needed for this task before treating a missing workspace as a blocker:

- If publishing is needed and the workspace is missing, load the `bootstrap` skill to set it up. In a non-interactive context this must be done locally first, then `.postman/resources.yaml` committed.
- If publishing is not needed, pass `--report-events false` and proceed.

### Capture plugin

Network traffic capture requires the `postman-playwright` package to be installed and the Playwright config wrapped with `withPostman()`. Before attempting any setup, check whether it is already configured — `postman app setup-capture --dry-run` shows the current state without touching files.

Decide what action (if any) is needed based on what the dry run reports:

- Already configured → no action needed.
- Not configured → run `postman app setup-capture --yes`. If automatic patching fails (non-standard config export patterns), fall back to manual installation: install `postman-playwright` as a dev dependency and wrap the config export with `withPostman()`.

**Legacy pattern:** If the project uses `attachNetworkCapture()` in spec files instead of `withPostman()`, that is still supported — do not re-run setup. The CLI detects it automatically. Only migrate to `withPostman()` if the user asks to upgrade.

### Server reachability

`postman app test` spawns Playwright, which drives the live application — servers must be running before the command starts.

Check `playwright.config.*` for a `webServer` entry. If present unconditionally, Playwright manages server startup automatically. If absent or conditional (e.g. gated on an env var), verify the servers are reachable before running. If they are not, check `webServer.command`, `package.json` scripts, and any README for the startup command, and surface it to the user.

---

## Running

Before constructing any command, run `postman app test --help` to confirm the available flags for the installed CLI version. Do not guess flag names.

**No `postman.config.cjs` yet** — the first run generates and saves `postman.config.cjs`, writing these choices as the defaults for all future runs. Confirm both with the user before running:

- *Test command*: check `package.json` scripts for a project-specific test command (e.g. `npm run test:e2e`). Present what you find and ask the user to confirm — the CLI defaults to `npx playwright test` when a Playwright config is found, but do not assume that is what they want.
- *Collection*: check `postman/collections/` and list what is available. Ask the user which collection to use. If none exist, ask whether to generate one from captured traffic.

Once confirmed, run `postman app test` with the appropriate flags (e.g. `--target-collection <path>` or `--generate-collection`) — the CLI generates and saves `postman.config.cjs` automatically. Do not write the config file manually.

Running `postman app test` without a collection in a non-interactive context exits with code 2 unless a collection source is provided explicitly.

**`postman.config.cjs` exists** — the config is the source of truth. Run `postman app test` without extra flags. Individual config values can be overridden per-run without editing the file; consult `postman app test --help` for the override flags.

**Capture-only mode** — when the goal is to stage and review traffic before committing a collection manually, there is a mode that skips collection matching and writes captured traffic as a collection to disk. Use this only as a review step, not the normal run path.

---

## Config File (`postman.config.cjs`)

Lives at the **repository root**. The generated file includes comments explaining every field — read it for the full reference. It stays current with the CLI version installed in the repo.

To edit config for common needs:
- **Change the test command** — update `command`
- **Add or change a collection** — update `targets.default.collections`
- **Exclude noisy requests** — add `filters` (urlPatterns, methods, headers)
- **Rewrite URLs before matching** — add `transformers` (config entries that normalize staging/proxy prefixes before the CLI matches captured URLs against the collection)
- **Multiple named environments** — add entries under `targets`

A **target** is a named set of collections + optional environment. The `default` target is used when no `--target` flag is passed. Individual values can be overridden per-run without editing config — consult `postman app test --help` for the override flags.

---

## Debugging

**If a flag in this skill is unrecognized** (e.g. `--yes`, `--generate-collection`, `--dry-run`) or the behaviour described here doesn't match what you see, check the CLI version first:
```bash
postman --version
```
This skill targets the latest CLI release. If the version is outdated, load the `bootstrap` skill for installation and update steps, then re-run. The `--help` output for each command shows the flags actually available in the installed version.

Read the CLI error output first — it names the specific failure and what to fix.

### Requests show "not matched" in the summary table

Run with `--verbose --no-report-events` to see the unmatched URLs without publishing a diagnostic run to Application Inventory. Then:

- Wrong collection selected — check `targets.default.collections` in config or override with the target-collection flag.
- URLs have a staging prefix or proxy path — add a `transformers` entry in `postman.config.cjs` to rewrite them before matching.

---

> **Note — Exit code:** The CLI exits with the **test runner's exit code** (Playwright's), not the Postman assertion pass/fail count. A run where Postman assertions fail but all Playwright `expect()` calls pass will exit 0. If you need CI to fail on Postman assertion failures, check the summary table output or the published results.

---

## Critical Rules

1. **`postman application test` captures traffic; it does not drive requests.** The test runner (Playwright) drives the app; this command observes and asserts. If no test runner is running, nothing is captured.
2. **`not matched` is not a test failure — it is a coverage gap.** Requests the CLI cannot find in a collection run no assertions and do not affect the exit code. A high not-matched count means the collection is incomplete for the traffic the app generates.
3. **Transformers run before matching, not before capture.** The raw URL is stored; the transformer rewrites it for the matching step only. Use this to normalise staging/prod URL differences without losing the original for debugging.
4. **Results are published per run.** Each invocation creates a new entry in Application Inventory. Pass `--report-events false` for dry runs or local debugging you do not want recorded.

## Anti-patterns

- **Capture-only mode is for reviewing traffic before committing to a collection** — use it when you want to inspect what the app generates before deciding on a collection structure. It is not a substitute for `--generate-collection`, which generates, tests, and saves to config in one step when no collection is configured.
- **Do not run `postman app init`** — it is deprecated. `postman app test` runs the same setup on first use.
- **Do not manually write `postman.config.cjs`** — the CLI generates it automatically on first run when you pass `--target-collection` or `--generate-collection`. Writing it by hand bypasses the CLI's generation logic.
- **Do not combine capture-only mode with a target collection** — capture-only skips collection matching entirely; passing a collection alongside it has no effect and signals a misunderstanding of the mode.

## Verification

State captured / matched / not-matched / assertion counts from the summary table. Note whether results were published to Postman (`View results:` URL present) or kept local. If debugging a "not captured" issue, confirm which capture format was detected (Playwright JSON report or legacy NDJSON) and which directory the CLI scanned.

Postman docs: https://learning.postman.com/docs/postman-cli/postman-cli-application/#postman-app-test
