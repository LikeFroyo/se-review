# Transactions & migrations — ACID boundaries and schema evolution

Audit transaction scoping, isolation levels, and database schema migrations.

## What to look for

- **Long-running transactions:** Wrapping slow network RPCs, user-wait loops, or heavy processing inside an open database transaction, holding lock rows open.
- **Unatomized co-dependent writes:** Modifying multiple database rows or tables that depend on each other without an enclosing transaction boundary.
- **Destructive schema migrations:** Dropping columns or changing constraints in a single deploy step instead of using the Expand/Contract (multi-phase) migration pattern.
- **Exclusive table locks on hot tables:** Adding columns with non-null defaults or building indexes without non-blocking options (e.g. `CREATE INDEX CONCURRENTLY`).
