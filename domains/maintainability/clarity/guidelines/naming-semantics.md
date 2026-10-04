# Naming semantics — intent communication and readability

Audit identifiers, functions, and boolean predicates.

## What to look for

- **Misleading names:** A function name promising one behavior while performing unexpected side effects (e.g. `calculate_total()` mutating database records or dispatching emails).
- **Vague / generic names:** Variables named `data`, `info`, `temp`, `manager`, or `handler` that obscure true business semantics.
- **Inverted boolean naming:** Booleans with double negatives (`not_disabled = True`) or non-predicate naming.
- **Inconsistent terminology:** Using conflicting terms for the same domain concept (e.g. mixing `user`, `customer`, `account`, and `client` interchangeably).
- **Name encodes the implementation:** Identifiers that freeze a decision the next change is likely to reverse — `get_user_from_redis`, `fetch_sql_v2`, a name naming the storage engine, the framework, or the algorithm inside it. The name then has to change with the implementation, so the rename rides along with every refactor.
- **Temporary suffix that became permanent:** `*_new`, `*_old`, `*_temp`, `*_final`, or a version suffix on a symbol still in use, so two live things differ only by a suffix that no longer describes them.
