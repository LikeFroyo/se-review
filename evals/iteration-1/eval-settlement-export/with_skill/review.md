Reviewing your settlement export fixture — inspecting the isolated workspace.
Found the review domains — now loading the scoring rules for your target file.
I've mapped the encoding and cross-boundary issues — now verifying each defect with a quick execution check.
# Review: evals/fixtures/settlement_export.py

`6 findings · C:1 M:4 m:1 i:0 · Mean 87.5/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: evals/fixtures/settlement_export.py · Not examined: 0 — none
Paths: 0 open | 0 · Unmapped: 0 — no crossing lacked a reachable classification
Unclassified: 0 findings fit no axis code
Domain Scores: Interoperability: 45/100 · Correctness: 80/100 · Security: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Leanness: 100/100
Gated by: `Critical finding` — always printed. Any Critical caps the grade at F, and the weakest domain (Interoperability, F) independently gates it.

Serial review (1 file, below the 30-file / 5,000-line fan-out ceiling). Only files inside the workspace were read.

## Findings

### [CRITICAL] UTF-8 bytes read as Latin-1 produce mojibake on every non-ASCII merchant
- **Domain:** Interoperability (D1)
- **Verified by:** RAN — executed `csv.writer` round-trip plus `'Café'.encode('utf-8').decode('latin-1')` → `'CafÃ©'`; traced writer side (`StringIO`, no encoding declared) against reader side (`import_settlements`, Latin-1 assumption per docstring/reference implementation).
- **Evidence:** evals/fixtures/settlement_export.py:14-35 (writer returns `str` with no charset contract) against evals/fixtures/settlement_export.py:38-49 (partner side reads Latin-1, splits on CRLF).
- **Failure scenario:** Export of `{"merchant_name": "Café"}` is UTF-8 `C3 A9`; read back as Latin-1 it becomes `CafÃ©`, is stored/inserted under the corrupted name, and the partner's lookup by exact merchant name misses on every accented row. Round-trip is not identity and compounds if stored back.
- **Fix:** Establish one declared contract at the boundary (scope: boundary): e.g. export `bytes` as UTF-8 with explicit `encoding="utf-8", newline=""` file handling and a matching `encoding="utf-8"` reader, or pin Latin-1 on both sides; add a round-trip test with `Café`, `€`, and CJK names. Cost of the fix is a contract change, not a code tweak — both sides must change together.
- **Trade-off:** Pinning UTF-8 costs a one-time migration of the partner reader and any stored mojibake backfill; the alternative (pinning Latin-1) silently restricts the merchant alphabet and re-corrupts on the next non-Latin-1 name.

### [MAJOR] NFC writer vs NFD reader means the rate-card lookup never matches
- **Domain:** Interoperability (D1)
- **Verified by:** RAN — `unicodedata.normalize("NFC","Café")|branch != normalize("NFD",...)|branch` returns `False`; visually identical keys compare unequal.
- **Evidence:** evals/fixtures/settlement_export.py:65-69 (`build_lookup_key` normalizes NFC) vs evals/fixtures/settlement_export.py:72-77 (`read_lookup_key` normalizes NFD).
- **Failure scenario:** Every merchant with a precomposed character (`é`, `ü`, `ñ`) writes one key form and reads the other, so the cache/rate-card lookup misses and falls through to a default or duplicate record path.
- **Fix:** Fix one normalisation form on both sides (scope: boundary) — NFC is the usual choice — and normalize once at the boundary, not per call site.
- **Trade-off:** One-line change plus backfill of existing keys; must pick the form the rest of the store already uses or migrate it.

### [MAJOR] Byte-limit truncation splits multi-byte characters and raises instead of fitting the column
- **Domain:** Interoperability (D1)
- **Verified by:** RAN — `'€'*50 .encode('utf-8')[:128].decode('utf-8')` and `'é'*64 .encode('utf-8')[:127].decode('utf-8')` both raise `UnicodeDecodeError: unexpected end of data`. The docstring's "stored value is not valid UTF-8" is inaccurate: CPython raises; nothing is stored.
- **Evidence:** evals/fixtures/settlement_export.py:52-62 `return value.encode("utf-8")[:column_bytes].decode("utf-8")`.
- **Failure scenario:** A single long accented name raises inside the export path; depending on the caller, that aborts the whole file rather than degrading one field — one row loses every settlement. Correctness cross-references here and takes no separate deduction (owner stands).
- **Fix:** Truncate on the encoded form with error-tolerant decode or, better, loop-truncate by characters until `len(encoded) <= column_bytes` (scope: local). Decide the contract first: truncate-and-flag vs reject-with-error.
- **Trade-off:** Character-boundary truncation costs O(n) re-encode per value (negligible at this size) and silently shortens names; the reject alternative preserves data but requires an error path the caller does not currently have.

### [MAJOR] Hand-split CSV parsing breaks quoting, shifts fields, and ingests the header as data
- **Domain:** Interoperability (D1)
- **Verified by:** RAN — `csv.writer` emits `'id1,"Acme, Inc",10,9,2026-01-01\r\n'`; `line.split(",")` yields 6 fields (`['id1', '"Acme', ' Inc"', ...]`), so the record is skipped; the header line splits to exactly 5 fields and passes the `len(fields) != 5` guard, so it is inserted as a settlement.
- **Evidence:** evals/fixtures/settlement_export.py:38-49 (`text.split("\r\n")`, `line.split(",")`, no header skip, no `csv` reader) against evals/fixtures/settlement_export.py:24-25 (`csv.writer` quoting producer).
- **Failure scenario:** Any merchant containing a comma, quote, or embedded newline is quoted by the writer and then mis-split by the reader — fields shift and the row is silently skipped (`continue`); conversely the header row is inserted into `settlements` as `(settlement_id, merchant) = ('settlement_id','merchant')`. Note: the writer's `\r\n` and the reader's `split("\r\n")` currently agree, so the docstring's "trailing CR on every line" claim was not reproduced — the delimiter/header defects above are the demonstrated ones.
- **Fix:** Parse with `csv.reader(io.StringIO(text))` (or stream the file) and explicitly skip/validate the header (scope: module — importer function plus its header contract).
- **Trade-off:** Adds correct quoting/newline handling at the cost of one small dependency on already-imported `csv`; header policy (require vs tolerate absent header) must be pinned or a headerless file loses its first record.

### [MAJOR] Importer calls `execute` on a connection that has no such method, with no cursor or commit
- **Domain:** Correctness (A8)
- **Verified by:** DERIVED — trace chain: module-level `_conn = psycopg2.connect(...)` at evals/fixtures/settlement_export.py:10 → `_conn.execute(...)` at evals/fixtures/settlement_export.py:45-47. In `psycopg2` the DB-API `execute` lives on cursors (`conn.cursor().execute(...)`), not connections; every call raises `AttributeError`, and no `commit()` ever runs, so even a cursor fix without commit persists nothing.
- **Evidence:** evals/fixtures/settlement_export.py:10 and evals/fixtures/settlement_export.py:45-47.
- **Failure scenario:** `import_settlements` fails on its first row on every invocation — settlement ingestion is 100% broken (observed as an exception, not silent loss).
- **Fix:** Acquire a cursor per import (or per batch), execute parameterized inserts on it, and commit once (scope: module).
- **Trade-off:** Cursor-per-import adds one round trip and requires deciding commit granularity (per-file commit is cheapest and matches the file-at-once importer; per-row commit is slower but partially persists on failure).

### [MINOR] Module-level database connect runs at import time with a hardcoded DSN
- **Domain:** Operations (C3)
- **Verified by:** READ — `psycopg2.connect("postgresql://localhost/ledger")` at import scope; no timeout, retry, or lazy init.
- **Evidence:** evals/fixtures/settlement_export.py:8-10.
- **Fix:** Move connect into a factory / lazy init read from config with a connect timeout (scope: local).

## Aligns well
- Parameterized `INSERT ... VALUES (%s, %s)` (S3): values never interpolated into SQL, so the merchant-name path carries no injection sink.
- `csv.writer` on the producer side (D4): quoting is delegated to the stdlib instead of hand-joined.

## Evolution candidates
- None. No defect class observed that lacks a covering guideline.