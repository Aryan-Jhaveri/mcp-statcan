// Run with: npm test (node --test; Node >= 23 strips TypeScript types natively)
import { test } from "node:test";
import assert from "node:assert/strict";
import { describeSource, parseRpcBody, periodToDate, prepareRows, prepareVegaLite, toCSV, unwrapToolResult } from "../src/data.ts";

test("periodToDate matches the server's period parsing", () => {
  assert.equal(periodToDate("2025"), "2025-01-01");
  assert.equal(periodToDate("2026-08"), "2026-08-01");
  assert.equal(periodToDate("2026-Q2"), "2026-04-01");
  assert.equal(periodToDate("2026-S2"), "2026-07-01");
  assert.equal(periodToDate("2026-10-15"), "2026-10-15");
  assert.equal(periodToDate("2026-W01"), null);
  assert.equal(periodToDate(null), null);
});

test("prepareRows makes values numeric and adds date", () => {
  const rows = prepareRows([{ period: "2024-03", value: "1.5" }, { period: "2024", value: "" }, { value: "x" }]);
  assert.deepEqual(rows, [
    { period: "2024-03", value: 1.5, date: "2024-03-01" },
    { period: "2024", value: "", date: "2024-01-01" },
    { value: "x" },
  ]);
});

test("toCSV quotes commas, quotes and newlines", () => {
  const csv = toCSV([{ a: 'say "hi"', b: "x,y" }, { a: null, b: "line\nbreak" }]);
  assert.equal(csv, 'a,b\n"say ""hi""","x,y"\n,"line\nbreak"');
});

test("describeSource names tables and vectors", () => {
  assert.equal(describeSource("https://x/rest/data/DF_18100004/2.2?lastNObservations=3"), "Table 18-10-0004-01");
  assert.equal(describeSource("https://x/rest/vector/v41690973?lastNObservations=3"), "Vector v41690973");
});

test("unwrapToolResult prefers structuredContent and throws tool errors", () => {
  assert.deepEqual(unwrapToolResult({ structuredContent: { a: 1 }, content: [] }), { a: 1 });
  assert.deepEqual(unwrapToolResult({ content: [{ type: "text", text: '{"b":2}' }] }), { b: 2 });
  assert.throws(
    () => unwrapToolResult({ isError: true, content: [{ type: "text", text: '{"error":"Bad key.","hint":"Check it."}' }] }),
    /Bad key\. Check it\./,
  );
});

test("parseRpcBody reads SSE and JSON bodies", () => {
  const sse = 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n\n';
  assert.deepEqual(parseRpcBody(sse, "text/event-stream").result, { ok: true });
  assert.deepEqual(parseRpcBody('{"jsonrpc":"2.0","id":1,"result":{}}', "application/json").result, {});
});

test("prepareVegaLite binds datasets and fills layout defaults", () => {
  const ds = { cpi: { columns: ["value"], rows: [{ value: 1 }], row_count: 1, truncated: false } };
  const out = prepareVegaLite({ mark: "line", data: { name: "cpi" } }, ds);
  assert.deepEqual(out.datasets, { cpi: [{ value: 1 }] });
  assert.equal(out.width, "container");
  assert.equal(out.$schema, "https://vega.github.io/schema/vega-lite/v6.json");
  const concat = prepareVegaLite({ hconcat: [] }, ds);
  assert.equal(concat.width, undefined);
});
