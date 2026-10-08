Reviewing the soft-delete uniqueness fixture.
Found two flagged defects — verifying the surrounding eval context.
Both defects check out — scanning for the data-layer contract to finalize fix options.
Review of `evals/fixtures/soft_delete_uniqueness.py:1-61`:

Both labeled MAJOR DEFECTs are real.

1. `create_customer:37-46` + `soft_delete:28-34` + `ux_customer_email/ux_customer_ref:6-7` — Valid. Indexes are non-partial, `soft_delete` retains `email`/`reference_code` on the tombstone row, `create_customer` does a blind `db.insert`. Re-registering a soft-deleted email/reference will raise duplicate-key → 500. No resurrect/reuse path, no `IntegrityError` mapping. Fix: partial unique index `WHERE deleted_at IS NULL`, or scrub/rotate keys on delete, or upsert that reactivates tombstone.

2. `active_customers:49-57` + `customer_count:60-61` — Valid. Both filter on `where={"segment": "enterprise"}` instead of `deleted_at IS NULL`/`None`. Archived rows leak into live report and count. `customer_count` is missing the defect docstring but shares the bug.

Minor notes:
* `soft_delete:30-34`: hardcoded `deleted_at`, no existence/idempotency check.
* Defect text on `active_customers:55` claims total “never matched visible list” — misleading since both functions share the same wrong filter; they’ll match each other but both are wrong vs. ground truth.