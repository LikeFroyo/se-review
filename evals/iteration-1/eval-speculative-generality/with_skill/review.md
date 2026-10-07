Reviewing your speculative factory fixture — checking for over-generalization.
Found a textbook speculative generality case — now loading the review rubric to grade it.
The abstraction layers look unearned — now verifying the evidence before scoring.
# Review: `evals/fixtures/speculative_factory.py`

`2 findings · C:1 M:0 m:1 i:0 · Mean 95.33/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: evals/fixtures/speculative_factory.py · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no trust boundary crossed; single-process string transform
Unclassified: 0 findings fit no axis code
Domain Scores: Leanness: 75/100 · Correctness: 97/100 · Maintainability: 100/100 · Security: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — L3 speculative factory caps grade at F

Serial mode: 1 file in scope, no fan-out per `shared/domain-fanout.md`.

## Findings

### [CRITICAL] Speculative factory stack with single implementor
- **Domain:** Leanness (L3)
- **Verified by:** RAN — repo-wide ripgrep for all 8 symbols plus `python3 -c "from evals.fixtures.speculative_factory import FormatterRegistry"` import/behaviour check
- **Evidence:** `evals/fixtures/speculative_factory.py:4-31` — `IMessageFormatter` (line 4) implemented only by `StandardUppercaseFormatter` (line 14); `IFormatterFactory` (line 9) implemented only by `StandardFormatterFactory` (line 19); `StandardFormatterFactory.create_formatter()` (line 20-21) only does `return StandardUppercaseFormatter()`; `FormatterRegistry.get_formatted()` (line 28-31) only does `factory.create_formatter()` → `formatter.format_text(text)`. Ripgrep across the run dir returns hits in this file only — zero second implementors, zero external callers, no `getattr`/`importlib`/DI/manifest indirection.
- **Failure scenario:** Permanent carrying tax, not a runtime crash. Three layers of indirection to execute `text.upper()`. Every reader, test, migration, and future formatter must traverse `Registry → Factory → Formatter → str.upper()`; adding a real second formatter requires touching all three layers, and deleting the abstraction requires proving the same single-implementor fact again.
- **Fix:** Delete the abstraction stack (scope: module). Inline to `def format_text(text: str) -> str: return text.upper()` or a single function in the registry, removing both ABCs and `StandardFormatterFactory`. No trade-off statement required for deletions.

### [MINOR] Unknown registry key raises bare `AttributeError` on `None`
- **Domain:** Correctness (A8)
- **Verified by:** RAN — executed `FormatterRegistry().get_formatted('missing','hello')`, observed `AttributeError: 'NoneType' object has no attribute 'create_formatter'`
- **Evidence:** `evals/fixtures/speculative_factory.py:28-30` — `factory = self._factories.get(key)` followed unguarded by `factory.create_formatter()`. `dict.get` returns `None` for any key other than `"standard"`.
- **Fix:** Localized cleanup (scope: local). Either `factory = self._factories[key]` to raise `KeyError`, or explicit `if factory is None: raise KeyError(key)` / `ValueError`.

## Aligns well
- `StandardUppercaseFormatter.format_text` is a pure total function on the happy path — `RAN` confirmed `get_formatted('standard','hello') == 'HELLO'` (A1).
- File docstring honestly labels the design as unearned generality, so intent is unambiguous (B4).

Disputed: Maintainability graded Info — single-implementor ABCs and pass-through factory also match B5 symptoms, but Leanness owns the failure scenario (carrying tax); no separate deduction taken.