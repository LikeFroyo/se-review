# Boundaries & truncation — where text is cut, split, or delimited

Audit every place text is length-limited, split on a delimiter, or joined into a line, where the two sides may be counting different things.

## What to look for

- **Byte limit applied to a character string:** A column or field limit in bytes used to truncate a multi-byte string mid-character, producing invalid encoding and a value that no longer parses on the other side.
- **Character limit applied to a byte buffer:** A length checked in characters against a buffer measured in bytes, so a value within the limit overflows the column and is truncated by the database instead.
- **Delimiter inside an unescaped field:** A name, note, or address concatenated into a delimited file or header without quoting, producing an extra column and shifting every field after it.
- **Line-ending mismatch:** One side writing `\n` and the other splitting on `\r\n`, leaving a stray carriage return at the end of the last field of every line — invisible, and it breaks exact key comparison.
- **Split with a fixed count:** A string split into N pieces with a limit, assuming exactly N fields, so an embedded delimiter silently changes the field count and the tail is dropped.
- **CSV formula injection as a boundary hazard:** A value beginning with a formula character written into a spreadsheet-consumed file, where the *consumer* is the interpreter — reported to `correctness/security` and cross-referenced here.
- **Header row assumed present:** A consumer that skips the first record unconditionally, so a file with no header is read as data and one record is lost.
- **Concatenation with no separator contract:** Values joined into one key or one line with a separator that can appear inside a value, so two different tuples produce the same key.
