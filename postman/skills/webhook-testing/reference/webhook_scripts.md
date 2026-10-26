# Webhook scripts

Recipes for the `onEvent` script that `postman webhook scripts set` uploads.
Each delivery runs the script in a fresh Postman sandbox, with the incoming
request in `pm.request`. `pm.test` results appear in
`postman webhook requests describe <webhookId> <requestId>`, and the
`console.log` output appears with `--verbose`.

```bash
postman webhook scripts set <webhookId> ./webhooks/github-on-event.js --event onEvent
```

## Contents

- [How webhook scripts behave](#how-webhook-scripts-behave)
- [What a script can use](#what-a-script-can-use)
- [Asserting on the payload](#asserting-on-the-payload)
- [Signature checks](#signature-checks): GitHub, Stripe, Slack, any HMAC

## How webhook scripts behave

- **`onEvent`** runs when a request arrives, before Postman forwards or
  responds. Use it to validate the payload, verify the signature, or modify
  the request. **`onResponse`** runs after Postman has responded to the
  sender. Use it for logging and follow-up work from your local responder
  or the configured forwarding endpoint.
- **The file in the repo is the only copy you can read.** The CLI has
  `scripts set` but no command that reads a script back, and a second `set`
  replaces the first. Commit the script beside the handler it guards, and set
  it again after you edit it. The file can be JavaScript or TypeScript.
- **No state carries over between deliveries.** A script can't remember which
  event ids it has already seen, so test duplicate handling in the handler, by
  replaying a request twice.
- **Secrets come from the linked environment.** Read a signing secret with
  `pm.environment.get` and never write it into the file. An environment is
  linked to a webhook in its settings in the Postman app. See the `variables`
  skill for where a secret belongs.
- **Results are per delivery.** The console output that `--verbose` shows is
  capped at 25 KB per event.
- **A script is a test, not your handler's guard.** Postman doesn't document
  that a failing `pm.test` stops the request from being routed. Your handler
  verifies signatures itself, whatever the script reports.

## What a script can use

| Available | Not available |
| --- | --- |
| `pm.request.headers.get(name)`, `pm.request.body.raw` | `pm.globals`, `pm.collectionVariables`, `pm.iterationData` |
| `pm.test`, `pm.expect` | `pm.execution.setNextRequest`, `pm.visualizer` |
| `pm.environment.get`, from the environment linked to the webhook | State that lasts beyond one delivery |
| `require("crypto-js")` and other packages, from the Package Library, npm or JSR | |
| `pm.execution.runRequest`, to run a saved collection request | |

Parse and hash `pm.request.body.raw`. Postman keeps the body exactly as the
sender sent it, and every signature scheme below is computed over those exact
bytes. A body that was parsed and serialized again fails the check even when
the JSON is the same.

## Asserting on the payload

Write down the contract the handler depends on. A test fails on the first
delivery that breaks it, instead of when the handler happens to crash.

```javascript
// Just a reference based on expected payload, it can be of a different data type as well.
const event = JSON.parse(pm.request.body.raw);

pm.test("is a JSON event with an id and a type", function () {
    pm.expect(event).to.have.property("id").that.is.a("string");
    pm.expect(event).to.have.property("type").that.is.a("string");
});

pm.test("is an event this handler subscribes to", function () {
    pm.expect(["payment_intent.succeeded", "payment_intent.payment_failed"])
        .to.include(event.type);
});
```

## Signature checks

Postman also has signature-verification presets for Stripe, GitHub and Slack
in the Postman app. Use a script when you want the check in a file that can be
reviewed, or when the provider has no preset. Read the secret from the linked
environment. A secret pasted into the script ends up in the repo and in the
webhook's configuration.

### GitHub

`X-Hub-Signature-256` is `sha256=` followed by the hex HMAC-SHA256 of the raw
body. There's no timestamp, so a replayed delivery still verifies.

```javascript
const CryptoJS = require("crypto-js");

const secret = pm.environment.get("github_webhook_secret");
const expected = "sha256=" +
    CryptoJS.HmacSHA256(pm.request.body.raw, secret).toString(CryptoJS.enc.Hex);

pm.test("GitHub signature matches the body", function () {
    pm.expect(pm.request.headers.get("X-Hub-Signature-256")).to.equal(expected);
});
```

### Stripe

`Stripe-Signature` is `t=<unix seconds>,v1=<hex>[,v1=<hex>…]`. Stripe signs
`<t>.<raw body>` with the endpoint's whole `whsec_…` secret, prefix included.
More than one `v1` appears while a secret is being rolled, and any one of them
can match.

```javascript
const CryptoJS = require("crypto-js");

const secret = pm.environment.get("stripe_webhook_secret");
const fields = pm.request.headers.get("Stripe-Signature").split(",");
const t = fields.find(f => f.startsWith("t=")).slice(2);
const signatures = fields.filter(f => f.startsWith("v1=")).map(f => f.slice(3));
const expected = CryptoJS.HmacSHA256(t + "." + pm.request.body.raw, secret)
    .toString(CryptoJS.enc.Hex);

pm.test("Stripe signature matches the body", function () {
    pm.expect(signatures).to.include(expected);
});

pm.test("Stripe timestamp is within five minutes", function () {
    pm.expect(Math.abs(Date.now() / 1000 - Number(t))).to.be.below(300);
});
```

The timestamp test fails on a replay of anything older than five minutes. That
failure is expected and doesn't mean the replay is broken.

### Slack

Slack signs `v0:<X-Slack-Request-Timestamp>:<raw body>` with the app's signing
secret and sends `X-Slack-Signature: v0=<hex>`.

```javascript
const CryptoJS = require("crypto-js");

const secret = pm.environment.get("slack_signing_secret");
const ts = pm.request.headers.get("X-Slack-Request-Timestamp");
const expected = "v0=" +
    CryptoJS.HmacSHA256("v0:" + ts + ":" + pm.request.body.raw, secret)
        .toString(CryptoJS.enc.Hex);

pm.test("Slack signature matches the body", function () {
    pm.expect(pm.request.headers.get("X-Slack-Signature")).to.equal(expected);
});

pm.test("Slack timestamp is within five minutes", function () {
    pm.expect(Math.abs(Date.now() / 1000 - Number(ts))).to.be.below(300);
});
```

### Any other HMAC scheme, including your own API's

Start from the provider's documentation, or your own if you're checking the
webhooks your API sends. Find out three things: which header carries the
signature and any prefix it uses, exactly which bytes are signed (the body
alone, or a timestamp or id joined to it), and whether the result is hex or
base64. A mismatch is nearly always one of those three. Use
`CryptoJS.enc.Base64` in place of `CryptoJS.enc.Hex` for a base64 signature.
