---
name: api-discovery
description: Use when finding an API or owner, integrating a public provider, locating Postman resources, or investigating consumers and change impact across services. Turns discovered contracts and mocks into reusable dependencies and identifies evidence outside the current checkout. Use for requests such as "who consumes this endpoint".
---

# API Discovery

Existing contracts and owners' mocks reduce the assumptions an integration
must invent. Relationship context broadens investigation beyond the checkout:
passing this service's own tests does not establish that its consumers can
still use a changed interface.

1. Choose the source by the question:

   | Need | Use |
   | --- | --- |
   | Public provider endpoints and integration details | Orbit search, then integrate |
   | A concrete Postman collection, request, spec, mock, or workspace | `postman search <type> <query>` |
   | Consumers, ownership, dependencies, or likely change impact | `postman context-graph ask` |

   These sources answer different questions. A miss in one does not establish
   absence in the others; combine entity search and relationship context when
   both the resource and its impact matter.
2. For public APIs, Orbit narrows discovery to task-relevant endpoints and
   returns integration guidance instead of requiring a whole vendor spec in
   context. Use it even when the provider is chosen: endpoint details and
   capability limits still determine whether the integration fits the task.
   `POST https://api.buildwithorbit.ai/v1/search` accepts a task in
   `q`; pass the chosen results' `id` and `resourceType` unchanged to
   `/v1/integrate`. Evaluate fit and limitations before choosing a provider,
   then use the returned auth, base URL, steps, and gotchas to implement.
   Read [Orbit's request schemas](reference/orbit.md) for the actual payloads
   and error handling. Orbit access does not supply a provider's credentials.
3. For Postman resources, narrow by entity type, ownership, and workspace.
   Read `postman search <type> -h` for supported filters. An empty result in
   the default ownership scope is incomplete evidence; consider
   `--ownership all` or a relevant narrower scope before declaring absence.
   Inspect the selected resource's owner and content rather than trusting a
   similar name.
4. For cross-service changes, ask the Context Graph a concrete question about
   the endpoint, schema, or service. `--wait` waits for an answer; without it,
   use the returned ID with `postman context-graph status <askId>`. The graph
   can connect Postman definitions, repository call sites, and runtime
   telemetry beyond the current checkout. Its coverage depends on connected
   and ingested sources, so verify consequential leads against definitions,
   source, or telemetry before treating them as facts. A newly added call may
   not be present yet. The query uses the authenticated API key's team, not
   the repository's workspace binding; changing that binding cannot fix a
   query against the wrong organization's context.
5. Use **bootstrap**'s "Owning workspace versus dependency" distinction
   before importing. For a dependency, `postman dependency add
   <collection|environment|mock> <name-or-id>` declares and downloads the
   selected resource without rebinding the repository. Prefer the discovered
   ID; `--workspace <id>` disambiguates names. If the graph only identified a
   service, search for its concrete resource first.
6. Dependency declarations live in `.postman/resources.yaml`, with downloads
   in `postman/.dependencies/`. `dependency install` restores them after a
   clone or in CI; `dependency update` refreshes them. Review refreshes when
   they can change test expectations. Copy a dependency into owned files to
   customize it, because updating dependencies overwrites downloaded edits.
   Use `dependency list` and command-specific help for targeted operations.

Use **api-simulation** to exercise the real service against discovered mocks,
and **ci-integration** to keep the resulting contract checks repeatable in PRs.

## Verification

Report which source answered the question, the resource IDs or evidence it
returned, what was reused, and any coverage gaps. A list of candidates alone
is neither an integration nor proof of compatibility.
