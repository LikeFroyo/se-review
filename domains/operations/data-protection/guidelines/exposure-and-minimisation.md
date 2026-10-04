# Exposure & minimisation — collection beyond need, access beyond role

Audit what is collected, who can reach it, and whether the person can obtain their own record.

## What to look for

- **Collection with no stated purpose:** Fields captured because a form or an SDK offered them, with no record of why, and no consumer that reads them.
- **Data collected and never read:** A column, event, or log field no query, export, or feature consumes — personal data held for a purpose that does not exist.
- **Whole-record access for a narrow need:** An endpoint or a query returning a full customer or employee record where the caller needs three fields, so every reader holds everything.
- **Access not scoped to the minimum:** Personal data visible to a role, a tenant, or a support agent beyond what the task needs, with no justification and no per-field restriction.
- **Unencrypted personal data at rest:** A sensitive field, column, or object store written without encryption, or with keys in the same store as the data.
- **No record of who read it:** A read of personal data leaving no entry anywhere, so a subject-access request or a breach investigation cannot name the readers.
- **Subject request answered from one store:** A data-export or rectification flow reading only the primary database, so the copy handed to the person is incomplete or wrong.
- **Consent or notice outside the system of record:** Consent captured in a form, a spreadsheet, or a tag, while the data lives elsewhere, so the record of consent cannot be produced or withdrawn against the actual data.
- **Free-text fields holding personal data:** A notes, description, or comment field that routinely contains names, addresses, or identifiers with no classification, redaction, or length bound.
