# Spreadsheet sources

Use a local dataset for Excel or OpenDocument workbooks. The worksheet-aware
source-add path creates one datasource per sheet; treating the entire workbook
as one CSV source leaves an artifact that can be saved but not queried.

- Supported workbook formats are `xlsx`, `xls`, and `ods`. Re-save other
  workbook formats rather than forcing `--format csv` onto binary data.
- `source add --file <workbook>` names sources from sheets; `-n` does not
  rename them or select one sheet. Workspace dataset adds do not support this
  worksheet expansion, even with `--upload`; use local workbooks or deliberate
  CSV/JSON exports for that branch.
- Read `sources[].table` in JSON output for each queryable identifier. Sheet
  names can normalize and collide, so deriving a SQL table from a display name
  or adding a `source_` prefix by habit can query the wrong identifier.
- Remove and re-add to replace a worksheet source. `source update` cannot
  establish a worksheet selector; replacing its file with CSV can leave a
  stale worksheet selector attached to data that has no worksheets.
- Verify that addition returned one source per intended sheet and query the
  needed tables. Older CLI behavior can register a single unusable workbook
  source; successful creation is insufficient evidence of worksheet support.

Let file extensions infer formats unless the contents require an explicit
supported override. A format string accepted by the CLI can still fail when
the query engine reads the source.
