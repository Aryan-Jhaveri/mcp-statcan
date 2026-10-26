---
name: api-documentation
description: Use when defining or improving an API contract, generating documentation from a collection or OpenAPI spec, publishing API docs, or sharing a documentation link. Makes auth, inputs, responses, and examples reusable by callers, tests, and mocks. Use for requests such as "publish API docs".
---

# API Documentation

A maintained contract gives callers enough information to integrate without
reading the implementation. Keeping descriptions and examples beside the API
artifacts lets the same knowledge support documentation, tests, and mocks,
with changes reviewable alongside code.

1. Start from the existing source of truth. An OpenAPI spec describes the
   interface for tooling; a Postman collection adds runnable requests,
   examples, and assertions. Maintain both when both uses matter, with an
   explicit direction of generation or synchronization so they do not become
   competing definitions. Local edits need **bootstrap** only when setup or
   bindings are unresolved.
2. When the spec is authoritative, reuse its operations with
   `postman spec generate collection <spec-path-or-id> -n "<collection-name>"`.
   Inspect the generated result before replacing an existing collection:
   maintained scripts and examples carry knowledge beyond endpoint shapes.
3. Describe what changes a caller's decision: required versus optional inputs,
   auth and scopes, response guarantees, pagination, retryable failures, and
   side effects. Derive guarantees from the agreed contract or verified
   behavior; label unresolved design choices instead of inventing them.
   Use [REST design guidance](reference/rest-api-best-practices.md) when a
   design choice affects usability or compatibility, not to redesign an
   unrelated interface while filling a documentation gap.
4. Save examples that clarify consequential cases, including relevant errors.
   Examples become inputs for mocks as well as explanations for readers;
   a success-only example can hide the failure path callers must handle.
   Use **collection-schema-v3** for local collection edits and **variables**
   to keep credentials out of reusable requests and examples.
5. Choose delivery by audience. Local artifacts support Git review;
   publishing to the bound workspace makes them available to teammates with
   access (see **bootstrap**). A workspace push does not itself publish a
   public docs page or change permissions. For a public documentation link,
   use **postman-mcp-server**'s documentation workflow and the available
   publishing tool; establish the intended audience before public exposure.

## Verification

Check that the edited artifact parses and its examples agree with the
contract. For a publication, inspect the resulting page and report its actual
link and visibility; a successful upload alone does not show readers usable
documentation. State any behavior that remains undocumented or unverified.
