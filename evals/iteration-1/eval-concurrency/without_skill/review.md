# Code Review: `concurrency.py`

## Overview
This module implements an in-memory rate limiter tracking client IP requests within a sliding window. While straightforward, it contains several critical concurrency defects and design limitations.

## Issues

### 1. Thread-Safety / Race Condition
The `REQUEST_COUNTS` dictionary is a global mutable object accessed across multiple worker threads without any locking mechanism.
- Multiple threads can concurrently execute `if client_ip not in REQUEST_COUNTS:` and overwrite each other's reset timers.
- The `entry["count"] = entry["count"] + 1` line is a read-modify-write operation which is not atomic. Under heavy load, requests will be dropped or undercounted.

**Recommendation:** Add a `threading.Lock()` or use an external cache like Redis.

### 2. Memory Leak (Unbounded Dictionary)
Old IP addresses are never removed from `REQUEST_COUNTS`. Over time, as distinct client IPs connect, memory usage will grow indefinitely until the application runs out of memory.

**Recommendation:** Use an LRU cache or a background thread to prune expired entries.

### 3. Time Monotonicity
The code uses `time.time()` (wall-clock time), which is susceptible to system clock shifts and NTP adjustments.

**Recommendation:** Use `time.monotonic()`.

### 4. Hardcoded Constants
`WINDOW_SECONDS` and `MAX_REQUESTS` are hardcoded at module level and cannot be configured per environment or client tier.
