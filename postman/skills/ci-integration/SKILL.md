---
name: ci-integration
description: Use when adding API tests, structural or governance lint, or AI-readiness gates to CI, or publishing reviewed API artifacts to a Postman workspace after merge. Makes contract checks repeatable and separates validation from shared workspace changes. Use for requests such as "run this collection on every PR".
---

# CI Integration

Versioned collections and specs let a PR carry its API checks beside the code
change. CI reruns those checks independently of the author's session, while
publishing after merge makes the reviewed contract available to teammates and
future work. **api-discovery** helps identify consumers the gate should cover;
the author's own passing tests do not establish cross-service compatibility.

1. Select checks by the guarantee they establish:

   | Guarantee | Gate |
   | --- | --- |
   | Saved behavioral assertions pass | `postman collection run <path-or-id>` |
   | A collection's structure/style is valid | `postman collection lint <path> -f error` |
   | A spec meets workspace governance rules | `postman spec lint <spec> --workspace-id <id> -f error` |
   | Workspace entities and bindings pass lint/governance | `postman workspace lint --workspace-id <id> -f error` |
   | Agent consumability meets an agreed threshold | `postman collection ai-readiness <path> --min-score <n>` or the spec equivalent |

   Collection lint does not apply organization governance. Workspace-aware
   lint evaluates the rules available to that workspace; it does not author
   the policy. Confirm the intended rules are configured before claiming
   compliance. Read command-specific `-h` for installed options.
2. Keep gate results distinguishable so a failed build identifies behavior,
   structure, governance, or readiness. Preserve nonzero exits; suppressing
   them with `-x`/`--suppress-exit-code` removes the gate. For collection runs,
   `-r junit,html` produces reviewable reports; `--bail` trades a complete
   failure inventory for an earlier signal. See **api-testing** for assertion
   semantics and **ai-readiness** for score limitations.
3. Restore declared dependencies with `postman dependency install` when tests
   use them. Choose the target deliberately: a mock checks behavior under a
   model, while a live run sends real requests and can write data. PR gates
   should use a suitable isolated target and credentials; being a test does
   not make the command read-only.
4. Authenticate only jobs that need workspace resources. Use the CI secret
   store to supply `POSTMAN_API_KEY`, then
   `postman login --with-api-key "$POSTMAN_API_KEY"`. A local-only gate need
   not log in. Command-specific API-key flags are not a general replacement
   for login across lint and push operations. Use **bootstrap** for unresolved
   bindings, and **variables** for request credentials.
5. Publish only the reviewed branch after its merge checks pass.
   `postman workspace push -y` changes shared context; a PR-triggered push
   would publish an unmerged contract. The normal prepare phase assigns IDs
   to new entities, so `--no-prepare` can leave additions unpublished.
   Inspect the intended diff and binding when configuring this job; `-y`
   supplies noninteractive execution, not authorization for a different scope.
6. Use the default create/update strategy unless exact mirroring is the
   explicit requirement. `--push-strategy force-sync` can delete workspace
   entities absent from the checkout, including resources managed elsewhere.
   Follow **bootstrap**'s diff and consent boundary for that branch.

## Verification

Validate the workflow's event conditions and secret references, then report
which gates actually ran, their targets and individual results. Distinguish a
locally checked workflow from an observed CI run. For publication, establish
the merge trigger, push strategy, created/updated entities, and conflicts;
a green job alone does not prove the intended artifacts became available.
