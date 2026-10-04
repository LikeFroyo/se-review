"""Medical records API service handler.
Demonstrates Broken Object-Level Authorization (IDOR / CWE-639 / OWASP A01):
Fetches and mutates sensitive records using client-supplied IDs without verifying
ownership or role-based access permissions.
"""

from typing import Any, Dict, Optional

# Mock database records
RECORDS_DB: Dict[str, Dict[str, Any]] = {
    "rec-101": {
        "patient_id": "usr-alice",
        "diagnosis": "Hypertension",
        "notes": "Prescribed Lisinopril 10mg daily",
    },
    "rec-102": {
        "patient_id": "usr-bob",
        "diagnosis": "Type 2 Diabetes",
        "notes": "Prescribed Metformin 500mg BID",
    },
}


def get_medical_record(
    record_id: str,
    current_user: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Retrieve patient medical record by record_id.

    A5 CRITICAL Defect (IDOR / BOLA):
    The handler trusts the client-supplied record_id directly. It never checks
    whether current_user owns the record (current_user['id'] == record['patient_id'])
    or possesses a privileged role (e.g., 'doctor' or 'medical_admin').
    Any authenticated user can read any patient's sensitive medical history by enumerating record_ids.
    """
    if record_id not in RECORDS_DB:
        return None

    # Returns sensitive record without authorization check
    return RECORDS_DB[record_id]


def update_medical_notes(
    record_id: str,
    new_notes: str,
    current_user: Dict[str, Any],
) -> bool:
    """Update clinical notes on a patient medical record.

    A5 CRITICAL Defect:
    Allows arbitrary users to overwrite medical records without verifying authorization.
    """
    if record_id not in RECORDS_DB:
        return False

    # Mutates record without verifying current_user permissions or ownership
    RECORDS_DB[record_id]["notes"] = new_notes
    return True
