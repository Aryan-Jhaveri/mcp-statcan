// Run with: npm test (node --test; Node >= 23 strips TypeScript types natively)
import { test } from "node:test";
import assert from "node:assert/strict";
import { formatProductId, periodToTime, toCsv, toDataset } from "../src/data.ts";
import { niceTicks } from "../src/chart.ts";

const utc = (y: number, m: number, d = 1) => Date.UTC(y, m - 1, d);

test("periodToTime parses StatCan period labels", () => {
  assert.equal(periodToTime("2025"), utc(2025, 1));
  assert.equal(periodToTime("2026-08"), utc(2026, 8));
  assert.equal(periodToTime("2026-Q2"), utc(2026, 4));
  assert.equal(periodToTime("2026-S2"), utc(2026, 7));
  assert.equal(periodToTime("2026-10-15"), utc(2026, 10, 15));
  assert.equal(periodToTime("2026-W01"), utc(2025, 12, 29));
  assert.equal(periodToTime("Total"), null);
});

test("formatProductId", () => assert.equal(formatProductId(18100004), "18-10-0004-01"));

const sdmx = (geo: string, key: string, vals: (string | null)[]) =>
  vals.map((v, i) => ({ Geography: geo, Products: "All-items", _series_key: key, period: `2026-0${i + 7}`, value: v, UOM: "2002=100" }));

test("SDMX rows group by series key; varying dims label, shared dims become constants", () => {
  const d = toDataset({
    _sdmx_url: "https://x/rest/data/DF_18100004/2+3.2",
    data: [...sdmx("Canada", "2.2", ["169.9", null, "170.0"]), ...sdmx("Ontario", "6.2", ["171", "172", "173"])],
    _truncated: false,
  });
  assert.equal(d.productId, 18100004);
  assert.deepEqual(d.series.map((s) => s.label), ["Canada", "Ontario"]);
  assert.deepEqual(d.constants, ["All-items"]);
  assert.equal(d.series[0].points[1].value, null); // missing value -> gap
  assert.ok(!d.columns.includes("_series_key"));
});

test("query_sdmx rows without periods are table-only", () => {
  const d = toDataset({ _sdmx_url: "u", rows: [{ Geography: "Calgary", value: 181.6 }], message: undefined });
  assert.equal(d.series.length, 0);
  assert.equal(d.valueColumn, "value");
});

test("query_sdmx rows with periods chart by their string columns", () => {
  const rows = ["Canada", "Alberta"].flatMap((g, i) => ["2025", "2026"].map((p, j) => ({ Geography: g, period: p, avg: 100 + i + j })));
  const d = toDataset({ rows });
  assert.equal(d.valueColumn, "avg");
  assert.deepEqual(d.series.map((s) => s.label), ["Canada", "Alberta"]);
});

test("vector results get a vector id", () => {
  assert.equal(toDataset({ _sdmx_url: "https://x/rest/vector/v41690973?lastNObservations=8", data: [] }).vectorId, 41690973);
});

test("toCsv escapes commas, quotes and newlines", () => {
  const csv = toCsv([{ a: 'Québec, "QC"', b: null }, { a: "x\ny", b: 1 }], ["a", "b"]);
  assert.equal(csv, 'a,b\n"Québec, ""QC""",\n"x\ny",1\n');
});

test("niceTicks always covers the data range", () => {
  for (const [lo, hi] of [[164.9, 174.9], [0, 1], [5, 5], [-3.2, 7.7], [382000, 391000]]) {
    const t = niceTicks(lo, hi);
    assert.ok(t[0] <= lo && t[t.length - 1] >= hi, `${lo}..${hi} -> ${t}`);
  }
});
