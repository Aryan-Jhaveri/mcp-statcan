# Testing the webhooks your API sends

Here the Postman webhook stands in for a subscriber. Create one with
`postman webhook create`, then register its URL as the subscriber endpoint in
your app, through its config or your subscription API. Trigger the action that
emits the event, with `postman request` or a collection that already covers it
(see the `api-testing` skill). Find the delivery with `requests list` and read
it with `requests describe`.

Check the delivery against the event contract you publish:

- the event type and the body's shape;
- the signature header, recomputed from the raw body with the secret your
  subscriber holds;
- the delivery or idempotency id, which should be unique per event and stay
  the same across retries.

Put those checks in an `onEvent` script so each delivery gets a test report;
see [webhook_scripts.md](webhook_scripts.md). Its last section covers checking
your own signature scheme.

To test retries, the subscriber has to fail. Either set the webhook's routing to
respond with a 5xx in the Postman app (routing isn't a CLI command), or forward
to a local endpoint that returns one. Check that `requests list` records the
failing response status before you read the repeated deliveries as retries.
