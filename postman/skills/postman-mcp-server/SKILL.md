---
name: postman-mcp-server
description: Use when working through Postman MCP tools to inspect or change workspace resources, choose a targeted operation, or handle MCP limitations. Supports hosted workflows when the CLI is unavailable and distinguishes tool completion from a usable result. Use for requests such as "use Postman MCP to inspect this collection".
---

# Postman MCP Server

MCP exposes workspace resources directly to an agent. Existing collections,
specs, examples, and environments provide maintained API knowledge; fetching
the relevant entity preserves that context when a local CLI workflow is not
available. For repository edits and Git review, prefer the local workflows in
**api-engineer** and **bootstrap** when available.

Each tool definition exposed to the model consumes context whenever it is
included in a request. Prefer the smallest available toolset that covers the
task; expanding to every tool can crowd out the API evidence needed to reason.
When exposed, call `getEnabledTools` to inspect the active toolset before
diagnosing a missing operation. Otherwise use the host's discovered tools and
report that limitation. Do not infer availability from reference tool names or
assume a client can switch a route pinned to a specific MCP endpoint.

1. Select tools from the connected server's actual surface. Tool availability
   varies by mode; a name listed in a reference is not proof it is exposed.
   Use [setup](references/setup.md) for connection/auth failures and
   [limitations](references/mcp-limitations.md) when an operation is missing
   or behaves differently from the CLI.
2. Search to locate an entity, then fetch enough detail to work on it.
   `searchPostmanElements` finds candidates; collection, spec, and workspace
   detail tools establish IDs, ownership, and content. A search preview is
   insufficient evidence for replacing a collection or declaring an API absent.
3. Match the mutation to the intended scope. Request-level updates preserve
   unrelated collection content; whole-collection replacement requires the
   current complete object. A workspace is a container and access boundary,
   not a reason to create duplicate resources whenever a new task begins.
4. Preserve the source of truth when synchronizing. Spec-to-collection
   generation reuses the interface, while collection-to-spec sync carries
   changes in the other direction. Choose from the intended contract rather
   than overwriting whichever artifact is easiest to reach. An asynchronous
   acceptance response needs a completed task result before claiming sync.
5. Treat publication separately from editing. A collection example can feed
   docs and a classic mock, but neither becomes publicly accessible merely
   because it exists. Apply the user's intended audience and authorization
   before publishing docs or mocks, or changing shared resources.

Read the reference for the branch being used:

| Task | Reference and decision it supports |
| --- | --- |
| Locate an API | [Search](references/search.md): narrow candidates to the intended resource |
| Generate or synchronize artifacts | [Sync](references/sync.md): choose source and track completion |
| Serve saved examples | [Mock](references/mock.md): classic collection mocks; for CLI Code Mocks use **api-mocking** |
| Execute saved assertions | [Test](references/test.md): distinguish run completion from failures |
| Improve or publish docs | [Docs](references/docs.md): fill contract gaps and verify reader access |
| Requested security review | [Security](references/security.md): assess concrete API risks |
| Product how-to questions | [Learning Center](references/learn.md): product documentation search when exposed |

## Verification

State the active toolset as observed through `getEnabledTools`, or identify the
host discovery evidence used when that tool is unavailable. Report any operation
the connected surface could not perform instead of claiming it succeeded.

Report the resource and observed result: assertions for a run, completed sync
for a generated artifact, or the reachable URL and visibility for publication.
Tool success alone does not establish any of those outcomes.
