Reviewing blind-sibling suppression fixture and constraints — reading source.
Found a de-duplicating consumer under unfiltered fan-out rules — mapping the eval harness.
Confirmed scope — now verifying the suspected stale-state behavior.
Review: `suppression_blind_sibling.py` vs `suppress_unfiltered_fanout_CONSTRAINTS.md`:

* C1 PASS: `suppression_blind_sibling.py:17-19` `Fanout.dispatch` is unfiltered — no filter/coalesce/dedupe, in registration order.
* C2 PASS (formally): `suppression_blind_sibling.py:29-33` reduction lives inside `ChainRecorder.__call__`, which C2 explicitly permits (`...CONSTRAINTS.md:11-12`).
* Functional bug — blind sibling suppression: dedupe key is `price` only (`suppression_blind_sibling.py:30`), but recorded value is `state` (`suppression_blind_sibling.py:33`). Same-price / new-state frame is dropped, leaving `.state` stale. Verified: `price=100/state=A` then `price=100/state=B` → `state` stays `A`.
* Fix: key on full observation, e.g. `if (price,state) == last: return`, or at minimum do not suppress when `state` changed.
* Doc nit: `suppression_blind_sibling.py:3` cites `FANOUT_CONSTRAINTS.md`, actual file is `suppress_unfiltered_fanout_CONSTRAINTS.md`.