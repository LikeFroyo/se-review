Reviewing your health and shutdown eval files.
Found the fixture with flagged defects — now mapping the surrounding eval context.
I've charted the liveness coupling, instant-exit handler, and grace-period mismatch — now pulling the scoring rubric to finalize the report.
# Review: `evals/fixtures/health_and_shutdown.py`

`5 findings · C:3 M:1 m:1 i:0 · Mean 56/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/health_and_shutdown.py` · Not examined: 0 — none
Unclassified: 0 findings fit no axis code
Domain Scores: Operations: 25/100 · Correctness: 87/100
Gated by: `Critical finding` — any Critical caps grade at F; weakest domain also F.

## Findings

### [CRITICAL] Liveness coupled to database
- **Domain:** Operations (C3)
- **Verified by:** DERIVED — chain: `liveness():27-30` opens `psycopg2.connect` + `SELECT 1` on every `GET /healthz` → DB blip returns `{"status":"unhealthy"}` → platform restarts all instances → fresh connects storm recovering DB.
- **Evidence:** `health_and_shutdown.py:16-33` — `def liveness()` with `conn = psycopg2.connect(DB_DSN...); cur.execute("SELECT 1")`, `except Exception: return {"status":"unhealthy"...}`
- **Failure scenario:** Brief DB latency spike makes every replica fail liveness simultaneously; orchestrator kills healthy processes, restart thundering herd prevents DB recovery — total outage from a transient dependency blip.
- **Fix:** Scope: module. Make liveness dependency-free (process-alive check only, return healthy if event loop can serve); move `SELECT 1` to `readiness()`.
- **Trade-off:** Cost: degraded DB no longer removes pods via liveness; readiness must reliably shed traffic instead, plus alerting on readiness-fail to avoid silent degraded service.

### [CRITICAL] SIGTERM exits immediately without draining
- **Domain:** Operations (C3)
- **Verified by:** DERIVED — chain: `signal.signal(SIGTERM, on_sigterm):48` → `on_sigterm:43-45` calls `os._exit(0)` → in-flight `monthly_report(~40s):57-62` and `process_queue→process_batch:65-67` killed mid-work; `TERMINATING` never set so `readiness():36-40` never withdraws.
- **Evidence:** `health_and_shutdown.py:43-48` — `def on_sigterm(signum, frame): os._exit(0)` installed at import.
- **Failure scenario:** Every deploy/scale-down kills live `POST /reports/monthly` and queue messages in flight; completed warehouse work lost, queue messages half-written or redelivered without ack coordination.
- **Fix:** Scope: module. In handler set `TERMINATING`, stop intake/listener, await in-flight reports/queue acks up to grace period, then exit; wire `readiness()` to already-present `TERMINATING.is_set()` check.
- **Trade-off:** Cost: shutdown path gains complexity and must enforce a hard deadline to avoid hanging termination; in-flight tracking (`REPORT_IN_FLIGHT`) must become thread-safe and awaited.

### [CRITICAL] Grace period shorter than longest work
- **Domain:** Operations (C3)
- **Verified by:** DERIVED — chain: comment `terminationGracePeriodSeconds: 15:50-52` vs `monthly_report(~40s)` + `requests.get(timeout=120):57-62` → platform SIGKILLs at 15s, legitimate 40s work can never complete.
- **Evidence:** `health_and_shutdown.py:50-62` — `# terminationGracePeriodSeconds: 15` / `# Longest accepted request: POST /reports/monthly (runs ~40s)`
- **Failure scenario:** Every monthly report deployed/rolled during generation is cut off at 15s; guaranteed user-visible failure for the longest, highest-value endpoint.
- **Fix:** Scope: boundary. Raise `terminationGracePeriodSeconds` above worst-case (e.g. 60-90s with buffer) or make report asynchronous (enqueue + poll) so request need not outlive pod.
- **Trade-off:** Cost: longer draining holds capacity during rollouts (slower deploys, higher cost); async alternative adds queue/API complexity.

### [MAJOR] DB connection leaked on health-check query failure
- **Domain:** Correctness (A3)
- **Verified by:** DERIVED — chain: `conn = connect:27` → `cur.execute:29` raises → `conn.close():30` skipped, no `finally`/`with` → descriptor leak exactly during DB blip when liveness is called most.
- **Evidence:** `health_and_shutdown.py:27-30` — `conn = psycopg2.connect(...); with conn.cursor() as cur: cur.execute(...); conn.close()`
- **Failure scenario:** During DB instability each probe leaks a connection server-side until exhaustion, amplifying the liveness restart storm above.
- **Fix:** Scope: local. Wrap in `try/finally: conn.close()` or `with psycopg2.connect(...) as conn:`.
- **Trade-off:** Adds one nesting level; negligible latency cost.

### [MINOR] Import-time hard dependency on environment
- **Domain:** Correctness (A1)
- **Verified by:** READ
- **Evidence:** `health_and_shutdown.py:12` — `DB_DSN = os.environ["DATABASE_URL"]`
- **Fix:** Use `os.getenv` with explicit startup validation/fail-fast message so import/tests don't raise bare `KeyError`.

## Aligns well
- `readiness()` intent checks `TERMINATING.is_set()` to return `draining` (C3) — correct withdrawal pattern, currently dead only because handler never sets the event.