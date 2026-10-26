# JMeter → Postman mapping table

Fidelity: **exact** (behaviour preserved) · **approx** (closest supported equivalent, reported) · **manual** (needs a judgment call, often with the user) · **unsupported** (dropped, reported).

## Structure

| JMeter element | XML tag | Postman | Fidelity |
|---|---|---|---|
| Test Plan | `TestPlan` | Collection (`info` + `item`) | exact |
| Thread Group | `ThreadGroup` | load config (VUs/duration/profile) + folder when >1 | approx |
| setUp/tearDown Thread Group | `SetupThreadGroup`/`PostThreadGroup` | folder; suggest `--setup-collection`/`--teardown-collection` | approx |
| Concurrency Thread Group | `...ConcurrencyThreadGroup` | VUs=`TargetLevel`, duration=`RampUp`+`Hold`, `ramp-up` | approx |
| Stepping Thread Group | `kg.apc...SteppingThreadGroup` | VUs=`num_threads`, duration=`flighttime`, `ramp-up` | approx |
| Ultimate Thread Group | `kg.apc...UltimateThreadGroup` | VUs=max row concurrency, duration=sum of row times | approx |
| Arrivals Thread Group | `...ArrivalsThreadGroup` | treated like concurrency | approx |
| Transaction Controller | `TransactionController` | folder | exact |
| Simple/Generic Controller | `GenericController`/`SimpleController` | folder | exact |
| Loop Controller | `LoopController` | flattened; loop count → duration | approx |
| If Controller | `IfController` | each enclosed request gets a pre-request skip guard (`pm.execution.skipRequest`); `${var}` → `pm.variables.get(...)` | approx |
| While Controller | `WhileController` | flattened, requests run unconditionally; restore looping with `pm.execution.setNextRequest` | approx |
| Recording Controller | `RecordingController` | transparent (children recursed) | exact |
| Module / Include Controller | `ModuleController`/`IncludeController` | flattened children if inline; external refs reported | manual |

## Requests

| JMeter | XML | Postman | Fidelity |
|---|---|---|---|
| HTTP Request | `HTTPSamplerProxy` | request item | exact |
| method / path / domain / port / protocol | `HTTPSampler.*` | `request.method` + `url` (blank protocol → `http`) | exact |
| Query/body params | `Arguments`/`HTTPArgument` | query (GET) / urlencoded (POST/PUT/PATCH) / formdata (multipart) | exact |
| Raw body | `postBodyRaw=true` | `body.mode=raw` | exact |
| Header Manager | `HeaderManager` | `request.header` (merged by scope, later wins) | exact |
| HTTP Request Defaults | `ConfigTestElement`/`HttpDefaultsGui` | fallback for blank domain/port/protocol/path | exact |
| Auth Manager Basic/Digest | `AuthManager` | `request.auth` basic/digest (first entry; multiples reported) | exact |
| Auth Manager Kerberos/NTLM | `AuthManager` mechanism | — | unsupported |
| Cookie / Cache / DNS Manager | `CookieManager`/... | auto per-VU cookies; presets not transferred | unsupported |
| Non-HTTP samplers | `JDBC/FTP/LDAP/Java/TCP/Debug/Dummy...Sampler` | — | unsupported |

## Extractors (post-response → test script `pm.collectionVariables.set`)

| JMeter | XML | Fidelity |
|---|---|---|
| Regular Expression Extractor | `RegexExtractor` | exact (via `new RegExp`, group from `$n$` template) |
| Boundary Extractor | `BoundaryExtractor` | exact (left/right → non-greedy regex) |
| JSON Extractor (native) | `JSONPostProcessor` | exact for dot/index paths; complex → manual |
| JSON Path Extractor (plugin) | `...JSONPathExtractor` | exact for simple paths |
| XPath / XPath2 Extractor | `XPathExtractor`/`XPath2Extractor` | manual (no sandbox XPath) |
| CSS/HTML Extractor | `HtmlExtractor` | manual (no sandbox CSS) |

## Assertions (→ `pm.test`)

| JMeter | XML | Maps to | Fidelity |
|---|---|---|---|
| Response Assertion | `ResponseAssertion` | status / contains / equals / matches, honouring `test_type` bitmask + NOT | exact |
| — test_field response_code | | `pm.response.code` | exact |
| — test_field response_data | | `pm.response.text()` | exact |
| — test_field headers/message | | `pm.response.headers`/`.status` | exact |
| Duration Assertion | `DurationAssertion` | `pm.test` responseTime + `--pass-if less_than(p95, ms)` hint | exact |
| Size Assertion | `SizeAssertion` | `pm.test` on `responseSize` | approx |
| JSON Assertion | `JSONPathAssertion` | `pm.test` on simple path | approx |

`ResponseAssertion.test_type` bits: `MATCH=1, CONTAINS=2, NOT=4, EQUALS=8, SUBSTRING=16, OR=32`.

## Variables & data

| JMeter | XML | Postman | Fidelity |
|---|---|---|---|
| User Defined Variables | `Arguments` under TestPlan/scope | collection `variable[]` | exact |
| `${var}` references | inline | `{{var}}` | exact |
| `${__UUID}` / `${__time}` | function | `{{$guid}}` / `{{$timestamp}}` | exact |
| `${__Random(...)}` and other `__fn` | function | `{{$randomInt}}` or flagged reference | approx/manual |
| CSV Data Set Config | `CSVDataSet` | `--data-file` + column list | approx (one file/run; naive CSV) |
| Counter / Random Variable | `CounterConfig`/`RandomVariableConfig` | pre-request script or `{{$randomInt}}` | manual |

## Scripting

| JMeter | XML | Postman | Fidelity |
|---|---|---|---|
| JSR223 PreProcessor | `JSR223PreProcessor` | prerequest script (JS, IIFE-wrapped) | manual |
| JSR223 PostProcessor | `JSR223PostProcessor` | test script | manual |
| BeanShell Pre/PostProcessor | `BeanShell*Processor` | pre/test script | manual |
| JSR223 / BeanShell Sampler | `JSR223Sampler`/`BeanShellSampler` | script-only stub (no HTTP) | manual |

## Timing / pacing — not supported, always reported

Postman performance runs have no think time and no flag for one. Every timer is
dropped and listed in the report; none is reproduced.

| JMeter | XML |
|---|---|
| Constant / Uniform / Gaussian / Poisson Timer | `ConstantTimer`/`UniformRandomTimer`/... |
| Constant Throughput Timer | `ConstantThroughputTimer` |
| Throughput Shaping Timer | plugin |
| Synchronizing Timer | `SyncTimer` |
| Test Action (pause/stop) | `TestAction` |
