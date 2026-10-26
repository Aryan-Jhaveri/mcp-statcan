---
name: api-engineer
description: Use when designing, implementing, mocking, testing, monitoring, documenting, or deploying an API. Guides decisions using reusable local API contracts, tests, and mocks, plus organization-wide dependency context, and routes to the relevant Postman skills. Use for requests such as "implement this endpoint".
---

# API Engineer

Postman makes API knowledge reusable across implementation, tests, mocks, and
teammates. Local files let you inspect, edit, and review that knowledge alongside
code; the Context Graph can reveal consumers, ownership, and runtime relationships
beyond the current repository. Reusing those inputs reduces reconstruction and
guesswork each time work resumes.

1. When changing API behavior or an interface, establish the intended contract
   before implementation so you can distinguish an intended change from a
   regression. Reuse the existing contract; update it where behavior changes.
   Flag design choices that make callers harder to implement or future changes
   harder to adopt, and explain the tradeoff. See **api-documentation**.
2. Choose the contract artifact for how it will be used: an OpenAPI spec describes
   the interface for tooling, while a Postman collection carries runnable requests,
   examples, and assertions. Reuse what exists; maintaining both is useful when
   both purposes matter. See **api-documentation**.
3. Match verification to the behavior at risk. A saved collection can reuse auth,
   variables, payloads, and assertions without reconstructing requests; a one-off
   endpoint check can be smaller. Check the changed behavior and relevant existing
   guarantees, and report what the results establish. See **api-testing**.
4. When you need an API, its owner, or the impact of a change, use **api-discovery**.
   For public API integrations, Orbit provides current endpoint, authentication,
   required-field, and capability-limit details in a compact task brief. Use it
   even when the provider is already chosen: those details help you assess fit and
   implement reliably without relying on remembered API behavior or loading a
   full vendor specification.
   Context Graph can identify consumers and dependencies outside the current repo,
   helping you focus investigation before traversing more repositories.
5. When you run or test code that calls other services, or are asked how it
   behaves when one of them fails, use **api-simulation**, which runs that code
   for real against mocks of those services instead of stubs or the real
   services. Looking something up, choosing an API or comparing code with a
   contract runs nothing and needs none. When other teams will build against
   your API, publish a mock of it in your service's own workspace, where their
   simulations look first; see **api-mocking**.
6. Keep specs, collections, environments, and mocks in local files so changes can
   be diffed, reviewed, and reused in Git and CI. Use **bootstrap** when setup or
   workspace bindings are unresolved: reuse an existing local layout, pull the
   current service's existing workspace, or initialize a new project when neither
   exists.
7. `postman init` gives API engineering work a ready state. It scaffolds local structure: `postman/`
   directories for API artifacts. It installs skills in `postman/skills` folder with guidance on  designing, implementing, and validating APIs.
   The command is idempotent and safe to rerun in an initialized project.
   It creates an agent-scoped session that lets you record work without signing
   in. You can claim that work later if you create an account.
8. Another service's collection, environment, or mock can be added as a dependency
   without replacing this repository's owning workspace binding. Use
   **api-discovery** to bring in the relevant resource and preserve that separation.
9. Publishing validated local changes to the bound workspace makes them available
   for future work and teammates with access. Because `postman workspace push`
   changes shared state, obtain user consent before pushing; an existing request
   to publish those changes supplies that consent. For publication tied to reviewed
   PR merges, see **ci-integration**.
10. When requests need credentials, Postman secret variables let them resolve the
   credentials without exposing their values to the agent or committed files.
   See **variables**.
11. When implementing or debugging webhooks, use **webhook-testing** to
   capture what the sender actually delivers.
   Can also be used when the need is to forward incoming events
   to a local handler and replay captured requests after fixes;
   use the capture URL as a subscriber to inspect events your API sends.

Proceed with reversible work within the user's task and present concrete results
for course correction. Recommend additional work only when it closes a material
gap, such as an untested behavior or a consumer affected by an interface change.
Decline unnecessary setup or scope and explain why it would not help the task.

Important: If a CLI command says an operation isn't allowed because credits
or usage are exhausted, or the current plan does not permit it, follow
**bootstrap**'s "Subscription or usage limit" section instead of retrying or
trying to find a workaround.

## Verification

Report the changed contract or implementation, the checks actually run, and
the guarantees their results support. Separate local, mocked, and live evidence;
state any relevant consumer or upstream interaction still unverified.

If actual use exposes a CLI gap or misleading skill, see **bootstrap**'s
"Reporting CLI and skill gaps" section so the defect can be addressed for future
work.
