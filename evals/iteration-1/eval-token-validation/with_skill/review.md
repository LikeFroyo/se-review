I'll read the file first.
Let me check how this fixture is used before reviewing the code itself.
This repo *is* a code-review skill, and the target is one of its eval fixtures. Let me check the fixture's role and the review rubric.
Found the matching guideline. Reading the security domain leafs and the eval's declared intent.
Now let me load the shared rubric files so my report conforms to this skill's own format and axis codes.
I read the file, the matching guideline (`domains/correctness/security/guidelines/token-validation.md`), the axis registry, and the eval's own grading record. Review below, in this repo's report format.

# Security Review: `evals/fixtures/token_validation.py`

`1 finding · C:1 M:0 m:0 i:0 · Domain Score: 75/100 (Grade C) · Final Grade: F`

**Scope ruling:** this is a deliberately vulnerable eval fixture (`evals/iteration-1/eval-token-validation/grading.json` asserts exactly this finding). The Critical is **intentional and must not be fixed** — the review below confirms the planted defect is correctly localized and graded. Secondary observations are reported as Info and explicitly not actioned.

## Findings

### [CRITICAL] Token is decoded with signature verification disabled and its claims trusted as identity
- **Domain:** Correctness / Security (A5)
- **Evidence:** `token_validation.py:AuthGateway.authenticate:24-26` — `jwt.decode(token, JWT_SECRET, options={"verify_signature": False})`, then `{"user_id": claims["sub"], "role": claims.get("role", "viewer")}`
- **Failure scenario:** With `verify_signature=False`, PyJWT `setdefault`s every other verification flag to `False`, so `exp`, `nbf`, `iat`, and `aud` are skipped too — one root cause, not four. Any unauthenticated caller sends a self-minted `{"sub":"attacker","role":"admin"}` and `is_permitted` (line 30-31) grants `delete_workspace` and `billing_refund`. Full auth bypass; no secret knowledge required, so `JWT_SECRET` is irrelevant to the attack.
- **Note:** the docstring at lines 17-22 says `aud`/`exp` "are also never inspected." That claim is correct — verified against PyJWT's `setdefault` behaviour, not assumed. Per `severity-and-rules.md:98`, documenting the flaw does not downgrade it.
- **Fix (module scope):** pin `algorithms=["RS256"]` at the call site with the issuer public key, drop the `verify_signature` override, and validate `exp`/`iss`/`aud` against expected values. Per `severity-and-rules.md:73`, ship the behaviour change now; structural follow-up is not required for a fixture.
- **Trade-off:** asymmetric verification adds ~1-2ms CPU per request (one public-key op vs. one HMAC) and requires a JWKS fetch with caching plus a key-rotation path — a real operational addition for a service that previously needed neither.

## Info / Suggestion — not actioned (fixture realism)

- **(A5)** `is_permitted:31` — `required in ALLOWED_ROLES` is **vacuously true**: `required` is only ever `"admin"` or `"viewer"`, both in the tuple. The predicate tests the *required* role, not `principal["role"]`, so the allowlist constrains nothing and cannot limit an attacker-supplied `role` claim. Inert today because `principal["role"] == required` subsumes it. Left as-is: it is exactly the kind of realistic-looking defense-in-depth a token-bypass fixture should contain.
- **(A1)** `is_permitted:30` — `"editor"` is in `ALLOWED_ROLES` but `required` never evaluates to it, so an editor is denied *every* action (neither `"editor" == "viewer"` nor `"editor" == "admin"`). The advertised role is ungrantable.
- **(A1)** `authenticate:26` — `claims["sub"]` is unguarded; a forged token omitting `sub` raises `KeyError` → 500 rather than 401. Fails loud, not open, so not security-relevant.
- **(L2)** `authenticate:25` — `JWT_SECRET` is passed as the `key` argument to a call that ignores it entirely. Dead parameter.
- **(A5)** `authenticate:24` — `removeprefix("Bearer ")` neither requires the prefix nor checks its case, so a bare token is accepted verbatim. Moot while verification is off; must be handled as part of the fix above.
- **(A5)** `authenticate:9` — `JWT_SECRET = "svc-signing-key-do-not-share"` would be a hardcoded-plaintext-secret Critical under `security/sub-leaf.md:21` if this were production code. Graded Info here because it is a self-describing placeholder and is inert. Worth noting the fixture teaches the wrong shape: the *fixed* version should not have this constant at all, since the correct design verifies against an issuer public key fetched per environment.

## Aligns well
- The planted defect is minimal and precisely localized to one call site (`token_validation.py:25`), which is what makes it a usable eval input — a reviewer has to actually read the options dict rather than pattern-match the filename.
- The docstring's technical claim about PyJWT claim validation is accurate, so the fixture doubles as a regression reference for the guideline it exercises.

---

## Two things worth raising about the eval itself

**1. The recorded grade violates the skill's own cap rule.** `grading.json:7` records `Domain Score: 75/100 (Grade C)` on a run containing a Critical. `shared/severity-and-rules.md:37` and `:42` are explicit: *any Critical caps the grade at F*, and in a single-domain run only that first cap can bind. The domain-score arithmetic (75) and the **final** grade (F) are two different numbers, and the recorded header appears to conflate them. Every Critical-bearing eval in `iteration-1` is likely mis-rendered the same way — worth checking before the scores are used to compare skill vs. no-skill.

**2. Assertions #1 and #5 pull in opposite directions.** Assertion1 requires *exactly 1 finding above Info*; assertion 5 requires identifying missing `aud`/`exp` validation. Because `verify_signature=False` suppresses those checks transitively, honouring both is only possible if you collapse them into the one root cause — which the recorded evidence does (`grading.json:10`). That is correct dedup per `severity-and-rules.md:95`, but it means the fixture cannot distinguish a reviewer who found the `exp` gap from one who found only the signature gap. If you want that discrimination, `exp`/`aud` need a second, independently-planted defect in a different fixture.