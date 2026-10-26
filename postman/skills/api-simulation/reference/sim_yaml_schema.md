# `.sim.yaml` reference

Read this when writing or debugging a `.sim.yaml` by hand.
`postman simulation create` writes the same shape; the Postman app adds
`id:` fields, which a local run ignores.

```yaml
simulation: checkout-dev               # required: the name
routing: path                          # path (default) or header
mocks:                                 # required: one entry per member
  - name: catalog                      # optional display name
    routeKey: catalog                  # lowercase letters, digits, - and _
    origin:                            # optional: hostnames, for --proxy
      - catalog.internal.example.com
    path: postman/mocks/catalog        # a mock's folder, config.yaml or handler
    scenarios:                         # optional: conditions, below
      - overrides:
          conditions:
            latency: { delay_ms: 250 }
```

Run the `.sim.yaml` rather than a simulation id: a run by id drops every
member's conditions (CLI 1.70.0–1.73.0), and `--proxy` takes no id at all,
since the file is what declares the hostnames.

`simulation create` writes each `path:` relative to the repository root, the
directory holding `postman/`, and puts the simulation in a folder of its own
(`postman/simulations/checkout-dev/checkout-dev.sim.yaml`) so its
`<name>.context.md` sits beside it; the app records that document in a
`context:` ref. Reading is broader than writing — a path relative to
`postman/simulations/`, to the file, absolute or `~/`, naming the folder or
the manifest inside it, all resolve — and an unresolvable one names every
directory it looked in.

## Conditions

| Condition | Field | Effect |
| --- | --- | --- |
| `latency` | `delay_ms` | Holds each request that long, then serves it. |
| `error` | `status_code` (400–599) | Every request gets that status as JSON, with `"scenario":"error"`. |
| `rate_limit` | `requests_per_minute` | Requests over the limit get `429` and `Retry-After`. |
| `chaos` | `failure_rate` (0–100), optional `status_code` | That share of requests, at random, get `500` or that status. |

- A condition covers every route on its member. To fail one endpoint while
  its siblings succeed, give that endpoint a mock of its own.
- They run in a fixed order (`latency`, `error`, `rate_limit`, `chaos`), and
  the first to fail a request ends it, so set one failure at a time,
  optionally with `latency`.
- An unknown condition name is ignored silently, so a misspelling injects
  nothing. `overrides.bypass` prints a warning and is ignored.
- A `latency` request is served and logged, with a `duration` that leaves
  out the delay.

## `origin`

The hostnames a member answers for under `--proxy`, and the only thing that
decides which member a proxied request reaches.

`simulation create` copies `origin` from the mock's manifest
(`origin: api.stripe.com`, a string or a list).

A scheme and port are stripped (`https://API.Stripe.com:443` →
`api.stripe.com`). An unmatchable value — a path left on a copied URL, a
wildcard — is warned about and skipped, leaving the member working; two
members claiming one hostname fails the run. A member whose mock declares
none has no `origin` key, since `origin: []` would reach the actual service instead of the mock.

Under `--proxy` the members run on throwaway ports, so a manifest's `port` is
ignored.

## The log (`--output ndjson`)

One JSON event per line on stdout; notices go to stderr, so keep them apart.

- `listening`: every member has started; a member that fails to start
  stops the run with `Error: …` and exit code 1.
- `request`: one per request a member served.
- `summary`, on stop: `requestsServed` (under 400), `requestsFailed` (400
  and up), `uptimeMs` and `signal`. Injected failures and the simulation's
  own `400`, `404` and `502` aren't counted.
