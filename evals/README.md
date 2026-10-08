# se-review evals

One hundred and two test fixtures with planted defects and clean controls, following the published eval-driven iteration pattern (with-skill run vs baseline, graded against 860 deterministic assertions — 116 of them
role-tagged `verdict` / `probe` / `strict`, defined below).

### Assertion roles

Every assertion carries a role in `evals.json`, and the role decides which rate it lands in.
Mixing them is how a corpus reports a skill as good at narration: a probe assertion is earned
by any review that honoured the output format, whatever it found, so averaging one in with a
verdict assertion lets conformity substitute for correctness.

| role | what it grades | in the quality rate? |
|---|---|---|
| `verdict` | whether the review found and described the defect | yes |
| `strict` | whether the proposed **fix** is correct — "Fix replaces the price-keyed guard with an identity-keyed one" | yes |
| `probe` | whether the mechanism ran at all — "Output includes 'Aligns well'", "Header matches pattern: 1 finding" | no |

`strict` is a quality claim, not a stricter `probe`: a review can find the defect and propose
the wrong repair, and those two are different failures. It was defined in code comments and
nowhere else, and `verdict_rates()` fell through both of its branches — so 7 assertions sat in
neither numerator nor denominator, meaning **finding a defect and fixing it wrong scored the
same**, with nothing printed. Roles are now counted and reported per run, and a role nothing
defines cannot be excluded from a quality rate on the strength of its own label.

Roles come from the corpus, not from the verdict. A verdict need not echo them: the roles
describe the question, so requiring each verdict to carry a copy of the question meant the
verdict/probe split stayed unreportable until the whole corpus had been re-graded.

## Fixtures & Test Matrix (860 Assertions)

| # | Fixture | Domain & Focus | Planted Defect / Feature | Expected Findings | Assertions |
|---|---|---|---|---|---|
| 1 | `fixtures/dead_code.py` | Leanness / Waste | Unused `LegacyPriceAdapter` + commented code | 1 × CRITICAL L1/L2 | 9 |
| 2 | `fixtures/retry.py` | Operations / Resilience | Immediate retry loop without backoff or jitter | 1 × MAJOR C3 | 9 |
| 3 | `fixtures/injection.py` | Security | f-string SQL injection + hardcoded live secret | 2 × CRITICAL A5 | 9 |
| 4 | `fixtures/nplusone.py` | Correctness / Data | Nested N+1 query loop over members and teams | 1 × MAJOR A3 | 7 |
| 5 | `fixtures/clean.py` | Control (Resilience) | Clean code (bounded exponential backoff + jitter) | 0 findings, `Aligns well` | 8 |
| 6 | `fixtures/concurrency.py` | Correctness / Concurrency | Check-then-act & non-atomic increment on shared dict | 1 × MAJOR A2 | 8 |
| 7 | `fixtures/swallowed_error.py` | Correctness / Logic | Bare except clause silently suppressing errors | 1 × CRITICAL A1 | 10 |
| 8 | `fixtures/complexity.py` | Maintainability / Complexity | Cyclomatic complexity >15, nesting >4, god method | 1 × MAJOR B1/B5 | 8 |
| 9 | `fixtures/memory_leak.py` | Operations / Performance | Unbounded global cache accumulation without TTL/eviction | 1 × MAJOR C1/C2 | 8 |
| 10 | `fixtures/idor_access.py` | Security | Broken Object-Level Authorization (IDOR / BOLA) | 1 × CRITICAL A5 | 8 |
| 11 | `fixtures/deadlock.py` | Correctness / Concurrency | Lock-order inversion deadlock in account transfers | 1 × MAJOR A2 | 8 |
| 12 | `fixtures/ssrf_webhook.py` | Security | Server-Side Request Forgery (SSRF) accepting unvalidated URL | 1 × CRITICAL A5 | 8 |
| 13 | `fixtures/hot_loop.py` | Operations / Performance | Quadratic string concatenation & unbuffered disk I/O in loop | 1 × MAJOR C1 | 8 |
| 14 | `fixtures/missing_timeout.py` | Operations / Resilience | Network HTTP request missing explicit connect/read timeout | 1 × MAJOR C3 | 8 |
| 15 | `fixtures/breaking_schema.py` | Correctness / API Contracts | Breaking schema change (renamed ID and mutated type) | 1 × MAJOR A4 | 8 |
| 16 | `fixtures/non_idempotent_payment.py` | Correctness / API Contracts | Payment mutation lacking idempotency keys | 1 × CRITICAL A4 | 8 |
| 17 | `fixtures/unpinned_manifest.json` | Leanness / Supply Chain | Unbounded wildcard dependency and dev dependency in prod | 1 × MAJOR L5 | 8 |
| 18 | `fixtures/ai_hallucination.py` | Leanness / Synthetic Code | Hallucinated non-existent library method and error masking | 1 × CRITICAL L6 | 8 |
| 19 | `fixtures/speculative_factory.py` | Leanness / Waste | 4-layer speculative factory hierarchy for 1 implementor | 1 × CRITICAL L2/L3 | 8 |
| 20 | `fixtures/pii_logging.py` | Operations / Observability | Logging plaintext passwords, SSN, and credit card CVV | 1 × CRITICAL C4 | 8 |
| 21 | `fixtures/poison_message.py` | Operations / Distributed | Message queue worker lacking Dead Letter Queue (DLQ) | 1 × MAJOR C5 | 8 |
| 22 | `fixtures/stale_flag.py` | Operations / Delivery | Feature flag without fallback default and 18-month stale flag | 1 × MAJOR C6 | 8 |
| 23 | `fixtures/mock_cheat.py` | Correctness / Testing | Test adequacy cheat mocking function under test with tautology | 1 × MAJOR A6 | 8 |
| 24 | `fixtures/flaky_sleep.py` | Correctness / Testing | Flaky test using wall-clock sleep instead of thread synchronization | 1 × MAJOR A6 | 8 |
| 25 | `fixtures/clean_service.py` | Control (Full Suite) | Exemplary payment service with resilience, logging, tenant security | 0 findings, `Aligns well` | 8 |
| 26 | `fixtures/dual_write.py` | Operations / Distributed | Publish-after-commit dual write without atomic outbox | 1 × MAJOR C5 | 8 |
| 27 | `fixtures/comment_drift.py` | Maintainability / Clarity | Stale retry comment plus drifted docstring, one root cause | 1 × MAJOR B4 | 8 |
| 28 | `fixtures/stale_cli.py` + `stale_cli_README.md` | Maintainability / Clarity | README documents `--output`, parser defines `--out-dir` | 1 × MAJOR B4 | 8 |
| 29 | `fixtures/stale_error.py` | Operations / Observability | Error string names removed `--output` flag | 1 × MAJOR C4 | 8 |
| 30 | `fixtures/weak_assertions.py` | Correctness / Testing | Weak assertions plus untested 0/100 boundaries, one root cause | 1 × MAJOR A6 | 8 |
| 31 | `fixtures/token_validation.py` | Security | JWT decoded with `verify_signature: False`, no `aud`/`exp` check | 1 × CRITICAL A5 | 8 |
| 32 | `fixtures/weak_password_hash.py` | Security | Passwords stored as unsalted single-pass SHA-256 | 1 × CRITICAL A5 | 9 |
| 33 | `fixtures/session_fixation.py` | Security | Session ID minted pre-auth and reused after login | 1 × CRITICAL A5 | 7 |
| 34 | `fixtures/tls_verify_disabled.py` | Security | Outbound `requests` with `verify=False` carrying a bearer token | 1 × CRITICAL A5 | 8 |
| 35 | `fixtures/unsafe_deserialization.py` | Security | `pickle.loads` on client-supplied cache bytes | 1 × CRITICAL A5 | 8 |
| 36 | `fixtures/path_traversal.py` | Security | Request-supplied path joined with no containment check | 1 × CRITICAL A5 | 8 |
| 37 | `fixtures/bfla_admin_route.py` | Security | Admin CSV export route with no role check | 1 × CRITICAL A5 | 8 |
| 38 | `fixtures/ecb_mode_cipher.py` | Security | AES-ECB field encryption | 1 × MAJOR A5 | 8 |
| 39 | `fixtures/cors_reflect_origin.py` | Security | Origin echoed into CORS with credentials allowed | 1 × MAJOR A5 | 9 |
| 40 | `fixtures/login_no_throttle.py` | Security | Login with no throttle and a user-enumerating message | 1 × MAJOR A5 | 9 |

### Audit & Evolve — Leanness (evals 41–45)

| # | Fixture | Domain & Focus | Planted Defect / Feature | Expected Findings | Assertions |
|---|---|---|---|---|---|
| 41 | `fixtures/build_integrity.py` | Leanness / Supply Chain | Ungated install script + floating CI/image refs | 2 × CRITICAL L5 | 9 |
| 42 | `fixtures/typosquat_dependency.py` | Leanness / Supply Chain | `requsts` and `colourama` lookalike packages | 1 × MAJOR L5 | 8 |
| 43 | `fixtures/dead_persistence.py` | Leanness / Waste | Unread columns + frozen migrations + unretired credential | 1 × CRITICAL L1, 1 × MAJOR L1 | 10 |
| 44 | `fixtures/completion_markers.py` | Leanness / Synthetic Code | Reachable stub reporting success + unimplemented guarantees | 1 × CRITICAL L6, 1 × MAJOR L6 | 9 |
| 45 | `fixtures/vendored_fork.py` | Leanness / Waste | Three in-tree upstream copies frozen at 2019 with unpatched CVEs | 1 × MAJOR L4 | 8 |

### Audit & Evolve — Operations (evals 46–53, 73–74)

| # | Fixture | Domain & Focus | Planted Defect / Feature | Expected Findings | Assertions |
|---|---|---|---|---|---|
| 46 | `fixtures/health_and_shutdown.py` | Operations / Resilience | Liveness querying the database + `os._exit` on SIGTERM, 15s grace vs 40s job | 1 × CRITICAL C3, 1 × MAJOR C3 | 9 |
| 47 | `fixtures/unbounded_fanout.py` | Operations / Performance | 50 000-wide unbounded fan-out + quadratic `total_due` | 2 × CRITICAL C1/C2 | 9 |
| 48 | `fixtures/saga_no_compensation.py` | Operations / Distributed | Three-service checkout with no saga and no compensation | 1 × CRITICAL C5 | 9 |
| 49 | `fixtures/cache_no_invalidation.py` | Operations / Performance | Write path skips the cache, no TTL, full flush as refresh | 1 × MAJOR C1 | 9 |
| 50 | `fixtures/lease_no_fencing.py` | Operations / Distributed | Redis TTL lease with no fencing token, release left to expiry | 1 × CRITICAL C5 | 9 |
| 51 | `fixtures/missing_audit_trail.py` | Operations / Observability | Debug-only audit log, unlogged refund, unlogged data export | 1 × MAJOR C4 | 9 |
| 52 | `fixtures/config_fails_open.py` | Operations / Delivery | API key defaults empty, TLS verify defaults false, secret fallback committed | 1 × CRITICAL C6 | 9 |
| 53 | `fixtures/irreversible_rollback.py` | Operations / Delivery | `DROP COLUMN` shipped with a downgrade that raises | 1 × CRITICAL C6 | 9 |
| 73 | `fixtures/region_failover.py` | Operations / Durability | Standby promoted while the primary still writes, nothing fences the old side; the late joiner resumes writing | 1 × CRITICAL C7, 1 × MAJOR C7 | 10 |
| 74 | `fixtures/personal_data_lifecycle.py` | Operations / Data Protection | Erasure touches only the primary row; the backup posture cannot meet the stated objective | 2 × CRITICAL C8 | 10 |

### Audit & Evolve — Maintainability (evals 54–61)

| # | Fixture | Domain & Focus | Planted Defect / Feature | Expected Findings | Assertions |
|---|---|---|---|---|---|
| 54 | `fixtures/unit_scale_error.py` | Maintainability / Clarity | `subtotal_cents` holding a float; ×1000 scale errors in two conversions | 1 × CRITICAL B4 | 9 |
| 55 | `fixtures/impossible_state.py` | Maintainability / Complexity | Order lifecycle as four independent booleans, no transition checks | 1 × CRITICAL B1 | 9 |
| 56 | `fixtures/ambient_clock_rules.py` | Maintainability / Evolvability | Clock, `random()`, env var and module user read inside business rules | 1 × CRITICAL B2 | 10 |
| 57 | `fixtures/no_test_seam.py` | Maintainability / Evolvability | Module-level SQS + engine, test setup dwarfing the function | 2 × MAJOR B2 | 9 |
| 58 | `fixtures/unenforced_invariant.py` | Maintainability / Clarity | Lock and transaction preconditions stated only in comments | 1 × MAJOR B4 | 9 |
| 59 | `fixtures/implementation_names.py` | Maintainability / Clarity | Storage engine in a name, permanent `_v2`/`_temp` suffixes, third term | 1 × MAJOR B4 | 9 |
| 60 | `fixtures/transposed_arguments.py` | Maintainability / Complexity | Adjacent same-typed parameters, `clamp` docstring admitting transposed calls | 1 × MAJOR B1 | 9 |
| 61 | `fixtures/boundary_error_policy.py` | Maintainability / Design | Bare except collapsing failure and absence into one `None` | 1 × MAJOR B5 | 9 |

### Audit & Evolve — Correctness (evals 62–69)

| # | Fixture | Domain & Focus | Planted Defect / Feature | Expected Findings | Assertions |
|---|---|---|---|---|---|
| 62 | `fixtures/cancelled_child_work.py` | Correctness / Concurrency | Timeout path never cancels the child task; `create_task` with no handle | 2 × CRITICAL A2 | 9 |
| 63 | `fixtures/lost_update_race.py` | Correctness / Data | Read-then-write stock reservation at default `READ COMMITTED` | 1 × CRITICAL A3 | 9 |
| 64 | `fixtures/string_truthiness.py` | Correctness / Logic | `"false"` and `"0"` read as true; zip coerced through `int` | 1 × CRITICAL A1 | 9 |
| 65 | `fixtures/unstable_pagination.py` | Correctness / API Contracts | `LIMIT/OFFSET` over a growing table; closed status set; null/cleared conflation | 1 × CRITICAL A4, 1 × MAJOR A4 | 9 |
| 66 | `fixtures/short_circuit_side_effects.py` | Correctness / Logic | Guard clauses skipping the audit write and metric on failure paths | 1 × MAJOR A1 | 9 |
| 67 | `fixtures/lock_starvation.py` | Correctness / Concurrency | Lock held across a batch loop and a blocking queue drain | 1 × MAJOR A2 | 9 |
| 68 | `fixtures/soft_delete_uniqueness.py` | Correctness / Data | Unique indexes spanning tombstones; queries not scoped by `deleted_at` | 1 × MAJOR A3 | 9 |
| 69 | `fixtures/skipped_tests.py` | Correctness / Testing | `skip` with no reason, `xfail` with no owner or expiry | 1 × MAJOR A6 | 9 |

### New Sub-Domains — AI Systems & Type Contracts (evals 70–72)

| # | Fixture | Domain & Focus | Planted Defect / Feature | Expected Findings | Assertions |
|---|---|---|---|---|---|
| 70 | `fixtures/rag_prompt_injection.py` | Correctness / AI Systems | Ticket body + unlabelled KB chunks in the prompt; unvalidated tool args; unfiltered tenant index | 2 × CRITICAL A7, 1 × MAJOR A7 | 11 |
| 71 | `fixtures/model_output_trusted.py` | Correctness / AI Systems | Completion interpolated into SQL/HTML, regex-parsed into routing and a discount, fetched as a URL | 1 × CRITICAL A7 | 10 |
| 72 | `fixtures/unchecked_casts.py` | Correctness / Type & Contracts | `Any` clients, untyped webhook payload, defaulted missing amount | 1 × CRITICAL A8 | 10 |

### New Domain — Interoperability (evals 75–78)

| # | Fixture | Domain & Focus | Planted Defect / Feature | Expected Findings | Assertions |
|---|---|---|---|---|---|
| 75 | `fixtures/settlement_export.py` | Interoperability / Encoding & Text | Implicit UTF-8 write against Latin-1/CRLF read, byte-truncating a string, NFC vs NFD key | 2 × CRITICAL D1 | 10 |
| 76 | `fixtures/dst_boundary_schedules.py` | Interoperability / Time & Locale | Naive 02:00 wall-clock schedule; dd/MM read against MM/dd written; ISO weeks | 1 × CRITICAL D2, 1 × MAJOR D2 | 10 |
| 77 | `fixtures/money_conversion.py` | Interoperability / Numeric Boundaries | Float money as JSON, ×10 000 against ÷10, `int()` truncation | 1 × CRITICAL D3 | 10 |
| 78 | `fixtures/field_name_mismatch.py` | Interoperability / Wire Formats | `customerId` read vs `customer_id` written, intolerant consumer, unpinned format | 1 × CRITICAL D4, 2 × MAJOR D4 | 9 |

### Scoring Caps (eval 79)

| # | Fixture | Domain & Focus | Planted Defect / Feature | Expected Findings | Assertions |
|---|---|---|---|---|---|
| 79 | `fixtures/operations_collapse.py` | Operations, all five domains | Five Major defects in one file and **zero Critical**, so the grade is bound by the weakest-domain cap rather than the Critical cap | 5 × MAJOR (C2, C3 ×3, C5) | 12 |

Eval 79 tests the arithmetic in `shared/severity-and-rules.md` § Domain scoring, not a defect class: the
mean across domains lands in the A band while Operations lands in F, so the final grade must be F with no
Critical present. It also asserts the negative — no invented findings in the four clean domains.

Eval 65 carries two guidelines (`pagination-and-lists.md` new, `backward-compatibility.md` updated); eval 68 exercises
the soft-delete scope in `query-patterns.md` and the visibility rules in `isolation-and-consistency.md`. That is
9 upserted guidelines across 8 fixtures.

### Suppression Ablation — the gate's own falsification (evals 80–91)

Two panels, and the second matters more than the first. A gate that silences every finding
scores **perfectly** on the false-positive panel and zero on the false-negative one.

| # | Fixture | Panel | Shape | Expected | Assert. |
|---|---|---|---|---|---|
| 80 | `suppress_unbounded_queue.py` + `..._CONSTRAINTS.md` | FP | unbounded store, measured backlog | 0 above Info | 9 |
| 81 | `suppress_unfiltered_fanout.py` + `..._CONSTRAINTS.md` | FP | unfiltered dispatch, consumer self-reduces | 0 above Info | 9 |
| 82 | `suppress_lockless_accumulator.py` + `..._CONSTRAINTS.md` | FP | one writer, no lock | 0 above Info | 10 |
| 83 | `suppress_ungated_memory.py` + `..._CONSTRAINTS.md` | FP | ungated slots, staleness published | 0 above Info | 9 |
| 84 | `suppress_constant_column.py` + `..._CONSTRAINTS.md` | FP | deliberately constant column | 0 above Info | 8 |
| 85 | `suppress_coincident_formulas.py` + `..._CONSTRAINTS.md` | FP | two estimators, deliberate cross-check | 0 above Info | 9 |
| 86 | `suppression_blind_sibling.py` | FN | defect **inside** the covered region | 1 × MAJOR A1 | 10 |
| 87 | `suppression_blind_nan_contract.py` | FN | the constraint's own sentence names the defect | 1 × CRITICAL A1 | 11 |
| 88 | `suppression_blind_backlog_measure.py` | FN | licence honoured, the promise it also makes broken | 1 × MAJOR A3 | 10 |
| 89 | `suppression_blind_unargued_clamp.py` | FN | argued twin vs unargued twin, three lines apart | 1 × MAJOR A1 | 11 |
| 90 | `suppression_blind_boundary_breach.py` + `per_contract_layer.py` | FN | breach of the boundary the constraint describes | 1 × MAJOR B5 | 10 |
| 91 | `suppression_ledger_unprovable_site.py` | FN | text search finds one site; a registry hides the second | 1 × MAJOR A1 | 11 |
| 92 | `numeric_plausibility.py` | Correctness / Logic | rate over an elapsed span that approaches zero: one event reads 5.7e5/s | 1 × MINOR A1 | 5 |
| 93 | `incremental_drift.py` | Correctness / Data | reclassify mutates the entry, never the balance; drift 125 vs 95, permanent | 1 × MAJOR A3 | 4 |
| 94 | `state_machine_exit.py` | Correctness / Logic | a stated 1h expiry policy, `APPROVAL_TTL_SECONDS` declared and never read | 1 × MAJOR A1 | 5 |
| 95 | `cold_start_estimator.py` | Correctness / Logic | slope over fewer than two samples: denominator is 0 | 1 × MINOR A1 | 4 |
| 96 | `test_expected_value.py` + `pricing.py` | Correctness / Testing | expected value re-derived from the code; `tax_rate` ignored, check green | 1 × MAJOR A6 | 5 |
| 97 | `test_fixture_realism.py` + `validate_email.py` | Correctness / Testing | well-formed inputs only; `"not-an-email"` returns truthy | 1 × MINOR A6 | 5 |
| 98 | `test_concurrency_coverage.py` + `counter.py` | Correctness / Testing | unsynchronised read-modify-write, checked single-threaded | 1 × MAJOR A6 | 5 |
| 99 | `work_unit_retry.py` | Operations / Resilience | retry restarts the batch: 4 ledger lines for 3 entries | 1 × MAJOR C3 | 5 |

Every FP fixture is two files on purpose: the constraint document is part of the task, not a
hint. If it were not in the workspace, the gate arm would fail for a reason unrelated to the
gate and the ablation would prove nothing.

Eval 82 is the sharpest FP — its shape is structurally identical to eval 6's planted defect,
a module-level mutable dict mutated without a lock, which the corpus spends 8 assertions
teaching a reviewer to flag. A gate that cannot overrule a pattern the rubric installed is not
a gate.

### The eight guidelines added this round, and how each was proved (evals 92–99)

Eight guidelines were added for defect classes a corpus sweep found uncovered. A guideline with no
fixture is an assertion about defects, not a check on them, so each got one — and **every fixture's
defect was proved by execution before the eval was written.** Three first attempts failed that test
and were corrected rather than shipped:

| # | Guideline | Proved by running it |
|---|---|---|
| 92 | numeric plausibility | one recorded event returns **571,424 events/second** — finite, typed, wrong |
| 93 | incremental aggregate drift | reclassify 40→10 leaves `balance` at 125 while entries sum to 95 |
| 94 | state machine completeness | a request 99,999s old is approved under a 1-hour expiry policy |
| 95 | cold start and reset | `trend()` on one sample raises `ZeroDivisionError` |
| 96 | expected-value provenance | `price_for(100, 0.15, tax_rate=0.20)` → **85.0**, should be 102.0; check is green |
| 97 | fixture realism | `normalise_email("not-an-email")` → `'not-an-email'`, truthy, no test covers it |
| 98 | concurrency coverage | **2023 of 2400 updates lost** at a 1µs switch interval; **0 lost** at the 5ms default |
| 99 | work-unit retry safety | first attempt fails at index 0, retry → 4 ledger lines for 3 entries |

Eval 98 is the sharpest result in the corpus. Identical code and an identical green check lose
**no** updates at Python's default thread switch interval and lose **2023 of 2400** at one
microsecond. The suite passing is a property of the scheduler, not of the code — which is the
entire argument for checking concurrency coverage rather than trusting green, arrived at by trying
and failing to reproduce the race at the default setting.

**An assertion should encode a property, not a guess at the answer.** Eval 92 originally
asserted the numeric-plausibility finding would be graded MINOR or lower, on my reasoning that no
production failure is demonstrable. The first live run disagreed: the reviewer graded it MAJOR, and
on the merits the reviewer is right — a monitoring value wrong by five orders of magnitude is an
observable defect, which is exactly what MAJOR names, even though it is not data loss or outage.
The assertion was the error, not the run. It now tests the property that actually discriminates —
*not Critical, and not dismissed as Info* — so it still catches over-grading and under-grading
without encoding a rung I had no evidence for. An assertion that pins a specific rung is a guess
about the answer wearing the costume of a test, and the first run either confirms the guess or
reveals it was a guess.

The three corrections matter more than the table. The first `pricing.py` applied tax correctly
(85 × 1.2 = 102.0), so the "defect" did not exist; the first `counter.py` lost no updates at any
setting tried. A fixture whose defect cannot be demonstrated is worse than no fixture, because it
asserts a false claim and spends a run to do it.

**Total:** 102 test fixtures · 860 atomic assertions.

Every count in this table derives from `evals/evals.json`, which is the single source of truth.

## Comparative Benchmark (Iteration 1)

```
Overall Assertions: With Skill: 703/1079 (65.2%)
Overall Assertions: Baseline: 63/183 (34.4%)
Paired evals (both arms current): 22 - 278 assertions
Admissible denominator: 102 of 102 evals (the rest are void, unverified or absent)
Run-to-run variance: mean within-eval sd 0.163 over 5 eval(s)
Run-to-run variance: mean within-eval sd 0.163 over 5 eval(s)
Run-to-run variance: mean within-eval sd 0.163 over 5 eval(s)
Run-to-run variance: mean within-eval sd 0.138 over 9 eval(s)
```

**This block is derived, not remembered.** `scripts/grade_evals.py` prints it under
**This block is checked, not remembered.** `scripts/grade_evals.py` builds it under PUBLISHED
SUMMARY from the same numbers it aggregates, and a test asserts the two agree. It did not, twice.
It sat reading `643/689 (93.3%)` and `+71.9%` weeks after the correction that produced
`409/640 (63.9%)` -- the delta dividing a with_skill numerator by a baseline denominator
belonging to a different population, over verdicts that no longer matched the questions asked
of them -- while asserting run-to-run variance was unmeasured weeks after it was measured. Then it
was pasted from the grader's output and drifted again inside the hour, when authoring the corpus
moved the denominator to 36. Generating it was not enough; pasting it is still remembering.

**Read the denominator before the rate.** 640 of 860 declared assertions is not 74 percent of
the corpus scored well — it is **38 of 102 fixtures**, and the other 64 split four ways:

| state | with_skill | what it means and what it needs |
|---|---|---|
| current | 38 | verdict matches the corpus; admitted to the aggregate |
| void | 8 | verdict disagrees with the corpus; needs re-grading |
| unverified | 40 | no `assertion_results` recorded; cannot be checked either way |
| absent | 16 | never run |

Void and unverified are both excluded, so no reported rate is inflated by them, but they are
not the same defect. A void verdict's evidence contradicts the corpus; an unverified one's has
never been examined. Conflating them would send the next person to re-grade 40 verdicts that
were never wrong.

### What the 64.2% does and does not measure

**Read the two columns with suspicion, for different reasons.**

The in-session baseline is **too harsh**. Those numbers come from guideline-reverted reviews
run *inside the same session* that wrote the guidelines; an independent blind re-measurement
below showed the reverted skill catches 23 of 24 defects unaided. Treat the baseline as a
vocabulary-and-format comparison, not a defect-detection measurement.

The with-skill 64.2% is measured over **36 of 102 fixtures**. Every earlier figure this file
published was wrong, in three different ways, and each is recorded here rather than deleted:
**93.3%** over "99 fixtures, 54 attributable, 45 never run" counted 99 fixtures when the corpus
declares 102 and aggregated over verdicts whose assertions no longer matched the questions
asked of them — and the sentence was truncated mid-word, which is how a figure nobody re-reads
announces itself. Then **63.9% over 38 of 102**, correct on its day, became wrong the moment
the corpus was authored: rewriting the assertions of fixtures 80-85 voided two stored verdicts
and moved the denominator to 36.

Measured against the corpus as it now stands:

| Measure | Value |
|---|---|
| Fixtures in the corpus | **102** |
| Declared assertions | **860** |
| Verdicts admissible to the aggregate (`with_skill`) | **40** |
| Assertions those verdicts score | **635** |
| With-skill score on them | **416/635 (65.5%)** |
| Verdicts void — recorded assertions disagree with the corpus | **10** |
| Verdicts unverified — no `assertion_results` recorded | **36** |
| Fixtures never run | **16** |

So **40 of 102 fixtures are currently measurable at all.**

Four verdicts were recovered from that unverified column by re-grading a stored review body
(`--recover-verdicts`), which moved 36 to 40 and the rate to 65.5%. Two of the four re-graded
**lower** than the score they had recorded — one from 9/9 to 8/9 and one from 9/9 to **6/9** —
because the stored summary came from an earlier grader. Each keeps the number it replaced under
`recovered.summary_before`, so both are readable.

The void count moved from 8 to 10, and the denominator from 38 to 36, because the no-axis
corpus rewrite changed the assertion text of fixtures 80-85. That is the currency mechanism
working: a verdict graded against questions the corpus has since reworded no longer answers
anything asked. It also means **every authoring pass costs coverage**, which is worth knowing
before deciding the corpus is cheap to edit. Every percentage in this file that
does not name its denominator should be read as unverified.

The 8 void verdicts are evidence that contradicts the corpus. The 40 unverified ones are not
evidence about anything: a verdict carrying no `assertion_results` cannot be tied to the
questions it was asked, so it is indistinguishable from a verdict for a fixture that no longer
exists. They are kept on disk because a review body may still be re-gradable by inspection, and
they are counted separately rather than folded into a pass rate, because folding them in is what
made the previous headline wrong.


Two facts in that subset matter more than the aggregate:

- **`eval-clean` scored 3/8 and `eval-clean-service` 4/8** — and the diagnosis recorded at the time
  was wrong in a way that mattered. It was read as *the skill over-reports on clean code*. It does
  not: **both fixtures contain real defects, and the skill found them.**

  | Fixture | "Clean" control asserted | What the file actually contains |
  |---|---|---|
  | `clean.py` | zero findings above Info | `urllib.error.HTTPError` subclasses `OSError`, so `except OSError` retries a deterministic 4xx; `_backoff` also runs on the final attempt before the raise |
  | `clean_service.py` | zero findings above Info | `execute_with_resilience(..., max_attempts=0)` iterates an empty range and returns `None` from a function annotated `-> dict` |

  Both verified by execution, not by reading the stored review. The stored `review.md` had
  independently reached the same conclusion and recommended repairing the fixtures rather than
  weakening the skill — the right call, for a reason worth keeping: **a negative control whose file
  is merely *almost* clean teaches the model to grade on a distinction it cannot defend.**

  **The fixtures were not edited.** Editing a control to raise a score is the move that makes a
  benchmark worthless, even with a good reason. Instead evals 5 and 25 now assert what is true:
  the real defect **is** reported, at the right severity, and style, type-hint and docstring
  observations stay at Info. That is a stronger control than "report nothing", which cannot
  distinguish a careful reviewer from a deaf one — it now tests precision, calibration and
  deference together. The old 3/8 and 4/8 are void: `grade_evals.py` flags both as *assertion text
  reworded since the last run* and refuses to report them as evidence.

- **6 of the 12 verifiable evals sit at 100%.** Real headroom is thinner than any headline claims.

### The suppression ablation (evals 80–91) — BLOCKED, and the blocker is measured

**The experiment was not run.** A pre-flight designed for exactly this question
(`evals/ablation_preflight.py`, eight grader calls, no reviewer calls) answers it before the
~120 calls are spent, and the answer is that **the corpus cannot return a valid verdict as
designed**.

**117 assertions across the 12 panels. 38 of them — 32.5% — are collectable by saying nothing.**
A negative assertion ("does NOT recommend adding a TTL, an eviction policy, a window, or a refresh
interval") passes whenever the review stays away from the behaviour, which is the grader's own
documented rule. So a review of *entirely unrelated code* collects the whole negative set for free.
Measured directly: `eval-weak-password-hash`'s review, graded against panel 83's assertions, scores
**44.4%** — on a panel whose recorded pass was 100%.

| Panel | negative | positive | free floor |
|---|---|---|---|
| 81 | 5 | 4 | **55.6%** |
| 82 | 5 | 5 | 50.0% |
| 80, 83, 85 | 4 | 5 | 44.4% |
| 84 | 3 | 5 | 37.5% |
| 87 | 3 | 8 | 27.3% |
| 86, 88, 90 | 2 | 8 | 20.0% |
| 89, 91 | 2 | 9 | 18.2% |

The kill criterion is a **40-point** difference in false-positive rate. A corpus that awards a
third of its points for silence cannot resolve a 40-point gap: the floor is the noise, and the
signal has to fight it. Panel 89 and 91 — the two with the most positive assertions and the lowest
free floor — are the ones the criterion could actually use, and they are the two with the fewest
negative assertions by design. **The corpus's shape is the bug, and it is fixable**: an FP panel
needs at least one assertion that fails when the gate stays silent *for the wrong reason*, which no
current panel has.

**What the pre-flight also found.** Replay drift is real but small — three of four panels reproduce a
recorded 100% exactly, the fourth drifts 11 points — so the grader is *mostly* deterministic. The
earlier 22- and 33-point drift figures were my own script's fault: one panel's stored review was also
the mismatch body, so the "mismatch" was scored against itself. Two mistakes found by running the
instrument, both recorded rather than quietly fixed.

**Order of work when this is unblocked.** Fix the negative-assertion floor first — it is corpus
authoring and costs nothing to run. Then the judge's separability. Then the ablation. Running the
ablation first would have spent 120 calls producing a number whose meaning is unestablished, which is
the exact failure this pre-flight exists to prevent.

### How the ablation is meant to work

The deliberate gate in `project-tree/shared/deliberate.md` is **unproven**. This is the
experiment that proves or kills it, and it is an **ablation**, not the existing baseline pair:
both arms carry the whole rubric and differ only by the gate file.

| Arm | Tree |
|---|---|
| `with_skill` | HEAD with `shared/deliberate.md` present and referenced |
| `nosuppress` | HEAD with that one file removed and every reference deleted |

Four disjoint measures, never one aggregate — a single score can be driven down by a gate that
deletes everything:

| Measure | Reads | Gate |
|---|---|---|
| `fp_rate` | FP panel, `verdict` assertions | must fall by **≥ 40 points** |
| `fn_rate` | FN panel, `verdict` assertions | Clopper-Pearson upper bound **≤ 0.10** at n=30 |
| `silence_rate` | FN panel — a gate that reports the covered region instead of the defect | **≤ 0.20** |
| `probe_rate` | `probe` assertions | reported, **never gated** |

`probe_rate` is ungated by design: it measures whether the mechanism *ran*, and no grader can
distinguish an agent that genuinely probed from one that paraphrased the constraint document
back. `fp_rate` reads `verdict` roles only, so narration cannot move the deciding number.

**Sample size.** At 5 replicates × 6 FP fixtures, n=30 per arm, which resolves a 40-point
delta at Fisher p≈0.004 — three noise floors clear. The 40-point bar is set at the smallest
effect this n can certify; a bar below the design's resolution would be a bar inside the noise.

**The kill criterion is automated.** `scripts/eval_diagnostics.py` prints
`SUPPRESSION ABLATION: verdict rate <nosuppress> -> <with_skill>  (delta ±N pts)` and then
`KILLED` when that delta is below 40 points. The figure is net of two opposing pressures —
false-positive assertions reward silence, false-negative assertions reward catching the
planted defect — so it is necessary, never sufficient, and must be read against `fn_rate`.

**Not yet run.** These 12 fixtures have no verdicts. Until they do, the gate ships unproven and
this section is a design, not a result.

### Independent blind re-measurement (evals 31–42, 55–66)

Two arms, each a fresh agent session, each blind to `evals/`, `grading.json`, and `auditandevolve/`.
Fixtures were re-serialised with **every docstring and comment stripped** (`ast` + `ast.unparse`) — the
repo's fixture convention puts the planted defect in the docstring (`CRITICAL DEFECT: …`), which is
itself a confound. The reverted arm was reconstructed from `git HEAD` (36 guidelines, 17 sub-domains);
the current arm is this tree (87 guidelines, 29 sub-domains). Scored on the 24 evals where both arms
produced an uncontaminated run:

| Measure | With skill | Reverted | Delta |
|---|---|---|---|
| Defect **detected** at all | 24/24 (100.0%) | 23/24 (95.8%) | **+4.2 pts** |
| **Severity** correct | 22/24 (91.7%) | 14/24 (58.3%) | **+33.3 pts** |
| **Root cause** complete | 23/24 (95.8%) | 21/24 (87.5%) | **+8.3 pts** |

**What this changes.** The reverted skill, given to a competent fresh reviewer, finds 23 of these 24
defects on its own. The in-session baseline's claim of "8 of 78 evals where the reverted skill caught
nothing" does not survive independent measurement, and the headline `+77.9%` should be treated as an
upper bound produced by a non-blind methodology, not as a measurement.

What the audit-and-evolve work demonstrably contributes is **severity discipline**: the reverted arm
detected the defect but graded it too low in 9 of 24 evals (unverified JWT decode and session fixation
as Major; cross-origin reflection, ambient state, lost update, and string truthiness as Major where
Critical is correct; boundary error policy over-graded the other way). A reviewer who knows *that* a
defect is present does not need a rule naming it; a reviewer deciding *how badly* it matters does.

Coverage not scored — two agent runs returned no output and one with-skill run self-disclosed a
recursive grep that had matched `evals/evals.json`:
- evals 43–54 — with-skill run contaminated; reverted run clean
- evals 67–78 — neither arm completed

The figure this replaced — `673/673 (100.0%)` against a `149/673 (22.1%)` baseline, a `+77.9%` delta
— was wrong in both directions at once: the denominator had drifted behind 689 assertions, and 100%
across every eval was never a measured state. It is kept here only to be superseded.

Also noted and since repaired: `fixtures/ambient_clock_rules.py` contained an unintended defect that no
assertion covered — `is_promotion_active` compared an aware `datetime.now(timezone.utc)` against naive
bounds and raised `TypeError` on every call. Both blind reviewers found it and it displaced the planted
finding in both. The bounds are now timezone-aware and eval 56's assertions were re-verified unchanged.

Evals 31–40 are the Audit & Evolve iteration on `domains/correctness/security`. Their baseline column is the
guideline-reverted review of the same fixtures: with the five new guideline files removed, 8 of the 10 defects
went unreported at any severity, the ninth was caught but stripped of its root cause and fix, and the tenth
(eval 37) was caught by the pre-existing IDOR/default-deny bullets alone.

## How to run

1. **Validate Skill & Test Suite:**
   ```bash
   python scripts/validate_skill.py
   ```
   Validates skill frontmatter, dynamic hierarchy, link integrity, and evals schema.

2. **Aggregate Benchmark & Grades:**
   ```bash
   python scripts/grade_evals.py
   ```
   Aggregates assertion results across all 79 test fixtures, verifies grading consistency, and
   updates `benchmark.json`. Exits 0 even when stale — it is a reporting aggregator;
   `validate_skill.py` remains the structural gate.

3. **Check Eval Health Before Trusting Any Number:**
   ```bash
   python scripts/eval_diagnostics.py --determinism 5
   ```
   Reports headroom, trigger rate, plumbing failures, task tells, the verdict-vs-probe split,
   the suppression ablation verdict, and grader flip rate. Reads `benchmark.json`, so run step 2
   first. Treat saturation, a flip rate, a `KILLED` ablation, or a row of "did not produce a
   review" as blocking.

4. **Run with replicates, when the delta matters:**
   ```bash
   python scripts/run_evals.py --condition with_skill --eval 86 --reps 5
   ```
   One review is a point estimate with no error bar. `--reps N` runs the eval N times in a fresh
   workspace each time, records every replicate, and writes a `replicate_summary` carrying the
   within-eval standard deviation — the noise floor `hillclimb.md` requires before round one.
   Step 3 prints it under `REPLICATE SPREAD`. A single-rep run deliberately reports no spread,
   because one sample cannot produce one.

5. **Run the suppression ablation:**
   ```bash
   python scripts/run_evals.py --condition nosuppress --eval 80 --reps 5
   python scripts/run_evals.py --condition with_skill  --eval 80 --reps 5
   ```
   Both arms, 5 replicates, fixtures 80–91. `--condition nosuppress` reconstructs the gate-free
   tree — verified to differ from HEAD by exactly `deliberate.md` and the lines naming it. Then
   re-run step 3 and read the `SUPPRESSION ABLATION` block.

6. **Run on an Individual Domain or Sub-Domain:**
   ```bash
   python scripts/validate_skill.py domains/correctness
   python scripts/validate_skill.py domains/correctness/security
   ```

## Eval Design Principles

The corpus is held to `auditandevolve/eval-design.md`, which adopts the four elements of a good
eval from the published *eval design and hillclimbing* guidance. Current status:

| # | Principle | Enforced by | Status |
|---|---|---|---|
| 1 | **Atomic & Binary** | Every assertion is one pass/fail condition; `validate_skill.py` rejects an eval with no `assertions` array | Enforced |
| 2 | **Blast-Radius Grounding** | Assertions name an expected severity and axis code, not a style preference | Enforced |
| 3 | **Restraint on Clean Code** | Controls (evals 5 & 25) assert 0 findings above Info | Enforced — **currently failing, 3/8 and 4/8** |
| 4 | **Actionable Fixes with Trade-offs** | Assertions require a concrete fix; Critical/Major must price scope and trade-off | Enforced |
| 5 | **Decoupled Architecture** | Each fixture targets distinct sub-domains, so leaf and sub-leaf evaluators are tested independently | Enforced |
| 6 | **Adversarial Sampling** | `eval-design.md` § Adversarial sampling — cases are included because a human judged them hard, not because today's model failed them | Documented, not independently audited |
| 7 | **Tasks Mirror Production** | Fixtures draw on published defect classes (CWE, OWASP, SRE practice) rather than model-failure sampling | Partial — no production-traffic sample exists to check the distribution against |
| 8 | **Passable Headroom** | `eval_diagnostics.py` blocks at ≥95% with-skill | **Enforced and tripping** — 93.3% aggregate, 80.8% verifiable |
| 9 | **Low Run-to-Run Variance** | `run_evals.py --reps N` records every replicate and a within-eval spread; `--determinism N` re-grades stored reviews for grader flip rate | **Mechanism shipped, corpus not yet re-run** — every committed verdict is still one sample |
| 10 | **Grader Validation** | Judge is a separate model, never the model under test; rubric written as checkable claims | Enforced in `run_evals.py` |
| 11 | **Plumbing ≠ Model Failure** | `run_evals.py` refuses to write a verdict when a tool errored or no review body was produced; `plumbing.json` records why | Enforced since `8615ae1` |
| 12 | **Overfitting Guards** | Random train/test split, never paste failure content into a patch, keep verdicts structurally out of the model's reach | Enforced in `hillclimb.md` |

### The first live measurements (2026-10-03)

The harness had never produced a clean run outside Windows, so every number above until this point
was unverified for a second reason than the ones listed. Four defects had to be fixed before a
single measurement was possible: a Windows-only executable resolver, a `--dir` flag that does not
exist, `cwd` alone being insufficient to pin the project (the reviewer landed in the real repository
and read `evals/evals.json` — the answer key), and a plumbing rule that discarded complete reviews
over a single misnamed tool.

Three measurements then landed before the free-tier quota closed:

| Eval | Fixture | with_skill | Baseline | What it shows |
|---|---|---|---|---|
| 82 | `suppress_lockless_accumulator` | **10/10** | rejected | The gate did **not** overrule a pattern the rubric installed |
| 83 | `suppress_ungated_memory` | **9/9** | rate-limited | Same, on the second FN-sibling fixture |
| 7 | `swallowed_error` | **7/10** | rejected | A non-ablation fixture with real headroom |

**Eval 82 is the load-bearing one.** Its planted defect is structurally identical to eval 6's — a
module-level mutable dict mutated without a lock, a pattern the corpus spends 8 assertions teaching
a reviewer to flag — and a suppression constraint covers the file. A gate that overruled it would
prove nothing, and 10/10 says it did not. That is the credibility test for `deliberate.md`, and it
passes on 2 of the 6 false-negative fixtures. **It is not a result yet**: one arm, one replicate, no
baseline, and the ablation it was built for was never reached.

Two things this session established that are not measurements:

- **The baseline arm is currently invalid.** The `without_skill` runs were *rejected* because the
  baseline read the skill — with no skill staged, it reached the real repository. Every delta in
  this file therefore rests on a baseline that may itself have been contaminated. Diagnosing why
  needs a model call, and the quota is closed.
- **A quota wall now stops the sweep** instead of producing one failure per remaining eval. The
  provider reports `provider.quota 429` as a stdout *event* with an empty stderr, so it surfaced as
  a bare exit code with no reason — a quota wall read as a broken harness, which cost a full
  sweep to diagnose. Both are fixed: the reason is extracted from the stream, and the sweep aborts
  with a count of what it did not attempt.

## Known gaps against the guidance

1. **No replicates.** Each eval runs once per arm, so run-to-run variance cannot be separated from
   grader variance, and the noise floor `hillclimb.md` requires before round one cannot be computed.
   This blocks hillclimbing, not merely reporting.
2. **Trigger rate is unrecorded.** `events.jsonl` is gitignored as regenerable bulk, so
   `eval_diagnostics.py` reports "no events.jsonl recorded" on a clean checkout. The metric the
   guidance calls *directly attributable* to the skill description cannot be audited from the repo.
3. **Most verdicts are unauditable.** `run_evals.py` writes `review.md` for every graded run, but
   the committed tree predates that for most evals. A verdict with no review body cannot be
   re-graded — which is exactly what the determinism check needs.
4. **No adversarial audit of the corpus.** No fresh agent has read the 102 fixtures cold to flag
   ambiguous cases, answerable-from-memory cases, or too-lenient assertions. Evals 92–99 are the
   only fixtures whose defects were independently demonstrated by execution; every other planted
   defect rests on its assertion strings alone, which is the weakest thing a fixture can rest on.
8. **The corpus is mostly unmeasured, and the free-tier quota is what stopped the sweep.** Of 99
   fixtures, 3 have a fresh verdict (evals 7, 82, 83) and 51 carry a verdict from before this
   session, of which 49 have no `eval_id` key and therefore attest to nothing. Evals 1–3, 6, 11–30 and
   79–91 were skipped as already-current against verdicts that cannot be tied to their assertions.
   **No baseline arm in this file is currently trustworthy** — see the live-measurements section
   above. `authoring a fixture is not measuring it`, and 99 measures the corpus, not the skill.
5. **Contamination was structurally possible.** `run_evals.py` ran every `with_skill` review with
   the skill root as cwd, so `evals/evals.json` — every `expected_output` and assertion string —
   sat two levels below the reviewer, and a recursive search could reach it. One run did, costing
   twelve evals. **Fixed:** staging is per-run, the workspace holds only the instruction surface
   and the eval's own files, and the runner refuses any read of the key, the recorded verdicts, a
   tree sweep, or an absolute path back into the real repository. The judge also runs in its own
   directory.
6. **The gate is unproven, and the blocker is now measured rather than assumed.** Evals 80–91 exist
   to falsify `project-tree/shared/deliberate.md`. They have not been run because a pre-flight showed
   the corpus **cannot return a valid verdict**: 32.5% of its 117 assertions are collectable by saying
   nothing, against a 40-point kill criterion. See § The suppression ablation above. The fix is
   corpus authoring, not more compute.
7. **No replicate runs yet.** `--reps` now exists and `eval_diagnostics.py` reports the
   within-eval spread it produces, but every committed verdict is still a single sample. Until
   the corpus is re-run with `--reps 3` or higher, run-to-run variance is unmeasured and the noise
   floor is still zero. This is the last blocker on hillclimbing, and it is a spend decision
   rather than a design one.
