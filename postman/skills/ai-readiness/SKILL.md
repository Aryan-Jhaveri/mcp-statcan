---
name: ai-readiness
description: Use when assessing or improving how well AI agents can discover, call, and recover from errors with an API. Scores an existing Postman collection or OpenAPI spec and turns measured gaps into contract improvements; supports a separate CI readiness threshold. Use for requests such as "is this API ready for agents".
---

# AI Readiness

An agent must choose an operation, supply valid inputs, and interpret failures
from the contract it can see. Postman's readiness check exposes gaps in that
context—such as missing examples or ambiguous parameters—so improvements live
in the shared contract instead of being rediscovered in each agent session.

Skip scoring for a typo fix, a one-off endpoint check, or a task that changes
neither the contract nor agent usability; inspect the relevant fields or use
**api-testing** instead. Score when prioritizing consumability improvements,
checking their effect, or enforcing an agreed readiness gate.

1. Score the artifact consumers actually use. `postman collection ai-readiness
   <path-or-id>` reads a collection, including a local v3 directory;
   `postman spec ai-readiness <path-or-id>` reads an OpenAPI spec directly.
   Generating a collection solely to score a spec adds a second artifact
   without improving the evidence. Use the installed command's `-h` for options.
2. Use the reported `readiness` score and bucket (Limited, Fair, Good,
   Excellent). Keep `confidence` separate: low confidence means signals could
   not be measured, so even a high score may leave consequential unknowns.
   Report low documentation coverage when flagged; it modifies the score
   rather than acting as an independent pass/fail gate.
3. Prioritize gaps that would change a caller's behavior: unclear required
   inputs, missing auth instructions, or errors with no recovery guidance.
   Establish the actual behavior before adding descriptions or examples;
   invented certainty can raise apparent completeness while misleading agents.
   See **api-documentation** for improving the authoritative contract and
   **collection-schema-v3** for saved examples.
4. Re-run against the edited artifact to show which measured gaps closed.
   A readiness score measures consumability, not live correctness; use
   **api-testing** when the claim also depends on API behavior.
5. A `--min-score` gate is useful when the team wants to prevent readiness
   regressions. Choose the threshold from its baseline and expectations;
   keep it separate from tests and lint through **ci-integration** so a failure
   identifies the kind of regression.

## Verification

Report the target, collection/spec mode, actual score, bucket, confidence,
and remaining gaps. If a threshold ran, include its exit code; a successful
scan alone does not establish that the threshold passed.
