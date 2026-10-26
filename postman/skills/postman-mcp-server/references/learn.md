---
description: Search the Postman Learning Center for how-to guidance, feature explanations, and suggested workflows. Use for "how do I..." questions about the Postman product.
---

# Learn Postman

Answer "how do I..." questions about the Postman product by searching the official Postman Learning Center (https://learning.postman.com). Explain features, walk through workflows, and cite authoritative sources.

Use this to learn *about Postman itself* — not to search the user's own collections, workspaces, or specs (that's `references/search.md`).

## Prerequisites

Use `searchLearningCenter` when it is exposed by the connected server. Follow
**postman-mcp-server**'s toolset inspection guidance before diagnosing a missing
tool; a remembered mode-to-tool mapping is not evidence of current availability.
The route's MCP endpoint determines its configured surface. `POSTMAN_MCP_MODE`
is not read by this plugin's routes and cannot switch that surface.

If no MCP tools are available, follow `references/setup.md`. If only the learning
tool is absent, use an available web search/browser to read the official Learning
Center and cite the pages actually consulted. Without either capability, report
the limitation and link the Learning Center rather than inventing product steps.

## Workflow

### Step 1: Search

Call `searchLearningCenter` with a focused `query` derived from the user's question. Prefer the product vocabulary from `postman-mcp-server` (mock server, environment, monitor, collection variable, etc.) over the user's exact phrasing.

- Turn a broad request into a specific query — "how to create a mock server", "write a test script", "set a collection variable", "schedule a monitor".
- If results are thin or off-target, refine: try a different feature term, split a multi-part question into separate searches, or broaden a narrow query.

### Step 2: Synthesize

Read the returned passages and compose a direct answer to the user's question. Do not just dump raw results.

- Lead with the answer or the concrete steps.
- Keep steps in the order the user would perform them.
- If the docs reveal a better or officially recommended workflow than what the user asked, surface it.
- Always cite the source URLs the tool returns so the user can read more.

### Step 3: Offer a Matching Workflow

When the answer maps to one of this skill's workflows, offer to run it so the user can act immediately:

- Creating/updating collections from a spec → `references/sync.md`
- Finding APIs in their org or the public network → `references/search.md`
- Running collection tests → `references/test.md`
- Creating mock servers → `references/mock.md`
- Generating or publishing docs → `references/docs.md`
- Security auditing → `references/security.md`

## Output

```
To create a mock server in Postman:

  1. Open the collection you want to mock (it needs saved example responses).
  2. Select the collection → "Mock collection".
  3. Name the mock, pick an environment, and choose visibility.
  4. Postman returns a mock URL that serves your examples.

  Mock servers read from saved examples, so add examples first if you
  have none — I can create the mock and its examples for you.

  Source: https://learning.postman.com/docs/design-apis/mock-apis/set-up-mock-servers/
```

## Error Handling

- **MCP not configured:** Follow `references/setup.md` to connect the Postman MCP Server.
- **`searchLearningCenter` unavailable:** Use the toolset inspection and official-documentation fallback under Prerequisites.
- **401 Unauthorized:** "Your Postman API key was rejected. Generate a new one at https://go.postman.co/settings/me/api-keys." Then re-authenticate with `references/setup.md`.
- **No results:** "Nothing matched in the Learning Center. Try rephrasing with the Postman feature name, or ask about a more specific step."
