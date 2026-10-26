---
description: Discover APIs across your Postman workspaces. Ask natural language questions about available endpoints and capabilities.
---

# Discover APIs

Answer natural language questions about available APIs across Postman workspaces. Find endpoints, check response shapes, and understand what's available.

## Prerequisites

The Postman MCP Server must be connected. If MCP tools aren't available, follow `references/setup.md` to connect it.

## Workflow

### Step 1: Search

Use the unified `searchPostmanElements` tool. It can search across various entity types like requests, collections, workspaces, specs, flows, environments and mocks. Choose `entityType`, `ownership`, and `filters` based on the user's intent.

1. Call `searchPostmanElements` with the user's query. Pick the parameters from the user's intent:
   - `entityType`: `requests` (default), `collections`, `workspaces`, `specs`, or `flows`.
   - `ownership`: `organization` (default — your org's resources), `external` (public Postman network, third-party APIs), or `all` (both).
   - `filters`: Optional structured `$and` expression to narrow results — e.g., restrict to the Private API Network, a workspace, or HTTP method.
2. If results are sparse, broaden the search — widen `ownership` to `all`, drop or relax filters, or try a different `entityType`. You can also fall back to `getWorkspaces` + `getCollections` for browsing, or `getTaggedEntities` to find collections by tag.

**Filter examples:**

- Search only the trusted Private API Network: `ownership: organization` with `filters: {"$and":[{"privateNetwork":{"$eq":true}}]}`
- Find a third-party public API (e.g. "Stripe API"): `ownership: external` with `filters: {"$and":[{"visibility":{"$eq":"public"}}]}`
- Restrict to a specific workspace: `filters: {"$and":[{"workspaceId":{"$eq":"ws-abc123"}}]}`
- GET requests only: `entityType: requests` with `filters: {"$and":[{"method":{"$eq":"GET"}}]}`

### Step 2: Drill Into Results

For each relevant hit:
1. Call `getCollection` to get the overview
2. Scan endpoint names and descriptions for relevance
3. Call `getCollectionRequest` for the most relevant endpoints
4. Call `getCollectionResponse` to show what data is available
5. Call `getSpecDefinition` if a linked spec exists for richer detail

### Step 3: Present

Format results as a clear answer to the user's question.

**When found:**
```
Yes, you can get a user's email via the API.

  Endpoint: GET /users/{id}
  Collection: "User Management API"
  Auth: Bearer token required

  Response includes:
    {
      "id": "usr_123",
      "email": "jane@example.com",
      "name": "Jane Smith",
      "role": "admin"
    }
```

**When not found:**
```
No endpoint returns user emails.

  Closest matches:
  - GET /users/{id}/profile — returns name, avatar (no email)
  - GET /users — list view doesn't include email

  The email field might require a different permission scope,
  or it may not be exposed via API yet.
```

**When multiple results:**
List relevant collections with endpoint counts, then ask which to explore further.

## Error Handling

- **MCP not configured:** Follow `references/setup.md` to connect the Postman MCP Server.
- **No results:** "Nothing matched your query. Try different keywords, broaden `ownership` to `all`, or browse the user's workspaces with `getWorkspaces` + `getCollections`."
- **401 Unauthorized:** "Your Postman API key was rejected. Generate a new one at https://go.postman.co/settings/me/api-keys." Then re-authenticate with `references/setup.md`.
- **Too many results:** Ask the user to be more specific. Suggest filtering by workspace or using tags.
