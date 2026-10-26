---
name: api-testing
description: Use when testing an endpoint, running collection assertions, or checking real application traffic against an API contract. Reuses saved requests and reports what live, mocked, or captured-traffic results actually establish. Use for requests such as "test this endpoint".
---

# API Testing

Saved requests preserve the auth, payloads, variables, and assertions that make
an API check reproducible. The useful result is evidence about an intended
guarantee; a successful HTTP exchange alone does not establish correctness.

1. Choose the smallest execution mode that answers the question:

   | Evidence needed | Use |
   | --- | --- |
   | One endpoint with no saved request | `postman request <url>` |
   | Behavior of an existing saved request | `postman collection run <collection-path> -i <request-id-name-or-path>` |
   | Reusable regression checks | `postman collection run <path-or-id>` |
   | Whether a real app's calls match the contract | `postman application test` |

2. Reuse a matching request under `postman/collections/` before reconstructing
   its HTTP fields. Running it through the collection retains inherited auth,
   variables, and scripts. `postman request` takes a URL, not a request YAML
   path; for an unsaved request with an existing payload file, `--body @path`
   preserves that file as the source. See **collection-schema-v3** when
   editing the saved request.
3. Derive assertions from the contract and the behavior at risk. A test that
   merely repeats the current implementation can bless its bug. Preserve
   existing guarantees and add checks for the changed behavior; put reusable
   `pm.test` assertions in the collection so later runs and teammates inherit
   them. Inline `--script-post-request` assertions suit a one-off check.
4. Choose a real or mocked target according to the claim. `--use-mock` lets a
   collection run exercise request and assertion logic without a live
   backend; `--mock` alone only starts one. `--use-mock` replaces the
   variable's whole value, base path included (see **api-mocking**). Passing
   against that mock does not verify the service the mock stands in for.
5. Reuse environment resolution with `-e` and **variables**. Use a CSV/JSON
   file through `-d` for simple iteration; use **datasets** when the inputs
   need queries, joins, or reusable views. Export reports such as
   `-r junit,html` when **ci-integration** needs evidence beyond terminal output.
6. Use `application test` when the application's actual traffic is the subject.
   It runs an existing command, such as `--command "npx playwright test"`,
   captures its traffic, and matches it against collections. `--capture-only`
   instead exports a v3 collection organized by host; that captures behavior
   without validating it. Results are recorded in the connected workspace by
   default; `--report-events=false` keeps the run local when required.

Use command-specific `-h` for supported options and **bootstrap** for unresolved
CLI setup or authentication when using workspace resources. A bare URL or
local collection does not require a workspace binding.

## Verification

Report the target, tested behavior, assertion counts, and exit code. The exit
code reflects failed assertions, not HTTP status alone: a 200 can fail a test.
For application testing, distinguish matching from capture-only mode, and for
mocked runs state which real behavior remains unverified.
