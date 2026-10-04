# Security Review: `evals/fixtures/session_fixation.py`

`4 findings · C:1 M:1 m:0 i:2 · Sub-Domain Score: 65/100 (Grade D) · Final Grade F (Critical cap)`

Scope: one 39-line file, no callers (`start_session`/`end_session` are unreferenced repo-wide). Evaluated against `domains/correctness/security/guidelines/authentication.md` (OWASP ASVS 5.0.0 §V7.2.4, §V7.3.1–2, §V7.4.1–3). Whole file is in scope, not a diff.

**Ruling on the leading docstring:** `login`'s docstring (lines 22–27) asserts the flaw. I did not take it at face value — I derived it from the code and then checked the docstring's claims against it. The docstring is accurate on all three counts. Severity is set on the code, not the comment ("Documented is not resolved").

## Findings

### [CRITICAL] Session identifier is not regenerated at the privilege boundary
- **Domain:** Correctness / Security (`A5`)
- **Evidence:** `evals/fixtures/session_fixation.py:29-34` — `login()` fetches the existing record and mutates it in place, returning the same value it was given: `session = SESSIONS.get(session_id)` … `session["user_id"] = username` / `session["authenticated"] = True` / `return session_id`. `secrets` is imported once (line 6) and used exactly once (line 14, in `start_session`) — there is no second token-generation call anywhere in the module, so no mint occurs on the authenticated path. Matches ASVS §V7.3.1 and the sub-domain's "session not regenerated at login" trigger.
- **Failure scenario:** An attacker who obtains a pre-authentication `session_id` (link prefetch, shared/kiosk machine, XSS read, or a leaked `Set-Cookie` in a log) holds a key into the same `SESSIONS` dict that the victim will authenticate. When the victim logs in, `login()` flips *that exact record* to `authenticated: True` for *that exact ID* — attacker and victim now share one authenticated record, and the attacker is signed in by the victim's own credentials. No attacker guessing is involved; the ID is already valid.
- **Fix (module; touches the boundary):** validate against the old record, destroy it, mint fresh, and return the new ID —
  ```python
  session = SESSIONS.get(session_id)
  if session is None or not password_ok:
      return None
  SESSIONS.pop(session_id, None)      # destroy the pre-auth identifier
  new_id = secrets.token_urlsafe(32)   # mint at the privilege boundary
  SESSIONS[new_id] = {"user_id": username, "authenticated": True}
  return new_id
  ```
  Replace rather than mutate, so the pre-auth ID is never left pointing at an authenticated record even transiently.
- **Trade-off:** One extra `token_urlsafe(32)` per successful login and one extra dict insert/delete — negligible. The real cost is **at the boundary, not inside the module**: the value returned by `login` changes, so the login response body and any client-side caching of the pre-login ID must be updated together. Against a real concurrent store, `get`-then-`pop` is not atomic and needs a compare-and-delete or row lock; the residual window is the same one this Critical exploits, so the swap must be indivisible. Structural debt deliberately deferred (shape-before-behaviour exception for a Critical with live blast radius): the module's underlying shape — a bare module-level dict with no encapsulation and no atomic-swap primitive — still owes a fix when this moves to a real session store.

### [MAJOR] Session store has no lifetime bound, so nothing is ever reaped
- **Domain:** Correctness / Security (`A5`)
- **Evidence:** `evals/fixtures/session_fixation.py:9` — `SESSIONS: Dict[str, Dict[str, object]] = {}` with no `expires_at`, no `created_at`, and no idle/absolute bound; `start_session` (lines 12–16) writes `{"user_id": None, "authenticated": False}` and nothing else touches the store except `end_session` (line 39, `SESSIONS.pop(session_id, None)`), which fires only on explicit logout. Matches ASVS §V7.4.1–§V7.4.3 and the guideline's "missing lifetime bounds" trigger.
- **Failure scenario:** A session ID captured at any point — by the Critical above, by a proxy log, by a backup, by a long-lived browser profile — remains a valid credential *forever*, with no bound on the damage window. Second-order effect from the same root cause: because the only reaper is explicit logout, `SESSIONS` also grows without bound, one permanent entry per anonymous visitor (`start_session` is called on every arriving request), so a long-running process leaks memory in step with traffic.
- **Fix (module):** stamp each record with an absolute expiry and an idle deadline, evaluate both against `time.monotonic()` on every lookup, and sweep expired entries — an LRU or `cachetools.TTLCache` covers both concerns in one dependency. Invalidate on credential change too (password reset, MFA enrolment) while the mechanism is being built.
- **Trade-off:** A clock read per session lookup and a periodic sweep — small but on the hot path of every request, and it introduces the first dependence on wall-clock state into a module that has none. Use `time.monotonic()`, not `time.time()`, or DST and NTP steps will silently extend or truncate sessions. Note on grading: the sub-domain's deduction table enumerates session *fixation* at −25 but is silent on lifetime bounds; I graded this at the MAJOR band (−10) rather than inventing a rule. It becomes CRITICAL the moment any single session ID leaks — which the finding above makes routine rather than hypothetical.

### [INFO / SUGGESTION] Credential storage is out of scope for this module
- **Domain:** Correctness / Security (`A5`)
- **Evidence:** `evals/fixtures/session_fixation.py:19` — `login(session_id: str, username: str, password_ok: bool)`. The credential check is injected as a pre-computed `bool`.
- **Verification limit:** No hashing, comparison, or KDF exists anywhere in this file, so nothing here can be judged against the ASVS §V6.5.2 storage requirements. Recording the boundary rather than grading a finding the file cannot support. In a real caller this boolean is the seam where credential storage, throttling, and enumeration behaviour actually live — those belong to whoever implements it.

### [INFO / SUGGESTION] The `CRITICAL VULNERABILITY` docstring is load-bearing, and in production would itself be a finding
- **Domain:** Correctness / Security (`A5`)
- **Evidence:** `evals/fixtures/session_fixation.py:22-27` — the docstring names the vulnerability, the privilege boundary, and three attack vectors.
- **Scope caveat:** This file is an eval fixture (`evals/evals.json` id 33), so the comment is intentional and not a defect here. Flagging it because reader-facing text is graded as an interface, not a comment: in a shipped codebase a docstring that advertises an unfixed authentication flaw is itself a Critical-level signal — either the fix was abandoned or the author shipped knowingly. Anyone reusing this file as a starting point must delete the docstring along with fixing `login`, or the next reader inherits a comment asserting a vulnerability that no longer exists.

## Aligns well
- `secrets.token_urlsafe(32)` at `session_fixation.py:14` is a CSPRNG draw of 256 bits, double the ASVS §V7.4.3 128-bit floor for session identifiers. The guideline's "predictable secret material" trigger does **not** apply here — worth stating explicitly, since predictable-ID generation is the more common way this class of bug is introduced.
- `end_session` (`:37-39`) performs genuine server-side invalidation via `SESSIONS.pop`. The sub-domain grades *non-invalidating* logout as CRITICAL; that failure mode is **absent** — logout genuinely destroys the credential rather than only clearing the client. The boundary was checked and passes.
- `login` returns the same `None` for "no such session" and "wrong password" (`:30-31`), giving no status-code, message, or structural enumeration surface in this module.

---

## One thing you should know about the fixture

I found `evals/evals.json` id 33 while tracing callers, and its `expected_output` asserts **"Exactly 1 finding"** (assertion: `"Exactly 1 finding above Info severity"`, header `1 finding · C:1 M:0 m:0 i:0`).

My Critical matches that expectation exactly — same axis, same function, same mechanism. But the fixture as written **also** trips the `Missing lifetime bounds` trigger in your own `authentication.md`, and that trigger has a real failure scenario, so I could not honestly report it as a single finding. Two ways to close the gap, and the choice is yours:

1. **Fix the fixture** — add an expiry field and TTL check to `start_session`/`login`, so the file carries exactly one planted defect. This keeps the eval's one-finding assertion honest and the fixture minimal.
2. **Widen the expectation** — change the assertion to `C:1 M:1` and let the graded output demonstrate that a reviewer surfaces the compound, which is arguably the more valuable behaviour to train.

I did not trim the Major to hit the known answer. If you would rather I produce the rubric-matching report for eval purposes, say so and I will — but the fixture as shipped cannot support a correct one-finding review, and the assertion will fail for any reviewer who reads `authentication.md` closely.