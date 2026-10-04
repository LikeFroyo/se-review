# Hot loops & allocations — buffer efficiency and GC pressure

Audit CPU and allocation pressure on high-frequency paths.

## What to look for

- **Growth-by-append in tight loops:** Appending to slices/lists inside loops without preallocating capacity when size is known beforehand.
- **String concatenation inside loops:** Using `+` or `+=` on strings inside loops causing $O(N^2)$ memory reallocation churn.
- **Unbuffered whole-payload reads:** Reading entire large files or unbounded HTTP response bodies into memory buffers at once (`readAll()`) instead of streaming chunks.
- **Synchronous I/O on event loops:** Performing blocking disk or network operations inside asynchronous event loops or high-throughput request handlers.
