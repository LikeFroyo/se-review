Reviewing your login fixture and run output.
Seen the vulnerable fixture — now gathering the eval context.
Scope confirmed — now loading the scoring rubric for the final report.
Rubric loaded — now verifying the flaws are actually exploitable.
# Security Review: `login_no_throttle.py`

`3 findings · C:3 M:0 m:0 i:0 · Domain Score: 25/100 (Grade F)`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/login_no_throttle.py` · Not examined: 0 — none
Paths: 3 open · Unmapped: 0 — all crossings classified

## Findings

### [CRITICAL] No login rate limit, lockout, or backoff — unlimited credential stuffing
- **Domain:** Security (S2)
- **Verified by:** RAN — imported `authenticate` and ran 1000 consecutive wrong-password attempts for `alice@corp.example` from a single `remote_ip`; all returned `False` with no delay, lockout, or error, and the correct password still signed in afterward.
- **Evidence:** `login_no_throttle.py:10` — `def authenticate(email: str, password: str, remote_ip: str)` takes `remote_ip` but never reads it; no counter, timestamp, lockout, or throttle anywhere in the 26-line file. Docstring at `:13-18` admits it.
- **Failure scenario:** Source: attacker-controlled `email`/`password` submitted at line rate from one IP → Boundary: `authenticate` entry, which applies no per-account or per-IP check → Sink: `ACCOUNTS[email]` comparison oracle at `:23`. Attacker runs password-spray / credential-stuffing dictionaries against known addresses until `:26` returns `True, "Signed in."`.
- **Fix:** Enforce per-account + per-IP attempt budget with exponential backoff and lockout, plus a CAPTCHA/bot signal at the handler boundary. Scope: boundary (handler contract + backing attempt store).
- **Trade-off:** Adds a stateful counter/store (memory or Redis) and latency on failed logins; lockout tuning risks user lockout abuse and support load.

### [CRITICAL] User enumeration via distinct failure messages
- **Domain:** Security (S2)
- **Verified by:** RAN — `authenticate('nobody@corp.example','x',…)` returns `"No account found for that email address."` while `authenticate('alice@corp.example','wrong',…)` returns `"Incorrect password. Please try again."`; the two strings reliably separate registered from unregistered addresses.
- **Evidence:** `login_no_throttle.py:20-24` — `if email not in ACCOUNTS: return False, "No account found…"` vs. `if password != …: return False, "Incorrect password…"`.
- **Failure scenario:** Source: attacker-chosen `email` → Boundary: login entry with no uniform response → Sink: message oracle distinguishing the branches. Attacker enumerates the address book, then focuses the unlimited-guessing path above (or phishing) on confirmed accounts.
- **Fix:** Return a single generic failure (`"Invalid email or password."`) with identical status/latency for both branches. Scope: local (the two return sites at `:21,24`).
- **Trade-off:** Slightly worse UX (legitimate users can't tell typo'd email from typo'd password); negligible latency/complexity cost.

### [CRITICAL] Passwords stored and compared in plaintext
- **Domain:** Security (S4)
- **Verified by:** DERIVED — trace: `ACCOUNTS` literal at `:4-7` holds `"correct-horse-battery-staple"` / `"hunter2-correct-horse"` in cleartext → `password != ACCOUNTS[email]` at `:23` compares cleartext. Any file, backup, log, or repo read of this module recovers every credential with no cracking step.
- **Evidence:** `login_no_throttle.py:4-7` — `ACCOUNTS: Dict[str, str] = {"alice@corp.example": "correct-horse-battery-staple", …}`; no hash, salt, KDF, or secrets manager.
- **Failure scenario:** Source: attacker with read access to source/backup/table dump → Boundary: none (no hashing boundary between stored secret and reader) → Sink: direct credential reuse against `:26` sign-in. One disclosure compromises all accounts silently.
- **Fix:** Store only a memory-hard hash (argon2id/bcrypt/scrypt with per-credential salt, work factor ≥ library-recommended minimum) and verify via constant-time compare; move secrets out of source. Scope: boundary (storage format + verification contract; requires migration of existing entries).
- **Trade-off:** Adds ~100–500 ms CPU per login for the KDF and a migration/reset for existing plaintext entries; negligible memory cost at this scale.

## Aligns well
- Minimal, readable handler with explicit typed signature — easy to gate once the above boundaries are added.