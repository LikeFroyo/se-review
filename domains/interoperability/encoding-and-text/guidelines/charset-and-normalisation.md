# Charset & normalisation — the same characters, differently encoded

Audit the declared encoding against the actual bytes, and the normalisation form against the other side's.

## What to look for

- **Encoding assumed rather than declared:** A file or stream read with the platform default, the locale default, or an implicit UTF-8 assumption, so the same bytes decode differently on a differently-configured host.
- **Encoding declared on one side only:** A column, a header, or a file written as UTF-8 with nothing marking it, read by a consumer that guesses Latin-1, producing mojibake that is stored back and compounds on every round trip.
- **Normalization form not fixed:** One side composing or comparing precomposed characters and the other using decomposed forms, so a name, a search term, or a deduplication key that is visually identical compares unequal and creates a duplicate record.
- **BOM assumed present or absent:** A byte-order mark written on some paths and not others, so a strict parser rejects half the files, or a mark is read as part of the first field.
- **Case- or width-folding applied on one side only:** Case-insensitive comparison, width folding, or canonical equivalence used for matching in one component and not the other, so a lookup succeeds in one path and fails in another.
- **Invisible characters carried as data:** Zero-width, non-breaking space, or soft-hyphen characters inside an identifier or a name field, which defeat exact matching and are stripped by the consumer but not the producer.
- **Round-trip that is not identity:** A value encoded, decoded, and re-encoded through two components that does not come back byte-identical, so a diff or a checksum on the original no longer validates.
