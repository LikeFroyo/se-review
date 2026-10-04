# Code Review: `injection.py`

## Overview

This is a small login handler module that authenticates users by querying a SQLite database. It's only 17 lines, but it contains two critical security vulnerabilities.

---

## Critical Issues

### 1. SQL Injection (Line 14)

The `authenticate` function builds its SQL query using an f-string with user-supplied values interpolated directly into the query:

```python
query = f"SELECT id, name FROM users WHERE name = '{username}' AND pass = '{password}'"
```

An attacker can trivially bypass authentication by providing input like `' OR '1'='1' --` as the username. This is the textbook definition of a SQL injection vulnerability.

**Fix:** Use parameterized queries:

```python
def authenticate(username, password):
    """Return the user row when credentials match, else None."""
    query = "SELECT id, name FROM users WHERE name = ? AND pass = ?"
    with get_db() as db:
        return db.execute(query, (username, password)).fetchone()
```

### 2. Hardcoded API Key / Secret (Line 5)

```python
API_KEY = "sk-live-9f2c41aa77d84e0fb31c5d90a2e77c1d"  # service key for user sync
```

A live secret key is committed directly in source code. Anyone with read access to the repository can see and use this key. The `sk-live-` prefix suggests this is a production credential.

**Fix:** Load secrets from environment variables or a secrets manager:

```python
import os

API_KEY = os.environ["USER_SYNC_API_KEY"]
```

---

## Other Issues

### 3. Passwords Stored / Compared in Plain Text

The query compares `pass = '{password}'`, which implies passwords are stored as plain text in the database. Passwords should be hashed (e.g., with `bcrypt` or `argon2`) and compared using a constant-time comparison function.

### 4. Hardcoded Database Path (Line 4)

```python
DB_PATH = "/var/app/users.db"
```

This hardcodes a Unix-style absolute path, making the module non-portable and difficult to test. Consider making it configurable via an environment variable or a constructor parameter.

### 5. No Input Validation

There is no validation on `username` or `password` (e.g., checking for empty strings, max length). While parameterized queries remove the injection risk, basic validation is still good practice.

### 6. `API_KEY` Is Unused

The `API_KEY` constant is defined but never used in this module. If it's needed elsewhere, it should live in a shared configuration module—not alongside the login handler. If it's not needed, remove it.

---

## Summary

| Issue | Severity |
|---|---|
| SQL injection via f-string query | **Critical** |
| Hardcoded production API key | **Critical** |
| Plain-text password storage/comparison | High |
| Hardcoded database path | Low |
| No input validation | Low |
| Unused `API_KEY` constant | Low |

The two critical issues (SQL injection and the leaked secret) must be fixed before this code goes anywhere near production.
