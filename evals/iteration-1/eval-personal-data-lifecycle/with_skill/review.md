Reviewing your lifecycle fixture — reading code and eval directory.
Fixture shows intentional lifecycle failures — checking eval harness for full context.
Confirmed single-fixture scope — loading review rubric to grade it.
Core durability and erasure patterns are clear — verifying remaining domains before scoring.
# Review: `evals/fixtures/personal_data_lifecycle.py`

`9 findings · C:4 M:3 m:2 i:1 · Mean 94/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/personal_data_lifecycle.py` · Not examined: 0 — none
Paths: 0 resolved open | 1 · Unmapped: 1 — `delete_customer`/`support_notes` entry point and auth boundary not mapped
Unclassified: 0 findings fit no axis code
Domain Scores: Operations: 0/100 · Correctness: 90/100 · Interoperability: 97/100 · Leanness: 90/100 · Maintainability: 87/100 · Security: 100/100
Gated by: `Critical finding` — any Critical caps grade at F; weakest domain Operations 0/F also gates

## Findings

### [CRITICAL] Snapshot shares primary failure domain, no PITR, unmeetable RPO
- **Domain:** Operations (C7)
- **Verified by:** DERIVED — `SNAPSHOT_BUCKET`/`REGION` constants → `snapshot_now` `put_object` → no cross-region copy, no PITR branch; `RPO_TARGET_MINUTES=0` vs 7-day nightly chain; `LAST_RESTORE_TEST="never"`
- **Evidence:** `personal_data_lifecycle.py:10-15` — `SNAPSHOT_BUCKET = "acme-orders-snapshots"`, `REGION = "eu-west-1"`, `SNAPSHOT_RETENTION_DAYS = 7`, `LAST_RESTORE_TEST = "never"`, `RPO_TARGET_MINUTES = 0`; `personal_data_lifecycle.py:32-37` — `boto3.client("s3", region_name=REGION)` + `put_object(Bucket=SNAPSHOT_BUCKET, ...)`
- **Failure scenario:** Region/account event destroys primary and every snapshot; last 24h of writes unrecoverable (nightly only); RPO 0 never satisfiable; corruption discovered after 7 days leaves no good copy.
- **Fix:** Boundary scope: separate backup account + cross-region replicated bucket with versioning/PITR, RPO/RTO restated to measured values, retention ≥ detection window.
- **Trade-off:** Cross-account replication + versioned storage adds latency on snapshot path and storage cost; restores must assume cross-account credentials.

### [CRITICAL] Restore never rehearsed, destroys live DB first
- **Domain:** Operations (C7)
- **Verified by:** DERIVED — `restore` drops live DB → creates empty DB → fetches snapshot from production bucket; `LAST_RESTORE_TEST="never"` confirms never run
- **Evidence:** `personal_data_lifecycle.py:41-54` — `_conn.execute("DROP DATABASE orders")`, `_conn.execute("CREATE DATABASE orders")`, `_conn.restore(client.get_object(Bucket=SNAPSHOT_BUCKET, Key=snapshot_key)["Body"])`
- **Failure scenario:** First execution happens during incident, against production, with production credentials; corrupt/missing key leaves empty DB; restore time vs RTO unknown.
- **Fix:** Module scope: fetch+verify snapshot to staging first, pre-step checkpoint, rehearsed runbook with timed restore to isolated host; never `DROP` before successful fetch.
- **Trade-off:** Staging restore doubles restore-time I/O and requires isolated restore host/credentials outside the failure domain.

### [CRITICAL] Retention schedule unenforced
- **Domain:** Operations (C8)
- **Verified by:** READ
- **Evidence:** `personal_data_lifecycle.py:57-66` — `retention_policy()` returns `{"orders": "90 days", "backups": "7 days", "support_tickets": "24 months"}`; no job reads it, no S3 lifecycle rule, no expiry column referenced anywhere in file
- **Failure scenario:** Personal data accumulates indefinitely; stated 90-day/24-month limits are false in a subject request or audit; regulatory breach on retention.
- **Fix:** Boundary scope: S3 lifecycle rules + DB expiry/`DELETE` jobs + legal-hold review that actually invoke this policy; audit log of deletions.
- **Trade-off:** Scheduled deletes add write load and need idempotent batching plus hold-bypass review process.

### [CRITICAL] Erasure leaves backups, DLQ, support notes intact
- **Domain:** Operations (C8)
- **Verified by:** DERIVED — `delete_customer` touches primary + index/cache/warehouse only → no backup scrub, no queue/DLQ purge, no `support_notes` delete; next disaster restore resurrects the “deleted” person
- **Evidence:** `personal_data_lifecycle.py:69-84` — `DELETE FROM customers WHERE id = %s` + index/cache/warehouse deletes, returns `{"deleted": True}`; no reference to `SNAPSHOT_BUCKET`, queues, or `support_notes(customer_id)` table read at `personal_data_lifecycle.py:93-95`
- **Failure scenario:** DSAR answered “done” while copies survive in 7 days of snapshots, dead-letter history, and support-notes text; restore re-identifies the subject.
- **Fix:** Boundary scope: erasure orchestrator covering primary, indexes, cache, warehouse, queues/DLQ, support tables, plus backup expiry/crypto-shredding policy and tombstone for restores.
- **Trade-off:** Cross-system fan-out adds latency/complexity; backup crypto-shredding requires per-customer keys; restores need tombstone reconciliation.

### [MAJOR] Free-text support notes store unbounded PII
- **Domain:** Operations (C8)
- **Verified by:** READ
- **Evidence:** `personal_data_lifecycle.py:87-96` — `support_notes()` selects `notes` verbatim; docstring admits full addresses, DOBs, card digits with no classification or length bound
- **Failure scenario:** Over-collection + whole-record read by any support caller; breach/DSAR scope explodes; card data in plaintext notes widens PCI exposure.
- **Fix:** Boundary scope: classify/redact at write, length-bound + PII detectors, separate sensitive fields with encryption and scoped access.
- **Trade-off:** Redaction/classification adds write-path latency and false-positive triage; migration must scrub history.

### [MAJOR] Delete path crashes on happy path, still reports success
- **Domain:** Correctness (A1)
- **Verified by:** DERIVED — `SEARCH_INDEX`/`CACHE`/`WAREHOUSE` are `str` constants (`personal_data_lifecycle.py:17-19`) → `SEARCH_INDEX.delete_by_query`, `CACHE.pop(k,None)`, `WAREHOUSE.execute` raise `AttributeError`; `_conn.execute(...).fetchone()` pattern in `support_notes` also misuses `psycopg2` API; success dict is unconditional
- **Evidence:** `personal_data_lifecycle.py:17-19` vs `personal_data_lifecycle.py:80-84`; `personal_data_lifecycle.py:93-95` — `.execute(...).fetchone()`
- **Failure scenario:** Every `delete_customer` raises after primary `DELETE`, leaving partial erasure; callers catching loosely believe `{"deleted": True}`.
- **Fix:** Module scope: inject real index/cache/warehouse clients behind seam, handle partial failure transactionally, return per-store receipt instead of unconditional `True`.
- **Trade-off:** New clients + error aggregation add complexity and make partial-erasure states explicit to callers.

### [MAJOR] Hallucinated DB/storage APIs
- **Domain:** Leanness (L6)
- **Verified by:** READ
- **Evidence:** `personal_data_lifecycle.py:36` — `_conn.dump()`; `personal_data_lifecycle.py:54` — `_conn.restore(...)`; `personal_data_lifecycle.py:52-53` — `_conn.execute("DROP/CREATE DATABASE...")` as if `psycopg2` connection executes DDL + returns fetchable cursor
- **Failure scenario:** Code cannot run as written; first restore/delete attempt fails at the invented call during an incident.
- **Fix:** Deletion-shaped local fix: replace with real dump/restore path (e.g. `pg_dump`/`pg_restore` or driver cursor) behind a tested helper; delete invented calls.
- **Trade-off:** Real dump path needs subprocess/streaming + credential handling instead of one-liner.

### [MAJOR] Ambient import-time DB connection, hardcoded DSN
- **Domain:** Maintainability (B2)
- **Verified by:** READ
- **Evidence:** `personal_data_lifecycle.py:8` — `_conn = psycopg2.connect("postgresql://localhost/orders")` at module scope
- **Failure scenario:** Import requires live DB; tests need real Postgres; credential/host change touches module; connection failure breaks unrelated imports.
- **Fix:** Boundary scope: connection factory + DI seam; config from environment; lazy connect.
- **Trade-off:** Adds indirection/plumbing for config and session lifecycle.

### [MINOR] Naive UTC snapshot key
- **Domain:** Interoperability (D2)
- **Verified by:** READ
- **Evidence:** `personal_data_lifecycle.py:35` — `Key=datetime.datetime.utcnow().isoformat()` (naive, no offset, contains `:`)
- **Fix:** Localized cleanup: timezone-aware UTC (e.g. `datetime.now(timezone.utc).isoformat()`) with agreed S3-safe format.
- **Disputed:** Correctness graded READ-only — naive-UTC vs aware-UTC is a crossing (writer → S3 key → restore/lister), so owner stands as Interoperability.

### [MINOR] Store handles masquerade as clients
- **Domain:** Maintainability (B4)
- **Verified by:** READ
- **Evidence:** `personal_data_lifecycle.py:17-19` — `SEARCH_INDEX = "orders-search"`, `CACHE = "orders-cache"`, `WAREHOUSE = "orders-warehouse"` then used as objects with methods
- **Fix:** Localized cleanup: rename to `*_NAME` and introduce typed clients.

### [INFO / SUGGESTION] Unauthenticated delete/read of personal data
- **Domain:** Security (S2)
- **Verified by:** READ
- **Evidence:** `personal_data_lifecycle.py:69-84` — `delete_customer(customer_id)` executes deletes with no caller/role check; `personal_data_lifecycle.py:87-96` — `support_notes(customer_id)` returns full notes with no scoping or audit
- **Fix:** Recommendation: require authenticated principal, object-level authorization, per-field minimization, and read-audit log; verify caller enforces it.
- **Source → Boundary → Sink:** Source: `customer_id` argument → Boundary: function entry (no check in file; caller boundary unmapped) → Sink: `DELETE`/select of personal data. Capped at Info: entry point unmapped, only 2 of 3 established.

## Aligns well
- `delete_customer`/`support_notes` use `%s` parameterization rather than string interpolation (S3)
- Retention intent is centralized in one `retention_policy()` function signature, giving a single seam to enforce (C8)

Cut by 15-cap: 0 findings (C:0 M:0 m:0 i:0) on axes none.
Excluded by --min: 0 findings.