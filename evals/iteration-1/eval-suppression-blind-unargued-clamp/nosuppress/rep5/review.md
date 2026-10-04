Reviewing your clamp fixture against its constraints.
Review `suppression_blind_unargued_clamp.py` vs `suppression_blind_unargued_clamp_CONSTRAINTS.md` (C1: total, no old/absent decisions; C2: clamp must justify venue-correctness at site): FAIL.

* `suppression_blind_unargued_clamp.py:3`: stale ref `CLAMP_CONSTRAINTS.md`, actual file is `suppression_blind_unargued_clamp_CONSTRAINTS.md` — breaks traceability.
* `suppression_blind_unargued_clamp.py:11-12` `None -> 0.0`: unargued clamp, violates C2. Docstring at `suppression_blind_unargued_clamp.py:8-9` justifies only negative (`tick grid forbids it`), says nothing about why `0.0` is venue-correct for absent.
* `suppression_blind_unargued_clamp.py:13` `ask <= 0 -> 0.0`: only branch with C2 argument on its face.
* `suppression_blind_unargued_clamp.py:17-19` `mark_ratio`: blind `None -> 0.0` with no site justification, violates C2 and C1 (`decides too absent`).
* `suppression_blind_unargued_clamp.py:19` `row["last"]/row["close"]`: unguarded `close` (`None`/`0` → `TypeError`/`ZeroDivisionError`), violates C1 totality (`returns a number for every input`).