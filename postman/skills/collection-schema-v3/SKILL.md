---
name: collection-schema-v3
description: Use when writing or debugging local Postman v3 collection and environment YAML, including collection lint failures. Preserves the per-entity files, inherited context, and schema shapes that make API changes reusable and reviewable in Git. Use for requests such as "fix this request YAML".
---

# Collection Schema (v3, Git-Native)

A v3 collection is a directory of independently editable entities. A change to
one request, example, or assertion can be reviewed in a PR beside the code it
checks, without regenerating a single large collection export.

1. Edit the entity that owns the change. Top-level directories under
   `postman/collections/` are collections; nested folders organize requests.
   Requests live in `*.request.yaml`, scope metadata in
   `.resources/definition.yaml`, and saved responses in
   `.resources/<request-name>.resources/examples/*.example.yaml`.
   `.resources/` holds metadata and examples, not runnable request files.
2. Preserve inherited auth, variables, and scripts when changing a request.
   Collection/folder definitions supply shared context; copying every inherited
   field into each request creates competing values and noisy future edits.
   See **variables** when deciding the scope of a value or secret reference.
3. Use [HTTP field shapes and examples](reference/http.md) when authoring
   request, example, or definition files. For other protocols, read
   [their schemas](reference/other_protocols.md); HTTP's URL/body/script shape
   cannot be assumed for gRPC, WebSocket, MCP, or LLM requests.
   [Environment files](reference/environment.md) have their own schema and
   do not use the collection entity's `$kind` discriminator.
4. Preserve types at the YAML boundary. Quote `{{variables}}` and strings that
   resemble booleans or numbers; JSON bodies are string content, best expressed
   with block scalars. A syntactically valid YAML object can still be the wrong
   request body shape. The HTTP reference gives the exact fields.
5. Keep edits local to the intended entity. `order` is a numeric relative
   ordering, so spaced values allow insertion without renumbering siblings.
   Keep filenames portable and unique case-insensitively; a display `name`
   can preserve characters that cannot appear in a filename. Renaming a request
   also requires checking its examples path.
6. Save examples for behavior consumers need to understand or simulate.
   Their schemas feed **api-documentation**, **api-mocking**, and
   **ai-readiness**; structural validity alone does not make an example
   accurate or useful. Assertions derived from the contract belong with the
   request through **api-testing**.

## Verification

Run `postman collection lint <collection-path>` for collection changes and
`postman environment lint <path>` for environment changes. Then inspect the
diff for unintended scope changes; when execution is appropriate, run the
changed request through its collection to check inherited context. Report
structural validation separately from behavior verified against a target.
