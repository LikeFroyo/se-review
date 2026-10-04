# Injection & secrets — sanitization, parameterization, and credential safety

Audit source-to-sink data flow for untrusted inputs and secret leakage.

## What to look for

- **SQL / NoSQL injection:** String-concatenating or f-string formatting untrusted user input into database queries instead of using parameterized queries.
- **Command & shell injection:** Passing unsanitized user arguments to `subprocess`, `exec`, or shell interpreters.
- **Server-Side Request Forgery (SSRF):** Fetching URLs provided directly by clients without strict domain/IP allowlists and blocking access to cloud metadata services (e.g. `169.254.169.254`) and private subnets.
- **Hardcoded secrets:** Committing API keys, database passwords, private keys, or tokens in source code, configuration files, or test fixtures.
- **Non-constant-time comparison:** Using standard `==` or `!=` operators to compare cryptographic signatures, hashes, or auth tokens instead of constant-time comparisons.
