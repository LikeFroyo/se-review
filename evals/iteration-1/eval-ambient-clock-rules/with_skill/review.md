Reviewing target files — reading the script and run directory.
First pass done — now digging into the evaluation context.
Spotted ambient coupling patterns — now checking the scoring rubrics.
Rubrics mapped — now verifying the failure modes by execution.
# Review: `evals/fixtures/ambient_clock_rules.py`

`8 findings · C:2 M:4 m:1 i:1 · Mean 84.5/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/ambient_clock_rules.py` · Not examined: 0 — none
Paths: 1 · Unmapped: 0 — single-file fixture, all crossings classified
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 80/100 · Security: 75/100 · Maintainability: 75/100 · Operations: 90/100 · Interoperability: 87/100 · Leanness: 100/100
Gated by: `Critical finding` — any Critical caps the grade at F

## Findings

### [CRITICAL] Business rules read ambient clock, randomness, env, and identity
- **Domain:** Maintainability (B2)
- **Verified by:** RAN — executed `price_for_basket` under `BASKET_DISCOUNT_PCT=0` vs `50` (10000 → 5000, same basket); `eligible_for_offer` low-basket 20 calls with `seed=1` gave 4 True / 16 False; flipped `CURRENT_USER["id"]` `usr-1` → `usr-2` and buyer followed with no signature change.
- **Evidence:** `ambient_clock_rules.py:8-9,18,32,34,47,58-60` — `is_promotion_active`: `datetime.now(timezone.utc)`; `eligible_for_offer`: `datetime.now().hour`, `random.random()`; `price_for_basket`: `os.environ.get("BASKET_DISCOUNT_PCT")`; `place_order`: `CURRENT_USER["id"]`, `REQUEST_CONTEXT["last_order_id"] = order_id`. Docstrings admit each ("Ambient time/configuration/identity").
- **Failure scenario:** Same customer + same basket is eligible on one call and not the next (random draw, hour cutoff); same basket prices differently in two processes with different envs with no version boundary; order attribution changes with import order / global mutation. Behaviour is non-reproducible and unverifiable without the live clock, RNG, env, and module state.
- **Fix:** Shape before behaviour. Thread explicit parameters: `is_promotion_active(now)`, `eligible_for_offer(..., now, rng)`, `price_for_basket(..., discount_pct)`, `place_order(..., buyer_id)`. Scope: boundary — callers and handler that populates `REQUEST_CONTEXT` migrate to pass values explicitly.
- **Trade-off:** Adds parameters / a small clock-RNG-config struct at call sites (complexity up); pays back in deterministic tests and independent deployability.

### [CRITICAL] Order buyer taken from mutable module global with no authorisation check
- **Domain:** Security (S2)
- **Verified by:** RAN — `place_order` with `CURRENT_USER["id"]="usr-1"` then `"usr-2"` produced buyers `usr-1` → `usr-2`; signature has no user/credential parameter; `REQUEST_CONTEXT["last_order_id"]` overwritten each call.
- **Evidence:** `ambient_clock_rules.py:8,51-60` — `CURRENT_USER = {"id": "usr-1", ...}`; `def place_order(basket)` returns `{"buyer": CURRENT_USER["id"], ...}` with no check.
- **Source → Boundary → Sink:** Source: any importer / handler code that can write `CURRENT_USER` (caller-controlled in-process state) → Boundary: `place_order` performs no authentication or object-level authorisation → Sink: order created and attributed to an arbitrary `buyer`, plus shared `REQUEST_CONTEXT` mutated.
- **Failure scenario:** A confused-deputy caller, test fixture, or earlier handler that sets the global causes orders to be billed/attributed to the wrong user with no rejection point. Privilege confusion between actor classes.
- **Fix:** Require authenticated `buyer_id` (or session/principal object) as an explicit argument and authorise it at the `place_order` boundary; stop reading the global. Scope: boundary — handler auth contract changes; globals become read-only defaults or are removed.
- **Trade-off:** Every call site must supply and prove identity (plumbing cost, possible auth-middleware change); eliminates silent misattribution.

### [MAJOR] `place_order` is non-idempotent; retries create duplicate orders
- **Domain:** Correctness (A4)
- **Verified by:** DERIVED — `place_order` (`ambient_clock_rules.py:51-60`) mints `str(uuid.uuid4())` on every invocation, takes no idempotency key, and overwrites `REQUEST_CONTEXT["last_order_id"]`; two calls with the same basket yield two distinct `order_id`s. Chain: retry → new `uuid4` → second order → `last_order_id` points only at the latest.
- **Evidence:** `ambient_clock_rules.py:51-60` — `order_id = str(uuid.uuid4())` with no key parameter.
- **Failure scenario:** Client timeout + retry, or double-submit, creates two chargeable orders for one intent; the overwritten `last_order_id` loses the first.
- **Fix:** Accept `idempotency_key` and return the existing order when replayed (store key → order mapping). Scope: module — function plus its order store.
- **Trade-off:** Requires a key store with lifecycle/expiry (memory + complexity); alternative of client-generated `order_id` is cheaper but pushes uniqueness to callers.

### [MAJOR] Eligibility is non-deterministic and wall-clock dependent, so untestable
- **Domain:** Correctness (A6)
- **Verified by:** RAN — same `("c", 10)` over 20 calls with `seed=1` returned 4× True; result also depends on `datetime.now().hour >= 21`. Cross-references Maintainability (B2) ambient-state root; graded here for the distinct test-determinism failure.
- **Evidence:** `ambient_clock_rules.py:26-36` — `if datetime.now().hour >= 21: return False` + `if random.random() < 0.10: return True`.
- **Failure scenario:** A test asserting eligibility passes at noon and fails after 21:00, or flakes 10% of the time; coverage proves nothing about the branch that shipped.
- **Fix:** Inject `now` and `rng` (or a `draw: float` / policy object) so tests pin both. Scope: module — function signature plus test harness.
- **Trade-off:** Slightly larger signature and fixture setup per test; yields deterministic, seed-pinned tests.

### [MAJOR] No audit record for money / ownership change
- **Domain:** Operations (C4)
- **Verified by:** READ — `place_order` (`ambient_clock_rules.py:51-60`) computes `total` via `price_for_basket` and returns it, emitting no log / structured event / append-only record; the only trace is the overwritten in-memory `REQUEST_CONTEXT["last_order_id"]`.
- **Evidence:** `ambient_clock_rules.py:51-60`, no logging import or audit call.
- **Failure scenario:** Disputed charge or misattributed buyer cannot be reconstructed after restart; `last_order_id` holds one entry and is lost with the process.
- **Fix:** Emit a structured, append-only order event (`order_id`, `buyer`, `total`, `discount_pct`, timestamp) with correlation ID to durable storage. Scope: module — order path plus log sink.
- **Trade-off:** Log volume and PII-handling/redaction cost on the money path.

### [MAJOR] Naive local hour vs aware UTC instant disagree across hosts
- **Domain:** Interoperability (D2)
- **Verified by:** DERIVED — `is_promotion_active` (`ambient_clock_rules.py:18`) reads `datetime.now(timezone.utc)` (aware); `eligible_for_offer` (`ambient_clock_rules.py:32`) reads naive `datetime.now().hour` (host local zone). Chain: same instant → different `hour` per `TZ` → 21:00 cutoff fires at different absolute times; promotion window (UTC) and eligibility gate (local) never agree on "now".
- **Evidence:** `ambient_clock_rules.py:18` vs `:32` — `timezone.utc` in one, bare `datetime.now()` in the other.
- **Failure scenario:** Deploying the same code in two regions shifts the evening blackout by hours; a customer eligible under UTC evaluation is rejected under local evaluation.
- **Fix:** Use one aware instant everywhere (`datetime.now(timezone.utc)`) and convert explicitly where a local business hour is intended. Scope: local — two call sites plus a stated contract for which zone the 21:00 rule means.
- **Trade-off:** Must declare the intended zone for the cutoff (possible behaviour change in one region on deploy).

### [MINOR] Discount math truncates cents; env parse is unvalidated
- **Domain:** Interoperability (D3)
- **Verified by:** RAN — 100¢ basket at `33%` priced at 67¢ (`subtotal * pct // 100` floors). DERIVED — `int(os.environ.get(...))` raises `ValueError` on `BASKET_DISCOUNT_PCT=abc` and silently floors otherwise.
- **Evidence:** `ambient_clock_rules.py:46-48` — `subtotal - (subtotal * discount_pct // 100)`.
- **Fix:** Validate/clamp `discount_pct` at the config boundary and define the rounding mode (e.g. banker's vs floor) with a cents-level test.

### [INFO / SUGGESTION] Hardcoded 2026-11-01..12-31 promo window
- **Domain:** Maintainability (B4)
- **Verified by:** READ — `ambient_clock_rules.py:20-23` embeds `datetime(2026, 11, 1)` / `datetime(2026, 12, 31)`.
- **Evidence:** `ambient_clock_rules.py:20-23`.
- **Fix:** Name the window (`PROMO_START/END`) and load it from config so the schedule change is not a code change.

## Aligns well
- Money kept in integer `price_cents` throughout (D3) — no float-money path.
- `is_promotion_active` uses an aware UTC comparison (D2), the correct half of the clock story.
- Each ambient read is disclosed in its docstring — the coupling is admitted, which made it verifiable instead of hidden.