---
name: performance-testing
description: Use when load-testing or benchmarking an API with concurrent virtual users and latency or error thresholds. Reuses a collection to probe a chosen failure mode and distinguishes target limits from load-generator limits. Use for requests such as "load test this API".
---

# Performance Testing

A collection supplies realistic request sequences; `postman performance run`
adds concurrency and a load profile. This makes performance claims repeatable,
but only for the workload, data, and network path actually exercised.
Collections run directly: converting with `postman-to-k6` is not required.

1. Choose the failure mode before the profile: `fixed` tests sustained
   concurrency, `ramp-up` explores degradation as load grows, `spike` tests
   sudden surges, and `peak` tests staying near maximum load. Reuse the
   collection's auth and assertions, and check that its operations and data
   represent the workload rather than repeating one unusually cheap request.
2. Establish the target, VU count, duration, and effects of write requests
   before sending load. Existing user authorization for that scope is enough;
   resolve missing limits before stressing a shared or production service.
   Thresholds are evaluated after the run, so a failing gate will not stop
   traffic early. A small initial run can expose wiring failures before a
   larger authorized test.
3. Choose the runner by reachability and capacity. `local` uses this machine
   or CI runner; its CPU or network can become the bottleneck. `postman-cloud`
   moves generation to Postman's infrastructure, while
   `postman-cloud-static-ip` supports targets with IP allowlists. Verify
   reachability before interpreting connection failures as service capacity.
4. Set thresholds that represent the user's objective, such as
   `--pass-if "less_than(p95, 500)"`. Supported metrics include `avg`, `p90`,
   `p95`, `p99`, `error_rate`, and `rps`; latency alone can look good when
   requests fail quickly. Use `postman performance run -h` for current syntax,
   units, and runner-specific options.
5. Isolate test data where concurrent writes would collide. **datasets**
   supports controlled row distribution across VUs; setup/teardown collections
   on hosted runners execute once around the test, not once per iteration.
   `--use-mock` can baseline collection/script overhead, but its numbers
   cannot establish the real backend's capacity.

## Importing from JMeter

Have a JMeter `.jmx` instead of a collection? Import it by following
`references/jmeter-import/README.md`, then treat the result as the collection
above. Its mapping table carries the JMeter semantics that are easy to get
wrong, and the import report marks what mapped exactly, what was approximated,
and which JMeter features have no equivalent here — think-time timers,
concurrent thread groups, and non-HTTP (JDBC/FTP/LDAP/Java) samplers are
reported, never faked.

## Verification

Report the workload, runner, achieved traffic, latency and error metrics,
and threshold verdict. Identify generator limits or target errors that prevent
attributing the result to API capacity. See **api-testing** for functional
assertions and **ci-integration** when the measured threshold becomes a gate.
