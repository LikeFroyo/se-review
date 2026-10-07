Reviewing the session fixation fixture — inspecting the run directory.
Found the fixation pattern — now gathering surrounding evaluation context.
I've mapped the authentication guidance to this code — now verifying the exploit before finalizing the review.
# Review: `evals/fixtures/session_fixation.py`

`1 finding · C:1 M:0 m:0 i:0 · Security: 75/100 (Grade C) · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/session_fixation.py` · Not examined: 0 — none
Paths: 1 open · Unmapped: 0 — no unclassified crossings
Unclassified: 0 findings fit no axis code
Gated by: `Critical finding` — any Critical caps grade at F

## Findings

### [CRITICAL] Session ID not regenerated at login (fixation)
- **Domain:** Security (S2)
- **Verified by:** RAN — `start_session(); login(sid, 'victim', True)` returns same `sid` with `authenticated: True`
- **Evidence:** `session_fixation.py:19-34` — `login()` mutates `SESSIONS[session_id]` in place and `return session_id`:
```python
session["user_id"] = username
session["authenticated"] = True
return session_id
```
- **Failure scenario:** Source: attacker-planted `session_id` (prefetched link, shared machine, XSS read) → Boundary: `login()` privilege escalation, which should mint a new ID → Sink: `SESSIONS[sid]` flipped to authenticated. Victim logs in; attacker's copy of the pre-auth ID is now an authenticated session. No hijack needed.
- **Fix:** Module scope, in `login()`: pop old entry, mint new ID, copy state. Invalidate the pre-auth ID server-side.
```python
SESSIONS.pop(session_id, None)
new_id = secrets.token_urlsafe(32)
SESSIONS[new_id] = {"user_id": username, "authenticated": True}
return new_id
```
- **Trade-off:** Cost is one dict delete + one CSPRNG mint per login (negligible). Concurrent anonymous requests racing login lose old-ID state — correct, that state was unauthenticated.

## Aligns well
- `session_fixation.py:13`: IDs via `secrets.token_urlsafe(32)` (~256-bit CSPRNG) — no predictable-material issue (S2).
- `session_fixation.py:37-39`: `end_session()` destroys server-side via `SESSIONS.pop`, not client-only clear.