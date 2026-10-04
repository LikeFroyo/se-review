# Code Review: `retry.py`

## Summary

This is a small module that pushes a payload to a remote endpoint and retries up to 5 times when the server returns a 5xx error. The intent is clear, but the retry logic has several issues that would cause problems in production.

---

## Issues

### 1. No backoff between retries

The loop fires all 5 requests as fast as possible with zero delay. If the server is overloaded or temporarily down, hammering it immediately makes things worse and is unlikely to succeed.

**Suggestion:** Add exponential backoff (or at least a fixed delay) between attempts.

```python
import time

for attempt in range(5):
    resp = requests.post(SYNC_URL, json=payload, timeout=TIMEOUT_S)
    if resp.status_code < 500:
        return resp
    time.sleep(2 ** attempt)  # 1s, 2s, 4s, 8s, 16s
```

### 2. Network exceptions are not caught

`requests.post` can raise `requests.exceptions.ConnectionError`, `requests.exceptions.Timeout`, and other exceptions. These will immediately propagate and skip the retry loop entirely — which is exactly the scenario where retrying is most useful.

**Suggestion:** Wrap the call in a `try/except` block:

```python
try:
    resp = requests.post(SYNC_URL, json=payload, timeout=TIMEOUT_S)
except requests.exceptions.RequestException:
    if attempt == max_retries - 1:
        raise
    continue
```

### 3. `resp.raise_for_status()` after the loop may reference an unbound variable

If `range(5)` were ever changed to `range(0)`, `resp` would be unbound when `raise_for_status()` is called, producing a `NameError` instead of a meaningful error. More practically, the current code assumes the loop always executes at least once — this is fragile.

**Suggestion:** Initialize `resp = None` before the loop and handle the edge case, or restructure so the function always returns or raises explicitly.

### 4. The retry count is a magic number

The `5` in `range(5)` should be a named constant (like `TIMEOUT_S` already is) for readability and easy tuning.

```python
MAX_RETRIES = 5
```

### 5. No logging

When retries happen it's important to know about it. Silent retries make debugging production issues very difficult.

**Suggestion:** Log a warning on each retry with the status code (or exception) so operators have visibility.

### 6. Client-error responses (4xx) are silently returned

Status codes like 400 or 403 are returned as-is without any warning or logging. Depending on the use case, callers may forget to check `resp.status_code`, leading to silent data loss. This may be intentional (letting the caller decide), but it's worth documenting or reconsidering.

---

## What's done well

- The module is short and focused — one function, one responsibility.
- Constants (`SYNC_URL`, `TIMEOUT_S`) are defined at module level rather than buried in the function.
- The `timeout` parameter is set on the request, avoiding indefinite hangs.
- The docstring clearly states the intent.
