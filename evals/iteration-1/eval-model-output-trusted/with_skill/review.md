Reviewing the file — reading it now.
Got the initial content — checking surrounding context to complete the review.
Confirmed isolated scope — loading review criteria to score the findings.
# Review: `evals/fixtures/model_output_trusted.py`

`8 findings · C:4 M:2 m:1 i:1 · Mean 79/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/model_output_trusted.py` · Not examined: 0 — none
Paths: 3 open · Unmapped: 0 — all crossings reached and classified
Unclassified: 0 findings fit no axis code
Domain Scores: Security: 25/100 · Correctness: 65/100 · Operations: 90/100 · Maintainability: 97/100 · Leanness: 97/100 · Interoperability: 100/100
Gated by: `Critical finding` — any Critical caps grade at F; weakest domain Security (F) also gates.

## Findings

### [CRITICAL] SQL injection via interpolated model output
- **Domain:** Security (S3)
- **Verified by:** DERIVED — `summarise_invoice()` → `llm()` completion → `run_invoice_sql(model_text)` → `cur.execute(f"...'{model_text}'")`
- **Evidence:** `model_output_trusted.py:31-35` — `cur.execute(f"SELECT total FROM invoices WHERE note = '{model_text}'")` where `model_text` is the raw `llm()` completion from `summarise_invoice():25`.
- **Failure scenario:** Source: attacker-influenced invoice document → model completion. Boundary: no parameterisation, escaping, or allowlist at DB crossing. Sink: `cur.execute()`. A crafted document inducing a `'`-terminated completion (e.g. `' OR '1'='1` / stacked statement) executes arbitrary SQL, exfiltrating or corrupting `invoices`.
- **Fix:** Parameterise query: `cur.execute("SELECT total FROM invoices WHERE note = %s", (model_text,))`, scope: local. Extract only validated fields from model output via schema, never raw prose, scope: boundary.
- **Trade-off:** Negligible latency; requires deciding what structured field to query on (module-scope contract change).

### [CRITICAL] Stored XSS persisted into invoice PDF
- **Domain:** Security (S3)
- **Verified by:** DERIVED — `llm()` completion → `render_html(completion, totals):39` → `write_pdf(invoice["id"], ...) :27`
- **Evidence:** `model_output_trusted.py:38-39` — `return f"<html><body><p>{model_text}</p><pre>{totals}</pre></body></html>"` with no escaping; written to persistent PDF in `summarise_invoice():27`.
- **Failure scenario:** Source: model completion (attacker-steerable). Boundary: no HTML-escaping / sanitisation. Sink: persisted PDF staff open daily. Completion containing `<script>` / malicious markup executes on every view.
- **Fix:** HTML-escape `model_text` and `totals` (e.g. `html.escape`) or render via auto-escaping template, scope: local. Treat model text as untrusted at render boundary, scope: boundary.
- **Trade-off:** One escape call per render; must pick escaping context (HTML vs PDF generator) — wrong context leaves bypass.

### [CRITICAL] SSRF to arbitrary URL from model text with redirect following
- **Domain:** Security (S3)
- **Verified by:** DERIVED — `model_text` → `re.search(r"https?://\S+", model_text):69` → `httpx.get(url, follow_redirects=True):70`
- **Evidence:** `model_output_trusted.py:61-70` — no scheme/host allowlist, `follow_redirects=True`, no timeout.
- **Failure scenario:** Source: model-produced link (steerable via prompt injection / crafted invoice). Boundary: no allowlist, redirects followed. Sink: server-side `httpx.get()`. Model can direct server to internal metadata (`169.254.169.254`), intranet, or attacker host, leaking cloud credentials / internal responses via returned `.text`.
- **Fix:** Allowlist scheme+host, `follow_redirects=False`, explicit `timeout=`, egress policy, scope: boundary. Never fetch model-supplied URLs without operator confirmation, scope: module.
- **Trade-off:** Adds allowlist maintenance and breaks open-ended fetch; timeout adds fail-closed behaviour under slow hosts.

### [CRITICAL] Untrusted model prose drives routing and financial charge
- **Domain:** Correctness (A7)
- **Verified by:** DERIVED — `llm("Classify...suggest a discount.", text):52` → regex `category`/`discount` → `file_ticket(queue=category.upper()):55` + `orders.apply_discount(..., int(...)):57`
- **Evidence:** `model_output_trusted.py:42-58` — `category` taken from prose and used as filing queue; `discount` percent applied straight to order total with no confirmation, bounds check, or allowlisted queue set.
- **Failure scenario:** Rephrased/hallucinated answer (`category: refunds`, `discount: 90%`) silently misroutes ticket to wrong team and charges a 90% discount. Suggestion is executed as privileged action.
- **Fix:** Treat completion as suggestion only: validate `category` against allowlisted queues, require human/ policy approval and max-cap for `apply_discount`, scope: boundary.
- **Trade-off:** Adds approval step / queue registry lookup; delays auto-filing but prevents silent financial loss.

### [MAJOR] Unchecked regex extraction crashes on off-format completion
- **Domain:** Correctness (A8)
- **Verified by:** DERIVED — `classify_ticket():53` `.group(1)` without None check; `fetch_report_url():69` `.group(0)` without None check
- **Evidence:** `model_output_trusted.py:53` — `re.search(r"category:\s*(\w+)", completion).group(1)`; `model_output_trusted.py:69` — `re.search(r"https?://\S+", model_text).group(0)`.
- **Failure scenario:** Any completion omitting `category:` or a URL raises `AttributeError`, crashing ticket classification / report fetch; fragile prose contract with no schema enforcement.
- **Fix:** Validate match is not None, enforce structured (JSON/function-call) model output with schema, scope: module.
- **Trade-off:** Requires defining output schema and retry/fallback path; small complexity increase.

### [MAJOR] External fetch with no timeout / retry budget
- **Domain:** Operations (C3)
- **Verified by:** DERIVED — `fetch_report_url():70` `httpx.get(url, follow_redirects=True)` with no `timeout=`
- **Evidence:** `model_output_trusted.py:70` — `return httpx.get(url, follow_redirects=True).text`
- **Failure scenario:** Slow/hung upstream hangs worker indefinitely, exhausting threads under load; no backoff/breaker.
- **Fix:** Set explicit `timeout=(connect, read)`, add retry budget with jitter or fail-fast, scope: local.
- **Trade-off:** Timeout tuning risks false failures on slow-legit hosts; needs observability on timeout rate.

### [MINOR] Unused imports `json`, `subprocess`
- **Domain:** Leanness (L2)
- **Verified by:** READ
- **Evidence:** `model_output_trusted.py:2-4` — `import json`, `import subprocess` never referenced in 70 lines.
- **Fix:** Delete unused imports.

### [INFO / SUGGESTION] No audit trail for auto-applied discount
- **Domain:** Operations (C4)
- **Verified by:** READ
- **Evidence:** `model_output_trusted.py:55-57` — `file_ticket` + `apply_discount` with no logging/correlation ID.
- **Fix:** Emit structured log with ticket ID, order ID, suggested vs applied discount, and model completion hash.

## Aligns well
- Docstrings explicitly label each trust violation (`model_output_trusted.py:17-23,44-50,63-67`), making intent auditable.