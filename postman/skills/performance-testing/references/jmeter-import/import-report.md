# Import Report — <TEST PLAN NAME>

> Fill in every section from the import. Once the manual tasks are resolved, update the
> "Needs manual work" list and the summary counts to match the collection you hand off.

## Summary

- Thread groups: <N>
- HTTP requests imported: <N>
- Folders: <N>
- Script-only samplers (stubs): <N>
- Collection variables: <N>
- Data files: <N>
- Items needing manual work: <N>

## Imported exactly

- HTTP requests (method, URL, headers, query/body params)
- Response assertions → `pm.test` (status / body contains / equals / matches)
- Regex & Boundary extractors → `pm.collectionVariables.set`
- Simple JSONPath extractors (dot/index paths) → property access
- Basic/Digest auth, User Defined Variables → collection variables
- `${var}` → `{{var}}` interpolation

## Approximated

- **Thread group load** → VU count + duration + one of 4 load profiles.
- **Loop counts / iterations** → duration in minutes.
- <element-specific warnings…>

## Needs manual work

- **[kind]** `request`: <what and why>

## Not supported by Postman performance runs (dropped)

- **Think time / timers** — no equivalent.
- **Multiple concurrent thread groups** — a run is one collection repeated across VUs.
- **Flow control** (If/While) — requests flattened; restore with `pm.execution.setNextRequest`/`skipRequest`.
- **Cookie/Cache/DNS managers** — cookies handled automatically per VU.
- **Non-HTTP samplers** (JDBC/FTP/LDAP/Java/TCP/Debug) — HTTP only.

## Performance run

```bash
postman performance run <COLLECTION_UID> \
    --vu-count <N> --duration <MIN> --load-profile <fixed|ramp-up|spike|peak> \
    [--data-file <file>] [--pass-if "<fn>(<metric>, <value>)"]
```

Upload the collection to a workspace first to get its UID. `--pass-if` is a suggested
default unless the JMeter plan had a Duration Assertion.
