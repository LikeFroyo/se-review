Reviewing the export fixture — reading the code.
Seen the main file — now checking the surrounding run context.
Got the scope — now verifying each suspected defect by execution before grading.
Review: `settlement_export.py:1-77`

Verified by execution (`RAN`) where noted; docstring claims checked against code.

**Critical**

1. `settlement_export.py:45` — `_conn.execute(...)` does not exist on `psycopg2` connection; requires `cursor().execute()`. Current code raises `AttributeError` on any call. Verified by: RAN (spec-mock without `execute` fails) + `psycopg2` API.
   Fix (local): `with _conn.cursor() as cur: cur.execute(...)` + commit. Cost: one cursor acquisition per row/batch; scope: local.

2. `settlement_export.py:38-49` — `import_settlements` uses `text.split("\r\n")` + `line.split(",")`:
   - header `settlement_id,merchant,...` has 5 fields, so counted/inserted as data. Verified by: RAN (`parsed=2` for 1-row input, first insert is header).
   - `export_settlements` correctly quotes (`"café, inc"`), importer splits to 6 fields and drops the row. Verified by: RAN.
   Fix (local): use `csv.reader(io.StringIO(text, newline=''))`, skip header. Cost: negligible; scope: local.

**Major**

3. `settlement_export.py:10` — `psycopg2.connect(...)` at import with hardcoded DSN. Import fails if DB down, untestable, no close/pooling. Fix: lazy factory / dependency injection. Cost: small refactor; scope: module boundary.

4. `settlement_export.py:62` — `truncate_to_column`: `encode()[:128].decode()` raises `UnicodeDecodeError` on mid-character cut, aborting whole export. Verified by: RAN (`'é'[:1]` raises). Docstring says “stored value is not valid UTF-8” — wrong, it never stores, it raises. Still data-loss for whole file from one long name.
   Fix (local): truncate by chars with byte-check loop or `errors='ignore'` + explicit policy. Cost: O(n); scope: local.

5. `settlement_export.py:65-77` — `build_lookup_key` NFC vs `read_lookup_key` NFD: keys never match for non-ASCII (`café` verified `match=False`, RAN). Silent cache miss. Also `key.split("|")` breaks if merchant contains `|` / missing delimiter.
   Fix (local): normalize both sides identically, use tuple or escaped separator. Cost: negligible; scope: local.

**Info / docstring corrections**

6. `settlement_export.py:14-24` — claimed “trailing CR stays / split mismatch” not reproduced here: `csv.writer` defaults to `\r\n` (RAN: `'a,b\r\n'`), importer splits on `\r\n`, so no stray `\r`. Encoding mojibake is downstream (this function returns `str`, no file `encoding=` involved). Real gap: no encoding contract documented/enforced. Fix: return `bytes` or document `utf-8-sig` + agree with partner; add `newline=''` on file open by caller.

7. `settlement_export.py:3-6,11` — unused: `datetime`, `json`, `Optional`, `UTC="UTC"`. Remove.

No evidence for whole-file loss via invalid UTF-8 read; actual mechanism is #4 raising or #2 dropping rows.