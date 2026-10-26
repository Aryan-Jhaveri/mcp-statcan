---
name: api-mocking
description: Finds, builds, runs and publishes a stand-in for one API — the owning team's published mock when there is one, otherwise one built from its spec or collection that behaves like the real API, stateful when callers write then read. Use when something needs an API that isn't built or reachable yet (a frontend, client or demo), when other teams should build against your API before it ships, or when asked to mock an API or fake a backend. To run and test your own code against the services it calls, use api-simulation. Covers `postman mock` and `postman dependency add mock`.
---

# API Mocking

A mock is a folder, `config.yaml` plus a handler such as `default.js`, that
answers like an API. The handler is a Node HTTP server that calls
`listen(process.env.PORT)`. It loads as CommonJS even in an ESM project, so
`import` fails: use `require`. The same mock lives in your repo
(`postman/mocks/<name>/`, run with `postman mock run`, no sign-in needed),
in a Postman workspace after `postman mock push`, where other teams pull it
from, and on a mock server after `postman mock deploy`, for callers that
can't run it themselves.

Several APIs at once, for a service, a frontend or a test suite? Use
`api-simulation`, which gets each member's mock here.

## Use the owner's mock first

When the API belongs to another team, look for their published mock before
writing one: theirs encodes their contract and their service's state; yours
encodes a guess. It needs `postman login`; signed out, build one and say the
owner search was skipped.

1. Find the owner's workspace with `postman search workspaces "<service>" -o json`.
   Name the service plainly, as your code does, not by what it returns: a
   description matches lookalike services. Prefer a Git-connected workspace
   (`isGitConnected`) named for that service.
2. List its mocks with `postman mock list -w <workspaceId> --json`.
   `postman search mocks` misses some, and its `classicMock` results only
   replay a collection's saved examples: `postman mock` can't pull or run
   them, so call one at `https://<mockId>.mock.pstmn.io` with
   `postman request`, or generate a code mock from its collection. A
   same-named mock in another workspace isn't the owner's.
3. Pull it with `postman dependency add mock <mockId>` and use it as it is.
   Never edit `postman/.dependencies/`: `dependency update` overwrites it,
   so copy a mock to `postman/mocks/` to change it. A pulled copy loses
   `interceptRequests`, so fork one whose handler reads `req.body` or relies
   on sessions. A mock is code that runs as you; pull only from workspaces
   you trust.

## Or build one that behaves like the real API

Callers shouldn't be able to tell the difference on the paths they use. A
mock that returns invented JSON passes your tests and fails against the
real service.

- **Start from the contract.** `postman mock generate <spec or collection>`
  writes each documented response. It's a replay: a `POST` and a later
  `GET` share nothing, and it accepts any request, so a call that breaks the
  contract still gets its answer. `x-mock-response-code` picks only a
  documented status; any other code gets the default 200, so put the errors
  callers handle (the unknown-id 404, the conflict 409, the bad-input 400) in
  the contract. From a spec
  it serves the server URL's base path (`/v2/...`); from a collection,
  routes start after the base-URL variable. `--update` regenerates the
  handler and overwrites your edits. With no contract, write it from how
  your code calls the API and say what you assumed.
- **Set `interceptRequests: true` in `config.yaml`.** Without it `req.body`
  and `req.query` are undefined, `x-mock-session` is ignored, and a throw in
  an async handler kills the mock instead of returning a `500`.
- **Make it stateful when callers write then read.** Keep records in
  `pm.state`, seed them on first use, add a reset route so a test can start
  clean, and answer an unknown id with the real 404. Every `mock run` starts
  empty.
- **Know who shares state.** Locally, all callers share one state unless
  each sends `x-mock-session: <id>`. A mock server deployed from the CLI
  isolates each caller: one that keeps neither the same `x-mock-session` nor
  the `pm_mock_session` cookie starts from the seed on every request, so its
  `POST` and later `GET` never meet.
- **Scenarios** are named handlers in `config.yaml`'s `scenarios` list, picked
  per request with `x-mock-scenario: <name>`. An unknown name falls back to
  the default locally but is a `404` on a mock server.

## Check it against the contract

`postman mock run` prints the URL it bound; a busy configured port moves
unless you pass `--port`, so take the URL from that line. Nothing reloads:
restart it after an edit.

A mock checked against the handler you just wrote proves nothing, so call
it with requests from the contract: `postman request`, or the API's
collection with
`postman collection run <collection> --use-mock "{{baseUrl}} mock:postman/mocks/<name>"`
(`--mock` alone only starts it). That form replaces the variable's whole
value, base path included, so a mock generated from a spec that serves
`/v2/...` answers `404`; start that one with `--mock <path> --port <n>` and
pass `--env-var "baseUrl=http://localhost:<n>/v2"`. To check your own calls
against a contract, compare each one, from the code or a simulation log,
with the spec; the mock won't reject a wrong one.

## Publish it for other teams

- **Push it to the service's own workspace,** the one this repo is linked
  to or the one the user names, never one chosen by name match: other
  teams' simulations look there. Signed out, the push fails but the local
  mock still works; build it, say so and ask the user to sign in. Keep it
  honest: change the mock in the same PR as the API and run the API's
  collection against it.
- **Deploy only when a caller needs a URL.** The server takes a slug of 3–32
  lowercase letters, digits and single hyphens, starting and ending with a
  letter or digit; the CLI accepts more, and its default can be too long.
  It's private: callers send an API key as `x-api-key`, or, if they can
  view the workspace, an access token as `x-access-token`. Deploying needs a paid plan; a team's first
  server can take minutes to answer, and teams that review deploys hold them
  for approval. Each later `push` changes what every caller of the server
  gets, so treat it as a release, not a backup.
- **Write it for where it runs.** A mock server runs each scenario as one
  file with Node's built-ins, not `fs` or `child_process`: no local
  `require`s, no `pm.mock` examples, no environment, no console output, and
  no caller `authorization`, `cookie` or `x-api-key` headers. A mock that
  relies on any of these works locally and breaks once deployed.
- **Ask before `--public`.** It serves the mock and its data to anyone with
  the URL, and a scripted redeploy can't make it private again.

## Before you say it's done

A mock isn't done because it started. Call it: a documented error comes
back, a valid scenario changes the response, a `POST` then `GET` shows state
if it should. Say where it runs and who can call it, where it lives, and
what you assumed.
