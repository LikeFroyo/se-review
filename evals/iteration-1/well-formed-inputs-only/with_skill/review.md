Reviewing your fixtures — reading the test files.
Got the two files — checking the surrounding run for context.
Small scope — running the review serially across the relevant domains.
The pattern is clear — verifying the failure concretely before grading.
# Review: `evals/fixtures/validate_email.py` + `evals/fixtures/test_fixture_realism.py`

`3 findings · C:0 M:2 m:0 i:1 · Mean 97/100 · Final Grade B`
`Covered: 2/2 files · Scope: focused on: evals/fixtures/validate_email.py, evals/fixtures/test_fixture_realism.py · Not examined: 0 — none`
`Paths: 0 · Unmapped: 0 — every crossing reached and classified`
`Unclassified: 0 findings fit no axis code`
`Domain Scores: Correctness: 80/100 · Security: 100/100 · Maintainability: 100/100 · Leanness: 100/100 · Interoperability: 100/100 · Operations: 100/100`
`Gated by: weakest domain: Correctness (B) — neither Critical cap bound`

Serial review (2 files, below fan-out ceiling in `shared/domain-fanout.md`).

## Findings

### [MAJOR] Validator exercised only on well-formed input — rejection path untested
- **Domain:** Correctness (A6)
- **Verified by:** RAN — ran `normalise_email` on `['', 'no-at-sign', '@', 'a@', '@example.com', 'a@b@c']` via `python3 -c`; emulated the two parametrised tests on `WELL_FORMED` (all pass)
- **Evidence:** `test_fixture_realism.py:6-10` — fixture is three valid addresses only (`WELL_FORMED = ["alice@example.com", "bob.smith@example.co.uk", "carol@example.org"]`); `test_fixture_realism.py:13-21` — both tests parametrise exclusively over `WELL_FORMED`, asserting domain-lowercasing and local-part preservation. No malformed, empty, whitespace-padded, `@`-less, or multi-`@` case appears.
- **Failure scenario:** `normalise_email('no-at-sign')` returns `'no-at-sign'` (non-empty), `'@'` returns `'@'`, `'a@'` returns `'a@'` — all treated as valid per the contract in `validate_email.py:1` ("any non-empty return as a valid address"). The suite stays green while the rejection path it claims to guard does not exist. This is the literal `fixture-realism.md` trigger: "A parser or validator is exercised exclusively on valid data, never on the invalid data it claims to reject."
- **Fix:** Add rejection cases to the fixture (module scope): `@`-less input, empty/whitespace-only, leading/trailing whitespace, `a@`, `@example.com`, `a@b@c`, uppercase local+domain. Assert each is rejected (empty return or raise, per chosen contract) rather than normalised. Ruling: code-is-right is not assumed — the fix states the contract first, then the tests.
- **Trade-off:** Cost is maintenance, not runtime: a larger fixture needs triage when the contract changes, and locking in rejection behaviour now constrains future callers that rely on passthrough. Scope: module (test file only).

### [MAJOR] `normalise_email` accepts malformed input as valid — unenforced boundary contract
- **Domain:** Correctness (A8)
- **Verified by:** RAN — same execution as above; observed `'' -> ''` (only rejection signal) vs `'no-at-sign' -> 'no-at-sign'`, `'@' -> '@'`, `'@example.com' -> '@example.com'`, `'a@b@c' -> 'a@b@c'`, `'ALICE@EXAMPLE.COM' -> 'ALICE@example.com'`
- **Evidence:** `validate_email.py:3-9` — `local, sep, domain = trimmed.partition("@"); if not sep: return trimmed.lower()` passes `@`-less input through, and the `return f"{local}@{domain.lower()}"` path accepts empty local, empty domain, and multiple `@` without complaint. Combined with `validate_email.py:1` (non-empty means valid), there is no construction path that rejects.
- **Failure scenario:** Any caller following the documented contract treats `'no-at-sign'`, `'@'`, or `'a@b@c'` as a deliverable address: bad row stored, downstream send attempted, or duplicate-account keyed on garbage. Demonstrated statically and by execution; no caller in scope, so blast radius is bounded to the contract, hence Major not Critical.
- **Fix:** Decide the contract at the boundary (boundary scope): either return `""` on malformed input or raise `ValueError`, and validate exactly one `@`, non-empty local and domain, no whitespace remainder. Update all callers to handle the rejection explicitly. Structure first (what "valid" means), behaviour second.
- **Trade-off:** Stricter rejection risks breaking callers that depend on lenient passthrough (e.g. display-only normalisation); requires auditing every `normalise_email` call site and agreeing on empty-vs-exception. Extra validation is O(n) string checks — negligible latency. Scope: boundary (function contract + callers).

### [INFO / SUGGESTION] Unvalidated email crossing is a lead, not a demonstrable attack path
- **Domain:** Security (S1)
- **Verified by:** READ — boundary inventory over the two in-scope files; RAN output above reused as reachability check
- **Evidence:** `validate_email.py:3` — `normalise_email(raw: str)` is the sole crossing; source is the `raw` string (attacker-controllable in any signup/import flow), boundary performs shape-only handling (`strip`, `partition`, `lower`), sink is absent — no caller, store, send, or auth decision in scope.
- **Fix:** No code change now. When a caller is added, enforce validation at this crossing (allow-list shape, reject don't sanitise) and record provenance so downstream does not re-trust the normalised string. Re-grade as path (`Source: caller input → Boundary: normalise_email → Sink: <store/send/auth>`) once the sink exists.
- **Note:** Per `axis-codes.md`, source + boundary with no demonstrated sink is a lead (Major at most); with no sink named at all it is capped here at Info.

## Aligns well
- Correctness (A1): function is total on strings — no exception, no `None`, no hidden branch; three-line logic is easy to reason about.
- Maintainability (B4): names (`normalise_email`, `WELL_FORMED`, `raw/trimmed/local/domain`) state intent; tests assert one property each.
- Leanness (L1): no dead code, no speculative surface — 9-line implementation, 21-line suite.