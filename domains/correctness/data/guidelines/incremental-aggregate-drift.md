# Incremental aggregate drift — the summary that stops matching its source

Audit any value maintained by applying deltas rather than recomputed. The defect is not a wrong
answer; it is a permanently wrong answer that nothing ever detects, because every input is
individually correct.

## The aggregate

- **Never reconciled against a full recompute:** An accumulator, rollup, counter set, or derived summary is maintained incrementally and no path recomputes it from the source to compare.
- **Order-dependent accumulation:** Summation, counting, or set combination whose result depends on the order of application, while the order of the inputs is not guaranteed anywhere.
- **Correction not applied forward:** An amendment, deletion, or re-statement to a source record adjusts the source but leaves aggregates already derived from it unchanged.
- **Two computations of one quantity, unasserted equal:** The same figure is computed incrementally in one place and in full in another, with nothing checking they agree.

## Boundaries the aggregate crosses

- **State assumed continuous across a restart:** Counters, offsets, or sequences are treated as continuous through a process restart, a partition gap, or a rollover, with no re-anchor and no check.
- **Partial reset:** Some of the accumulated state is re-derived on recovery and some is carried over, with no rule stating which, so the two disagree from the first request onward.
- **Expiry and eviction applied to the source but not the aggregate:** A record leaves the retention window while its contribution stays in the derived figure indefinitely.
