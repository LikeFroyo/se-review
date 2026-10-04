# Retention & erasure — how long, and can a person be forgotten

Audit whether data actually leaves the system when it should, and whether anything keeps it forever by accident.

## What to look for

- **No retention period on personal data:** A table, index, queue, or bucket holding personal data with no expiry, so records accumulate indefinitely and there is no defined point at which the obligation ends.
- **Retention never executed:** A documented retention schedule with no job enforcing it, so the schedule is a document and the data never leaves.
- **Erasure not honoured in every copy:** A delete that removes the primary row while the record survives in search indexes, caches, analytics stores, data warehouses, message queues, or audit tables, so the person is not actually forgotten.
- **Erasure blocked by a foreign key or a legal hold with no review:** A hold that keeps personal data indefinitely because no one ever lifts it, and no record of why the hold exists.
- **Backups outlive the deletion:** Personal data present in backups that are never expired or scrubbed, so an erasure request is answered "done" while the data still exists and will be restored by a later disaster.
- **Onward retention in a third party:** Personal data shared with a processor, an analytics provider, or a sub-processor with no stated retention or deletion obligation, so the controller cannot answer where the data is.
- **Retention applied to the wrong axis:** Expiry driven by an access or update timestamp, so a record repeatedly touched never ages out while an untouched one does.
