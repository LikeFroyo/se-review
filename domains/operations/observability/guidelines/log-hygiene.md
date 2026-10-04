# Log hygiene — sensitive data redaction and cardinality caps

Audit logs and metrics for security leaks and operational noise.

## What to look for

- **Plaintext credentials or PII in logs:** Printing raw request bodies, authorization headers, passwords, credit card numbers, or API keys to logs.
- **Metric label cardinality explosion:** Attaching high-cardinality attributes (user IDs, email addresses, order IDs) as metric labels, crashing metric stores.
- **Excessive debug logging on hot paths:** Printing verbose debug logs on every request in production, flooding disk I/O and increasing log ingestion costs.
- **Log/error text asserting removed behavior:** Error messages, usage strings, or log lines naming commands, flags, paths, or limits the code no longer has.
- **Intent reported as outcome:** Progress or completion logged before the outcome is known (counts printed before the flush, success logged before the commit).
