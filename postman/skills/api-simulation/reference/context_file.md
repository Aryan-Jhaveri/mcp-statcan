# `<name>.context.md`

The handoff document beside a simulation: `postman/simulations/checkout.sim.yaml`
gets `checkout.context.md`, and a foldered simulation keeps both in its folder.
`simulation create` and the Postman app write it from what they already know,
`simulation update` renames it with the simulation, and `simulation delete`
removes it. An existing one is never overwritten, because it holds what earlier
sessions learned.

It is prose for whoever works here next, human or agent. Nothing parses it, so
there is no schema to satisfy — but the generated headings and the
`<!-- begin:observations -->` markers are what a reader and the next write
expect to find, so keep them.

Keep it to the generated sections plus `## What didn't work`, in Markdown,
under about a screenful, so the line that matters is the one a reader lands on
rather than one they have to search for.

## What the generated file contains

A fresh file states the simulation's name, the date, its members and the hosts
they stand in for, and the run command for this simulation's own path.
Everything needing someone who has actually run it is left as an `@todo` HTML
comment, so a half-filled file reads as half-filled instead of as fact.

| Section | Holds |
| --- | --- |
| Header | Generation date and what the mocks came from. |
| `## Purpose` | What the simulation stands in for and what work it unblocks. Generated as the member list and a pointer to the handlers; needs hindsight, so it is the last thing to rewrite. |
| `## Execution` | The commands, in order: start the simulation, start the service pointed at it, prove it is up, count what got called, stop. The generated block leaves the service's own command, the proof request, the port and the log path as `@todo`. |
| `## Assumptions` | Every precondition someone had to discover, what the simulation takes for granted about the dependencies' own behaviour, the seeded data worth reusing, and what the simulation cannot reproduce. Each is a dated claim, the consequence of it not holding, and how it was established. |
| `## Observations` | One dated line per run, newest first, between the `begin`/`end` markers: which members took traffic and which took none. A summary, not a request log, and a failure goes in `## What didn't work` instead. |
| `## What didn't work` | Failures this simulation has already hit, a dated line each: what broke, the signature you'd recognize it by, where it surfaced, and the cause. Not generated — add the heading at the end, after `## Observations`, the first time a run gives you one. |

`## Observations` and `## What didn't work` both accrete, so a run is visible
in the file after the next one; `## Purpose`, `## Execution` and
`## Assumptions` are rewritten in place, since they describe the simulation as
it stands rather than a run. Each accreting section is bounded: `## What didn't
work` keeps the ten most recent, a line staying until a run shows it fixed, and
`## Observations` the five most recent runs. Past that the oldest go.

A run that keeps its line is how a pattern becomes visible — a member silent
for three runs running is worth more than the same fact seen once.

Don't restate what the generated file already says: its `## Assumptions` ships
with the ones that hold for every simulation.

## What earns a line

Write what running it taught you, and only that. Each line passes one test:
the repo doesn't already state it. That leaves five kinds of thing, and they
are the file's whole value:

- **A precondition you had to discover** — the setting, the service, the
  cleanup a run needs before it works at all. In `## Assumptions`.
- **A failure and its cause**, with where it surfaced, so the next session
  recognizes it instead of debugging it again. In `## What didn't work`.
- **What the run takes for granted about a dependency itself** — that an
  operation is idempotent, that a timeout means nothing committed, what order
  events arrive in. A mock answers these whether or not anyone checked, so its
  answer is a belief your code now relies on. In `## Assumptions`.
- **What the simulation can't reproduce, and what nobody has settled**, so a
  passing run is read for what it actually proves. In `## Assumptions`.
- **What the last run served**: which members took traffic, which stayed
  silent, and why. In `## Observations`.

For anything the repo does state — routes and request shapes, valid actions,
auth mechanics, each mock's hosts, config flags — name the file that holds it,
the way the generated `## Purpose` points at the handlers, and let the reader
go there. One source stays true; a copy here drifts, and this file gets
committed, so a named file is also how a credential stays out of it.

Write statements that stay true between runs. Counts, timings and coverage
belong to the run that produced them, so leave them in the log and keep the
pattern here: "every member served except `workspace`" rather than a tally.

## How a line carries its evidence

The log a claim came from isn't committed, so the line is all the next session
gets. Date every claim in `## Assumptions` and `## What didn't work`, and say
where it came from when a run didn't show it: `(observed 2026-10-22)` for what
a run established, `(reasoned 2026-10-22, src/payments/client.ts)` for what was
read rather than run.

A failure also carries the signature the next session will recognize it by —
the error text, the status, the member that sent it — since that is what
someone matches a new failure against. Quote the error itself, never a
response body. For the rest, name the committed file that holds it: the
handler that threw, the mock example captured from the real service, the test
that reproduces it. Not the run's log, which is wherever that run redirected
output and which the next run overwrites.

A good `## Assumptions` is a claim, its consequence and its date; a good
`## Observations` is a few lines; a good `## What didn't work` is one line per
failure:

```markdown
## Assumptions

- **`payments` treats a retried charge as idempotent on `Idempotency-Key`.**
  If it doesn't, the retry path charges twice. Nobody has settled it and the
  mock answers as though it does. (reasoned 2026-10-22, the mock's handler)
- **Redis holds no `EVENT_BATCH` key when a run starts.** A leftover one
  crashes the aggregation flush before any request is sent. (observed
  2026-10-22)

<!-- begin:observations -->
2026-10-22: every member served except `workspace`, which the service never
calls in development, and `god`, which models no endpoints.
2026-10-18: same, and `payments` served only `POST /charges`.
<!-- end:observations -->

## What didn't work

- 2026-10-22: the aggregation flush crashed on start —
  `TypeError: batch.map is not a function` in `src/events/flush.ts`, from a
  stale Redis `EVENT_BATCH` key an earlier run left behind. Not a simulation
  error, so the log shows nothing.
- 2026-09-30: `payments` answered `501` for `POST /refunds` — the mock models
  no refund path, so a run that reaches it proves nothing about refunds.
```

## Working with it

Read it before starting. An observed claim holds until your run contradicts
it; a reasoned one is a hypothesis, so check it, cheaply, when your run depends
on it. Check the assumptions and anything recorded about what a run doesn't
prove before concluding that something works. A claim this run contradicts is
a finding to report, not to quietly route around.

What it already answers, it answers: `## Execution` holds commands that ran,
and `## Assumptions` holds preconditions someone already established, so both
are usable as they stand rather than as a starting point to rebuild from. The
code you are about to change still needs reading; the setup around it is what
this file is for. A session that reads the document and then repeats the
search it was meant to replace has paid for it twice.

Then leave it truer than you found it:

- Replace the `@todo`s your run can answer, and delete each one you replace.
- Correct what you found wrong. Say what it is now, not what it used to be.
- Add the precondition you had to discover, or the thing the simulation turned
  out not to reproduce, as another dated claim-and-consequence pair.
- Add what broke and why to `## What didn't work`, and delete the lines there
  your run showed fixed.
- Add this run's summary to the top of the `## Observations` block, read from
  the simulation's log, and drop the oldest line past five.

A run that only confirms the file still adds its `## Observations` line.

## Rules

- Leave another session's assumptions and limits standing unless your run
  contradicted one: not exercised is not the same as not true.
- Keep this file for how the simulation behaves, and let the `.sim.yaml`
  speak for what it is.
- Rewrite `## Purpose` when the simulation's scope genuinely changed.
- Prefer deleting a line to adding one. Everything here is something the next
  session must either trust or re-check.
