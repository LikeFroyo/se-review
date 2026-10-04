# Review: evals/fixtures/idor_access.py

`1 finding · C:1 M:0 m:0 i:0`

## Findings

### [CRITICAL] Broken object-level authorization (IDOR) exposes and allows tampering of patient medical records
- **Axis:** A5 (Security)
- **Evidence:** `evals/fixtures/idor_access.py:22-49` — In both `get_medical_record` and `update_medical_notes`, client-supplied `record_id` is looked up directly in `RECORDS_DB` with no verification that `current_user["id"] == record["patient_id"]` or that `current_user` possesses clinical role entitlements (`"doctor"` / `"medical_admin"`).
- **Failure scenario:** Any authenticated caller can enumerate integer or UUID keys (`rec-101`, `rec-102`) to view other patients' private diagnoses and prescriptions, or submit arbitrary payloads to overwrite medical treatment notes. This constitutes a severe HIPAA/GDPR compliance violation and total breach of patient confidentiality and data integrity.
- **Fix:** Enforce server-side resource authorization before retrieving or mutating records: verify that the authenticated caller's identity matches `record["patient_id"]`, or evaluate role-based permissions against an access control policy before returning or modifying the database entity.
- **Trade-off:** Adds an authorization check step (and potential metadata query overhead) to the request path, and requires integrating a centralized permission service or role resolver.

## Aligns well
- Handlers cleanly return `None` or `False` for non-existent record keys without raising unhandled `KeyError` exceptions (A1).
