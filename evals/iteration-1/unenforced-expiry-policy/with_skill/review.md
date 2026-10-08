Reviewing the state machine fixture — inspecting its logic and run context.
Found the gap — the approval TTL is documented but never enforced. Now gathering the rubric to grade it.
Rubric mapped — now verifying the missing expiry check by executing the code.
# Review: `evals/fixtures/state_machine_exit.py`

`2 findings · C:0 M:1 m:1 i:0 · Mean 98/100 · Final Grade B`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/state_machine_exit.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no untrusted-entry → sink crossing in scope
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 87/100 · Security: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100 · Leanness: 100/100
Gated by: weakest domain: Correctness (B) — **always printed**

## Findings

### [MAJOR] Expired PENDING request can still be approved — TTL policy unenforced
- **Domain:** Correctness (A1)
- **Verified by:** RAN — created `Request(PENDING, created_at=now-TTL-10)`, called `approve()`, observed transition to `APPROVED` instead of rejection
- **Evidence:** `state_machine_exit.py:10` — `APPROVAL_TTL_SECONDS = 3600` plus docstring `state_machine_exit.py:3-4` — `PENDING request expires after APPROVAL_TTL_SECONDS and must be re-submitted`; `state_machine_exit.py:25-28` — `def approve(request): if request.state is not State.PENDING: raise ...; request.state = APPROVED` — no `created_at` / `time` check. Same gap in `state_machine_exit.py:31-34` `reject()`.
- **Failure scenario:** DERIVED chain `created_at → approve() → APPROVED`: any request older than 1h approves normally, so the stated expiry never fires. Stale approvals become permanent; no `EXPIRED` state, `is_expired()`, or timeout transition exists per `state-machine-completeness.md` — `No exit from a waiting state`.
- **Fix:** Module scope — add `def is_expired(req, now) -> bool: return now - req.created_at > APPROVAL_TTL_SECONDS`, reject expired in `approve()/reject()` with `ValueError("request expired, resubmit")` (or transition to a new `EXPIRED` state), inject `now: float` parameter instead of calling `time.time()` inside.
- **Trade-off:** Adds clock dependency; needs injectable `now` for determinism, negligible latency/memory cost.

### [MINOR] Unused `time` import; `created_at=0.0` default is always expired
- **Domain:** Correctness (A1)
- **Verified by:** RAN — `Request()` defaults to `created_at=0.0` (1970 epoch), i.e. instantly `>TTL` old once the Major fix lands
- **Evidence:** `state_machine_exit.py:6` — `import time` never used; `state_machine_exit.py:22` — `created_at: float = 0.0`
- **Fix:** Localized cleanup — remove unused import or use it via injectable `now`; default `created_at` to `None` and require explicit timestamp, or use `field(default_factory=time.time)`.

## Aligns well
- State guard on decided requests (`state_machine_exit.py:26,32`) correctly prevents `APPROVED→REJECTED` double-decision (A1).
- No security path, I/O, concurrency, or wire-format surface in scope — nothing to grade on S/C/D/L axes.