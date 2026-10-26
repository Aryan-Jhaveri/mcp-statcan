---
name: variables
description: Use when parameterizing requests across environments, choosing variable scopes, chaining values in scripts, or referencing credentials without committing or exposing them. Keeps one reusable collection while separating target configuration from secret values. Use for requests such as "where should I put this API key".
---

# Variables

Variables let one maintained collection run against different targets without
forking its requests. Scope determines which value wins; secret references
allow the same files to be shared without sharing credential values.

1. Put API defaults in collection variables and target-specific values, such
   as `base_url`, in an environment. Parameterize values that actually vary;
   a stable literal need not become another configuration choice. Reference
   values as `{{key}}` in URLs, headers, parameters, or bodies.
2. Resolve surprises through precedence: local script values override
   iteration data, then environment, collection, and global values. A correct
   environment file can still lose to a row or script override. Values can
   reference other variables and resolve at send time, so inspect the chain
   rather than just the final request field.
3. Use runtime values for chaining responses into later requests. Choose
   `pm.environment` or `pm.collectionVariables` when the scope is intentional;
   `pm.variables.get` reads across scopes, and `pm.variables.set` holds a local
   value for the current run. For transient sensitive values, avoid persisting
   them to an environment or logging them.
4. Store durable credentials in the shared vault and commit references.
   `type: secret` alone masks the UI but still leaves a literal YAML value
   readable. **collection-schema-v3**'s environment reference describes the
   file schema; command-specific `-h` supplies supported vault operations.

For non-sensitive target configuration:

```bash
postman environment new "Staging"
postman environment var set base_url https://staging.example.com \
  --environment "postman/environments/Staging.environment.yaml"
```

For a secret, have the user supply the value through the CLI's masked prompt,
not through agent context or a literal command argument:

```bash
postman secret create STRIPE_API_KEY --workspace <workspace-id>
postman environment var set api_key --secret-id <secret-id> --vault-id <vault-id> \
  --environment "postman/environments/Staging.environment.yaml"
```

The environment then carries the vault/secret IDs rather than the value.
Secret resolution and permission to view the secret are distinct; a teammate's
ability to run a request need not expose the credential to them. Use
**bootstrap** when the vault operation needs unresolved authentication.

## Verification

Run `postman environment lint <path> --fail-severity warning` to fail on
warnings as well as errors in the saved environment. Lint checks the artifact;
it does not prove that the session can resolve a vault secret. Verify resolution
with an appropriate authenticated request and a contract-derived assertion,
keeping credentials out of output. An unresolved-reference or authorization
failure needs investigation, not a claim that the secret worked.
Report the selected environment and scope
or reference that supplies the value; a masked display alone does not prove
that the committed file contains no literal secret.
