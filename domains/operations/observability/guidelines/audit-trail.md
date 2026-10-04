# Audit trail — durable records for actions that matter

Audit whether the system can answer "who did this, when, and from where" for actions that change access, money, or data ownership.

## Missing or fragile records

- **No audit event for the action:** A handler that grants or revokes a role, changes a payment or refund, exports customer data, or alters a permission, with no append-only record of the actor, target, and time.
- **Audit written to the application log:** The record goes to the same stream and log level as debug output, so raising the level to debug, a log rotation, or a sampling rule silently drops the audit trail.
- **Actor not recorded independently:** The event logs only the object acted on, with the acting identity taken from a field the caller supplied rather than from the verified session.
- **Before-and-after state absent:** Only the outcome is recorded, so it cannot be shown what the value was prior to the change.
- **Audit records mutable or deletable:** The store accepts updates and deletes on the audit table itself, so the record is evidence of nothing.

## Incomplete coverage

- **Failures not audited:** Rejected and denied actions — a failed authorization, a rejected payment, a refused withdrawal — are not recorded, so abuse is invisible precisely when it is happening.
- **Read access not audited:** Bulk exports, report generation, and administrative listing are unrecorded, so data leaving the system leaves no trace.
- **Retention shorter than the investigation window:** Audit records expire sooner than the period a dispute, chargeback, or breach investigation can cover.
