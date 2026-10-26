---
name: datasets
description: Use when a collection needs queried or joined test inputs, a reusable named view, spreadsheet worksheet data, live database rows, or script access through pm.datasets(). Chooses between a simple iteration file and a dataset while preserving query semantics, portability, and credential boundaries. Use for requests such as "run this collection over database rows".
---

# Datasets

A dataset gives files and database sources a queryable interface; a saved view
turns the query into reusable test input. That is useful when filtering,
joining, or refreshing rows is part of the test. A one-off CSV/JSON run can
stay with `collection run -d`; a dataset should earn its extra configuration.

## Choose the data and execution path

1. Prefer local file sources for reproducible fixtures. A live database is
   useful when current data is the point, but adds authentication, entitlement,
   network, and credential requirements even in a local `.dataset.yaml`.
   Check `postman dataset <action> -h` and the actual source capability before
   promising a workflow; source support can vary with the installed CLI.
2. Use the default federated SQLite query path to join supported sources.
   `--source <name>` instead sends SQL to one source in its native dialect.
   Switching modes to silence a SQL error changes query semantics. JDBC
   requires the native path and cannot join in the federated layer; native
   database connectors can support federation.
3. Choose credentials before choosing a database connector. JDBC variables
   and properties accept shared-vault references such as
   `vault:<vaultId>/<secretId>`, resolved at query time. Native database
   credentials are stored literally in dataset configuration on the documented
   CLI surface; inspect current support before use, and keep secret-bearing
   configuration out of Git. Literal values passed through stdin avoid argv
   exposure but can still be persisted in YAML. See **variables** for vault
   handling. A connector that enables a join may have a worse credential
   boundary than JDBC; do not hide that tradeoff.
4. Choose iteration or script access deliberately. The paired
   `--iteration-data-dataset <path-or-id>` and
   `--iteration-data-view <name-or-id>` flags feed one row per collection
   iteration, with columns exposed as variables. They exclude `-d` and require
   a parameter-free view because the runner has no query-parameter input.
   Repeatable `--dataset <path-or-dir>` instead exposes `pm.datasets()` to
   scripts; it does not itself create row-driven iterations.

## Build a portable, queryable artifact

Create a local manifest with `postman dataset create <path.dataset.yaml>
--name <name>`, then attach sources with `dataset source add`. Source commands
supply IDs and validation that hand-written entries can miss. Existing-dataset
commands accept a local path or workspace ID; `list` needs a local path for
local discovery, while workspace create/list use `--workspace`.

File sources are copied into `data_dir` unless `--ref-only` is used. That option
records absolute paths and makes the dataset machine-specific. For a workspace
dataset, adding `--file` alone registers a local filesystem source; `--upload`
is what uploads bytes. Use **bootstrap**'s workspace sync when publishing the
whole project; there is no separate `dataset push`.

For spreadsheet sources, use the worksheet-aware guidance in
[Spreadsheet sources](reference/spreadsheets.md). For ordinary source names,
prefer normalized identifiers: table names lowercase, collapse repeated
underscores, and strip edge underscores. A source called `users` is queried
as `users`, not `source_users`. Verify actual tables before interpreting an
unknown-table error as missing data.

For JDBC, `dataset jdbc inspect <driver.jar>` supplies driver class, URL
template, variables, and properties for `source add`; `--from-source` can reuse
a connection. JDBC addition tests connectivity unless disabled; native source
addition needs a separate `dataset source test`. This distinction prevents
mistaking a saved source for a working connection.

Prove the query with `dataset query` before saving it with `dataset view create`,
then run the view. Query parameters are positional (`$1`, `$2`, with `-p`
values in order). Commit the manifest and intended source files; keep engine
state such as `data.db`, `meta.db`, `daemon.log`, and caches out of the repo.
Dataset commands do not create a `.postman/resources.yaml` registry entry.
Deletion removes the manifest but preserves source files that may be shared.
Deleting a workspace dataset is permanent; establish that intent rather than
treating deletion as a way to repair a query.

## Interpret failures and results

A generic server-error wrapper can hide SQL or connection errors. Use structured
`--json` errors and their remediation, or `--debug` when necessary, to identify
the layer before retrying. `source test` separates database connectivity from
SQL errors; file/URL sources have no connection to test. Engine startup failures
may need `data_dir`'s daemon log rather than a different query.

Script dataset access is lazy, and invalid YAML can be skipped with a warning
rather than failing the run. On a hosted collection, `--dataset` is not an
access-control boundary: scripts can access other datasets readable by the
session. Inspect the collection's data access before running untrusted scripts
with that session.

## Verification

Report the queried columns and row count, local/workspace location, live versus
copied sources, and federated versus native execution. For iteration runs,
compare the actual iteration count with the intended view rows and configured
limits. Matching counts establishes wiring, not that the data covers every
behavior the test needs. Creating a manifest alone proves neither.
