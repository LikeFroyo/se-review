# Review of memory_leak.py

Here are some general recommendations to improve the analytics cache code:

1. **Global variable usage**: Using a global dictionary `QUERY_RESULT_CACHE` is generally discouraged. Consider encapsulating it inside a service class.
2. **Cache invalidation**: The cache does not have an expiration mechanism, so older entries may become stale if underlying metrics change.
3. **Data slicing**: Slicing `raw_samples[:100]` will create a new list slice each time.
4. **Missing error handling**: If `metric` is not found in `item`, `item.get(metric, 0)` works, but make sure raw dataset entries are valid dictionaries.
