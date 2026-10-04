# Encoding & Text Sub-Domain Evaluator

Audits text that changes representation between a process, a file, a database, and a wire. The bytes are the same length; the meaning is not.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Charset & Normalisation** | Declared vs actual encoding, BOM, normalisation forms, invisible characters | `guidelines/charset-and-normalisation.md` |
| **Boundaries & Truncation** | Byte vs character limits, line endings, delimiter escaping, invisible in output | `guidelines/boundaries-and-truncation.md` |

## Sub-domain scoring & deduction rules
- Text read with a different charset than it was written, producing corrupt or unsearchable records: **CRITICAL** (-25 points).
- Byte-length truncation applied to a multi-byte string, splitting a character: **MAJOR** (-10 points).
- Normalisation form differing between the two sides, so a lookup by name or key misses: **MAJOR** (-10 points).
- Line-ending or BOM difference that a strict parser rejects: **MAJOR** (-10 points).
- Delimiter or quoting difference producing an extra or missing field: **MAJOR** (-10 points).
- Encoding declared explicitly on both sides and agreeing: **INFO** (0 points).

## Scope boundary

- SQL or command injection through text is `correctness/security`; report it there and cross-reference, do not re-grade it here.
- A mis-set charset with no boundary — a single process, one file read and written the same way — is not an interoperability finding.
