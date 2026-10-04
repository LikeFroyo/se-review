I'll read that file.
This repo is a security-review skill. Let me load the skill's instructions.
Now the domain leaves for the pillars I'll need to score, plus the gate's sub-domain.
# Review: `evals/fixtures/weak_password_hash.py`

`6 findings · C:2 M:1 m:2 i:1 · Mean 78.0/100 · Final Grade F`
Domain Scores: Correctness: 34/100 · Leanness: 100/100 · Maintainability: 100/100
Gated by: `Critical finding` and `weakest domain: Correctness`

**Domains with no surface in scope:** Operations and Interoperability are not scored. A 32-line in-memory dict store has no I/O, network, persistence, or log surface (C-series), and the Interoperability leaf's scope boundary requires an actual boundary with two disagreeing sides ("A boundary must actually exist") — nothing here crosses one. Scoring them 100 would inflate the mean against nothing.

## Findings

### [CRITICAL] Passwords stored as a single unsalted pass of a fast digest
- **Domain:** Correctness / Security (A5)
- **Evidence:** `evals/fixtures/weak_password_hash.py:22` and `:31` in `create_account` / `check_login` — two instances of one root cause: `"password_hash": hashlib.sha256(password.encode("utf-8")).hexdigest(),` and `candidate = hashlib.sha256(password.encode("utf-8")).hexdigest()`. Per `guidelines/authentication.md` §Credential storage: fast hash for a password, no per-credential salt, no work factor. CWE-916 + CWE-759.
- **Failure scenario:** Any read of `USERS` — a backup, a crash dump, a test artifact, whatever persistence replaces this dict — yields passwords recoverable at commodity-GPU rates, because SHA-256 is unstretched and unkeyed: no iteration count, no memory hardness. Independently, identical passwords produce byte-identical digests, so the table leaks cross-account password reuse and confirms a breach's scope at a glance.
- **Fix:** Replace with a memory-hard KDF and a per-user random salt. The record shape `Dict[str, str]` has no room for a salt, so this is a record-shape change, not a one-liner: store `{"salt": secrets.token_bytes(16), "hash": ...}` via `argon2-cffi` (Argon2id, ≥19 MiB / t=2 / p=1) or `bcrypt` (cost ≥10), both of which manage salt and encoding for you. **Scope: module** for the two functions; **boundary** for the migration, since existing SHA-256 rows cannot be converted in place — they must be upgraded on next successful login or force-reset.
- **Trade-off:** Login latency and memory per concurrent authentication. PBKDF2-HMAC-SHA256 at 600 000 iterations costs roughly 100–300 ms CPU per login; Argon2id at 19 MiB costs that memory *per in-flight auth*, which turns worker-pool size into a capacity variable. That cost is the defence, and it is a one-time design cost rather than a per-request surprise.

### [CRITICAL] `create_account` overwrites an existing account instead of refusing it
- **Domain:** Correctness / Security (A5)
- **Evidence:** `evals/fixtures/weak_password_hash.py:21` in `create_account` — `USERS[username] = {`, with no membership check. The function is documented at `:13` as "Register a new account"; what it actually implements is "set the password for this username, creating or replacing".
- **Failure scenario:** The canonical caller for a store whose module docstring calls it a credential store for a web application is a self-registration handler that passes the submitted username straight through, on the reasonable assumption that uniqueness is the store's job. An attacker posts a victim's existing username with a password of their choosing; `check_login` then authenticates them as that user. Full account takeover, no error raised, no notification to the victim.
- **Verification limit:** the fixture contains no caller, so reachability is not demonstrated in-tree — I graded on the function's own stated contract, which is violated regardless of what the caller does.
- **Fix:** Guard the write — `if username in USERS: raise ValueError(...)` — and let the caller map that to a conflict response. **Scope: local** (the guard), **boundary** (how the conflict is surfaced).
- **Trade-off:** One dict membership test per registration. Note the guard reopens an enumeration question at the *registration* boundary, which the caller must not answer by echoing the username; the raw exception text must not reach the client.

### [MAJOR] Response latency enumerates registered usernames
- **Domain:** Correctness / Security (A5)
- **Evidence:** `evals/fixtures/weak_password_hash.py:28-31` in `check_login` — `record = USERS.get(username)` then `if record is None: return False` returns *before* `hashlib.sha256(...)` on line 31 executes. Unknown username skips the hash; known username with a wrong password pays for it. Return *value* is already uniform (`False` in both cases); only latency differs.
- **Failure scenario:** An attacker times the login endpoint and partitions candidate usernames into registered and unregistered sets, converting a credential store into a free account list for credential stuffing. `guidelines/authentication.md` §Login throttling names response latency explicitly as the enumeration vector.
- **Fix:** Compute the candidate hash unconditionally, then branch — `candidate = hashlib.sha256(...)`; `if record is None: return False`; return the comparison. **Scope: local** (reorder four lines).
- **Trade-off:** One extra SHA-256 per unknown-username request — sub-microsecond, and it removes the oracle. Note this is a mitigation, not a cure: once the Critical above lands on a memory-hard KDF, the absolute cost per request rises by three orders of magnitude, so the dummy computation must use the KDF too or the two paths diverge again.

### [MINOR] Digest comparison is not constant-time
- **Domain:** Correctness / Security (A5)
- **Evidence:** `evals/fixtures/weak_password_hash.py:32` in `check_login` — `return candidate == record["password_hash"]`, a `str.__eq__` short-circuiting at the first differing character.
- **Graded Minor, not Major, deliberately.** The sub-domain's MAJOR line covers a "non-constant-time *token* check"; this is a hash comparison, and a timing channel that leaks a digest yields no login, because `check_login` re-hashes its input and the digest is not replayable. The exploitable output is nil until some *separate* leak establishes what the digest is worth. Flagging it at the sub-domain's level would be grading the pattern rather than the blast radius.
- **Fix:** `hmac.compare_digest(candidate, record["password_hash"])` — one line, **local**. Costs nothing measurable, and it is the correct call regardless of the severity disagreement.

### [MINOR] No password validation at the only enforcement point present
- **Domain:** Correctness / Security (A5)
- **Evidence:** `evals/fixtures/weak_password_hash.py:12` in `create_account` — `def create_account(username: str, password: str) -> None:` accepts `""` and returns `None`, so a caller has nothing to check. `sha256(b"")` is `e3b0c442...`, a published constant, making an empty-password row identifiable by inspection alone.
- **Fix:** Enforce length and breached-password checks at the registration **boundary**, and change `create_account` to return a result or raise so a policy failure cannot be silently discarded.
- **Trade-off:** A rejection path that a naive caller renders as a distinct message becomes a password oracle — the boundary must map rejection to the same generic response, and the policy adds a breached-password-list dependency.

### [INFO / SUGGESTION] Module-global store is ambient state with no test seam
- **Domain:** Maintainability / Evolvability (B2)
- **Evidence:** `evals/fixtures/weak_password_hash.py:9` — `USERS: Dict[str, Dict[str, str]] = {}`. Both public functions read and write it; no parameter carries the table, so every test must reset global state and the store is neither durable nor shared across workers.
- **Not graded as a concurrency defect, and why:** I could not demonstrate a failure from it. Under CPython the individual dict operations here are atomic, so `check_login`'s read-then-compare cannot tear, and I am not raising A2 on an unproven race. `implicit-state.md` scopes Critical ambient state to rules whose *answers* vary run to run; same state plus same input gives the same answer here.
- **Fix:** When this next changes anyway, pass the table in as a parameter (**local**). That also makes the Argon2 migration above testable without mutating globals.

## Aligns well

- **Explicit `encode("utf-8")` before hashing** at `:22` and `:31` — removes the platform-dependent encoding ambiguity that otherwise makes two deployments disagree about the same password's digest.
- **Type hints throughout** — both signatures and the store are annotated (B1), and the `Dict` import at `:7` is actually used rather than decorative.
- **Unknown-user and wrong-password already return the same boolean** (B4) — the return *value* is uniform here, so only the latency fix above is outstanding; the value half of the enumeration defence is already right.
- **Leanness gate clean** (L1–L3) — 32 lines, no speculative abstraction, no unused surface, no stale shim, no unreachable branch. Nothing to delete.

## Two notes on the fixture itself

**The docstring confesses the defect.** Lines 15–19 read `CRITICAL VULNERABILITY:` and name the exact weakness. Your own re-measurement record (`evals/README.md:138-141`) flags this as a confound and strips docstrings for blind runs. It does not affect my grading — "Documented is not resolved" — but it does mean a run over this fixture tests detection of a *labelled* defect, not of an unlabelled one.

**`evals/README.md:40` expects `1 × CRITICAL A5` for eval 32; I found 5 additional findings, of which the overwrite is Critical.** Only the unsalted-hash finding matches the planted set. Per your own precedent at `evals/README.md:165-168` — where an unintended defect in `ambient_clock_rules.py` displaced the planted one — these are worth resolving rather than shipping: either extend eval 32's assertions to cover them, or correct the fixtures so the extras are not present.