---
name: webhook-testing
description: Capture, forward to localhost, replay, and validate webhook deliveries using a reusable public URL. Keep sender configuration across debugging sessions and record arrivals even while local forwarding is stopped, helping distinguish delivery failures from local connectivity issues. Use for implementing or debugging incoming handlers and testing webhooks an API sends, whether or not Postman is mentioned. Example requests include "get payment events to localhost," "inspect a webhook delivery," and "replay an event after a fix"; these illustrate intent, not an exhaustive list or exact phrases to match.
---

# Webhook Testing

`postman webhook` gives a sender a hosted URL,
`https://<webhookId>.webhook.pstmn.io`, that records every request it gets,
with the raw headers and body as they were sent, and forwards each one to a
port on this machine. You don't need a separate tunnel. Two properties shape
how to use it:

- **Reuse the URL across debugging sessions.** It survives new sessions, pause
  and start, so the sender is registered once. Reuse a webhook when the user
  names one or says the sender already posts to one. Use `list` to resolve that
  reference; ask only if the available context still leaves multiple plausible choices.
  Create a new one when a new endpoint is needed. Each new webhook is another
  URL to register and a second event history.
- **Every request is recorded,** including requests that arrive while nothing
  is forwarding. `requests describe` shows a delivery exactly as it was sent.
  After a fix, `requests replay` sends it again, so you don't need the sender
  to fire it again.

The command is singular, and every subcommand needs a signed-in session. Run what you need,
and read `bootstrap` only if a command fails with a setup error such as `Authentication required`.
When all you have is the URL, its subdomain is the webhook id.

For capture or inspection alone, create or reuse a webhook and inspect its
recorded requests; no local service or forwarding to a local port is needed.

Use replays and [scripts](reference/webhook_scripts.md) to validate incoming events.

## Get a sender reaching localhost

When the task is to reach a local handler, check the path from the public URL
meant to be forwarded to the local service:

1. **Make sure the route exists.** A URL that forwards to a local service with no
   matching route only ever returns 404. Check the local service for a handler for
   this event. Add a missing handler when implementing the receiver is part
   of the task. Senders retry, and replay re-sends an identical request, so
   deduplicate using the sender's stable event identifier where available.
   Acknowledge valid, authenticated events that the handler intentionally
   ignores with a 2xx to avoid unnecessary retries; malformed or
   unauthenticated requests still need rejection.
2. **Reuse the existing webhook or create a new endpoint.** To create one,
   use `postman webhook create --title <name>`. When a new endpoint is clearly
   needed, creating it directly avoids an unnecessary discovery step.
3. **Start the local service, then forward to its port** with
   `postman webhook forward <webhookId> <port>`. `forward` runs until it's
   stopped, so run it in the background. For stopping the forwarding process,
   see [Forwarding lifecycle](reference/forwarding.md).
4. **Send one request to the URL, at the route's path.** Check that a 2xx came
   back and that the handler logged the request. `requests list` shows whether
   the request reached the webhook at all, which separates a wrong URL from a
   forwarding or routing problem.

For a connectivity task, one successful probe demonstrates that the tested
path reaches the handler. Sender compatibility and handler correctness need
evidence from actual sender deliveries and relevant scenarios.

## Gotchas / Notes

- **Build the webhook script's test event from the sender's contract, not from your handler.**
  A payload written to match the handler you just wrote only proves the two
  agree with each other. Take it from the sender's documented event schema.
  Better, use a real delivery: send one from the sender's test mode (such as
  `stripe trigger <event>` or a GitHub redelivery), then replay that recorded
  request as you iterate.
- **A permission error needs workspace context.** Check the selected workspace
  and the account's access. A cloned repository may point to a workspace this
  account cannot use. If the intended accessible workspace is known, pass
  `-w`; otherwise ask which workspace to use. Creating another workspace does
  not grant access to the existing one.
- **Some old signed events fail verification on replay, by design.** Stripe
  (`t=` in `Stripe-Signature`) and Slack (`X-Slack-Request-Timestamp`) sign a
  timestamp, and their SDKs reject one older than about five minutes.
  Send a fresh event instead of loosening verification. GitHub's signature has no
  timestamp, so its replays still verify.
- **Confirm before `delete`.** It's permanent, and a sender still registered
  to the URL starts failing. Replay also reaches application code, so account
  for the handler's side effects when choosing which delivery to resend.

## Handing over

For endpoint setup, leave the webhook active so the user can point a sender
at it. For a completed investigation, choose the final state based on whether
the sender still needs the endpoint. Forwarding stops when the `forward`
process does; while the webhook remains active, arrivals are recorded and
can be replayed. Give the user:

- the URL with the route's path;
- for local forwarding, the two commands that start the loop again: start
  the local service, then `postman webhook forward <webhookId> <port>`;
- any changes made to the local service;
- what was verified: the captured delivery or the response and handler receipt
  for a forwarding test.

To validate deliveries automatically with a `pm.test` script, see
[reference/webhook_scripts.md](reference/webhook_scripts.md). To test the
webhooks your own API sends, with a Postman webhook as the subscriber, see
[reference/outbound_webhooks.md](reference/outbound_webhooks.md).
