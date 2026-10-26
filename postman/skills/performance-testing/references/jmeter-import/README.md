# Importing a JMeter `.jmx` into Postman

> Reference for the `performance-testing` skill. Import the plan, review the report, then the result is an ordinary performance run.

Turn a JMeter test plan into three artifacts:

1. **Postman Collection v2.1** — requests, flow, headers, auth, variables, extractors, assertions.
2. **Performance config** — VU count, duration, load profile, data file, `--pass-if`, and the exact `postman performance run` command.
3. **Import report** — what imported exactly, what was approximated, what needs manual work, what is unsupported.

There is no importer to run: you read the `.jmx` and build these yourself. The files next to this one are the algorithm:

- `mapping-table.md` — what each JMeter element becomes, and how faithfully.
- `postman-perf-capabilities.md` — the hard limits of the import target.
- `script-translation.md` — Groovy/BeanShell → JS, and the JS templates for extractors and assertions.
- `import-report.md` — the report's shape.

## When NOT to guess

Postman performance runs do not support everything JMeter does (see `postman-perf-capabilities.md`). Never invent a Postman feature to cover a JMeter one. If something can't import, it goes in the report's "Needs manual work" or "Not supported" section — that is a correct outcome, not a failure.

## Workflow

### 1. Walk the plan

JMX has one structural rule: every element is followed by a sibling `<hashTree>` holding its children. Walk those pairs. A config element (Header Manager, Auth Manager, HTTP Defaults, extractor, assertion) applies to every sampler in its subtree; the same element inside a sampler's own hashTree applies only to that sampler. For a large plan, work one thread group or controller at a time.

### 2. Apply the JMeter semantics

These are easy to get subtly wrong:

- **Implicit HTTP success** — JMeter fails a sample on HTTP ≥ 400 even with no assertion. Every request gets the default 200–399 `pm.test` from `script-translation.md`, **unless** it has a Response Assertion whose `test_field` is `response_code` or `response_message`, or any assertion with `assume_success=true` (Ignore Status). An assertion on the body (`response_data`) does not suppress it.
- **Port 0 / -1** → "use protocol default" → omit from the URL.
- **Full-URL path** — if `HTTPSampler.path` starts with `http://` or `https://`, use it verbatim and ignore domain/port.
- **HEAD / TRACE arguments** — JMeter doesn't send separate parameters as a query for these; drop them and note it.
- **Headers** — in-scope Header Managers merge; the nearer/last value per name wins, and the collapse is reported. Keep inherited headers even on a GET (JMeter still sends them).
- **Variables and functions** — `${var}` → `{{var}}`; `${__UUID}` → `{{$guid}}`, `${__time}` → `{{$timestamp}}`, `${__Random(..)}` → `{{$randomInt}}`, `${__RandomString(..)}` → `{{$randomAlphaNumeric}}`.
- **Extractors and assertions** — extractors become `pm.collectionVariables.set` in the test script, assertions become `pm.test`. Use the templates in `script-translation.md` so every import produces the same code.
- **Load** — VUs = `num_threads`; duration (minutes) = round(`ThreadGroup.duration` seconds ÷ 60), minimum 1; profile = `ramp-up` if `ramp_time` > 0 or it's a plugin/concurrency group, else `fixed`. Loop counts become duration (there is no iteration count). One `--pass-if` only: a Duration Assertion → `less_than(p95, <ms>)`, otherwise default to `less_than(error_rate, 5)`.
- **Timers, concurrent thread groups, non-HTTP samplers** → not supported. List them in the report; never fake them.

### 3. Handle what needs judgment

- **JSR223/BeanShell pre/post-processors** — translate to a prerequest/test script with `script-translation.md`. Mark anything you're unsure of with a `// REVIEW` comment and list it under "Needs manual work".
- **JSR223/BeanShell samplers** (no HTTP) — decide with the user: delete it, fold its logic into an adjacent request's script, or replace it with a real request.
- **XPath / CSS extractors** — the sandbox has no XPath/CSS engine. Rewrite against the JSON body if the response is JSON, use `xml2js`/`cheerio` via `require(...)` (confirm availability), or drop it with a note.
- **Complex JSONPath** (wildcards, filters, recursion) — rewrite as explicit property access in the test script.

### 4. Validate the collection

Confirm the collection is valid v2.1 JSON and that **every `event` script parses as JavaScript** (`node --check` each `exec`, or equivalent). A syntax error in a script is invisible in the file and only surfaces when the perf run executes that request, mid-load.

### 5. Write the report

Fill in `import-report.md`'s sections and counts so the report matches the collection you're handing off.

### 6. Hand off the perf config

The command needs a collection UID, so the collection must be in a workspace first. The `--pass-if` value is a suggestion unless the JMeter plan had a Duration Assertion, so surface the VU/duration/profile/pass-if choices for the user to adjust.

### 7. (optional) Publish to a Postman workspace

Only on explicit user consent — and **never make the user paste a workspace ID**. Pick the destination like this:

- **If the current folder is already a connected workspace** (the usual headless case), use it — `postman workspace push` targets the workspace bound to this directory, no ID. Just tell the user which one.
- **If the user named a workspace** (by name), resolve it with `postman workspace list --json` and match.
- **Otherwise present a choice, don't demand an ID.** Run `postman workspace list --json`, show the **names**, and ask the user to pick one *or* create a new one:
  - **pick existing** → connect it once with `postman workspace pull <id>` (ID taken from the list), then push.
  - **create new** → the CLI has no `create`; make it via MCP `createWorkspace` (or the Postman app), then `pull` and push.
- **Get the imported collection into the bound workspace before pushing.** The import is a standalone v2.1 `*.postman_collection.json`; a pulled workspace is a git-native v3 tree. After `pull`, bring the file in with `postman collection migrate <file>.postman_collection.json` into the workspace's collections directory (check `postman collection migrate -h`), then `postman workspace push`. Pushing a folder that has no collection in its tree uploads nothing.
- **Push through the CLI, not MCP.** MCP `createCollection` drops each request's URL (requests land blank); use MCP only if the `postman` binary genuinely can't be installed, and repair URLs afterward.
- Interrogate `postman <cmd> -h` for exact flags — the help is authoritative, this file is not.

Smoke-test with `postman collection run` — the **same runtime that executes the perf test**, not a generic client — so the request is proven under the variable/auth resolution it will actually run under. Then wire the returned UID into the perf command.

## Scope limits (hard facts, verified against the CLI/engine code)

- Performance runs execute **one collection repeated across VUs**. Multiple thread groups cannot run concurrently in a single run.
- Runs are **time-based**, not iteration-based. JMeter loop counts become a duration.
- `--pass-if` is a **single, non-repeatable** condition. Extra assertions stay as `pm.test` in scripts.
- **No think time.** JMeter timers are not reproduced; each one is reported.
- Only **HTTP(S)** samplers import. JDBC/FTP/LDAP/Java/TCP/Debug/Dummy samplers are reported as skipped.
