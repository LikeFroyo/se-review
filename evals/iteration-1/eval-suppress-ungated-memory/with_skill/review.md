# Review: evals/fixtures/suppress_ungated_memory.py

`0 findings · C:0 M:0 m:0 i:0 · Mean 100/100 · Final Grade A`
Covered: 2/2 files · Scope: focused on `evals/fixtures/suppress_ungated_memory.py` + `..._CONSTRAINTS.md` · Not examined: 0 — none
Domain Scores: Correctness: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Leanness: 100/100
Gated by: neither — highest grade reached (A)

## Findings

None.

The unbounded, per-instrument `_values` dict with no TTL, window, or eviction is the deliberate expression of the declared constraints, not a cache without a policy. C1 (`suppress_ungated_memory_CONSTRAINTS.md:3-9`) states the memory tier *is* the archive and that a TTL would delete the only record a late-arriving consumer could still want; C2 (lines 11-12) reserves staleness judgement for the consumer. The code matches: `put` (`suppress_ungated_memory.py:16-17`) overwrites only on a new observation, `get` (`:19-20`) returns the last observed value whenever called, and `age_s` (`:22-24`) **publishes staleness rather than acting on it** — nothing in the tier thresholds, expires, or refreshes. That division of labour is exactly what C1/C2 require; a naive reading flags "dict with no TTL and no eviction," but here growth is bounded by the instrument universe and every entry is still wanted.

Ruling noted in one line: the holder stays deliberately ungated because the constraints name `age_s` as the staleness surface and assign the judgement to the caller, so no finding.

## Aligns well

- **`age_s` is exposed, not enforced** (`suppress_ungated_memory.py:22-24`) — staleness is a measured signal handed to the consumer, which is the mechanism C2 prescribes.
- **No silent expiry anywhere**: no background sweep, no max-age check in `get`, no eviction on `put` — a consumer can always retrieve the last value.
- **Docstring states the contract** (`:11`): "The value stands however old it is" — doc-as-intent and code agree, matching the C1 statement that the latest value stands however old.
- **Trivial surface**: `put`/`get`/`age_s`/`instruments` do one thing each, no dead code, no unused abstraction.

**What would break if a TTL, window, or eviction policy were added**: the memory would stop being the archive — the last observed value for an instrument would be deleted precisely when a late-arriving consumer still wants it, and `age_s` would become moot because old entries would no longer exist. That is the failure C1 names, and it would be a behavioural regression, not a hardening.