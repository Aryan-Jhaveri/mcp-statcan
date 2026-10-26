# Orbit — public API discovery reference

Orbit finds and integrates **public third-party APIs** — weather, payments,
invoicing, messaging, geocoding, calendar, and the like. It is free, needs no
signup and no API key, and works entirely against publicly available APIs.

- REST base: `https://api.buildwithorbit.ai`
- Docs: `https://www.buildwithorbit.ai`

## Implementation

Two REST calls, both `POST`, both read-only (safe to retry). No auth header —
send `Content-Type: application/json` and a JSON body. Optionally identify your
client with `Orbit-Client-Name` (see below). Run search first, surface
candidates, then integrate the chosen ids.

```bash
# Step 1 — search
curl -sS 'https://api.buildwithorbit.ai/v1/search?limit=10' \
  -H 'Content-Type: application/json' \
  -H 'Orbit-Client-Name: claude/opus-4.8' \
  -d '{ "q": "send email via SMTP" }'

# Step 2 — integrate (ids come from the search response, verbatim)
curl -sS https://api.buildwithorbit.ai/v1/integrate \
  -H 'Content-Type: application/json' \
  -H 'Orbit-Client-Name: claude/opus-4.8' \
  -d '{
    "task": "Send a welcome email when a user signs up",
    "resources": [{ "id": "urn:orbit:endpoint:v1:...", "type": "endpoint" }]
  }'
```

Implementation notes:

- A typical search+integrate is ~2,500 tokens and ~15–20s end to end, vs
  ~69,000 tokens for loading a vendor OpenAPI spec.
- One integrate call can span up to 10 resources across different providers;
  batch every endpoint the task needs into a single `resources` array rather
  than making one call per endpoint.
- Auth, request bodies, `Threading`, and `GOTCHAS` come from live public API
  schemas, so take them from the brief rather than from memory.
- `Orbit-Client-Name` is an optional request header (both endpoints, max 128
  chars) that names the calling client/agent for Orbit's anonymous usage
  analytics. The convention is `client/model`, slash-separated —
  e.g. `claude/opus-4.8`, `cursor/composer-2.5`, `codex/gpt-5.6-sol` — or a bare
  client name like `vscode`. Set it to the host agent and model running this
  plugin. It never affects results and can be omitted.

## Step 1 — Search (`POST /v1/search`)

Describe the task, not a provider name. Good: `"send an invoice to a customer"`.
Worse: `"PayPal"`. Provider name is fine to include when it is fixed.

Request body (JSON):

- `q` — the query; max 512 characters.

```json
{ "q": "send email via SMTP" }
```

Query params:

- `limit` — default 10, max 25.
- `cursor` — from `meta.nextCursor`; pagination stops at 40 results.

Returns `data[]`. Each item has:

- `id` — opaque URN. Pass it back verbatim; never construct, shorten, or edit
  it.
- `resourceType` — `endpoint` or `mcp`.
- `name`, `method`, `url`, `description`.
- `evaluateGuide` — how well the endpoint fits the task, including what it
  cannot do.

Hold onto both `id` and `resourceType` — both are required for integrate. Do not
read `meta.total` as a match count; it reports the page size.

## Step 2 — Integrate (`POST /v1/integrate`)

Pass the same task plus every endpoint the job needs (up to 10). Use
`resourceType` from the search result as the `type` field.

```json
{
  "task": "Send a welcome email when a user signs up",
  "resources": [{ "id": "urn:orbit:endpoint:v1:...", "type": "endpoint" }]
}
```

Returns a `taskBrief` covering:

- `FIT` — Fully or Partially (and names the gap if Partial).
- `AUTH` — use the exact header name given; it is frequently not
  `Authorization`.
- `BASE URL`.
- numbered `STEPS` — method, path, every parameter with an example, expected
  responses, `Threading`.
- `GOTCHAS` — read these before writing the client.

## Error handling

Both endpoints are read-only, so retries are safe. Free and unauthenticated is
not unlimited — back off on `429`.

- `400` — invalid input.
- `404` on integrate — no IDs resolved.
- `500` — server error.

If `FIT` is not Fully, say what's missing before writing code. If the brief
names a credential the user doesn't have yet, stop and tell them which one to
get.
