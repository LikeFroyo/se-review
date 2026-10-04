# Code Review for idor_access.py

Here are a few suggestions to improve this code:

1. **Unused parameter**: In both `get_medical_record` and `update_medical_notes`, `current_user` is passed in as an argument but never actually used. You should either use it to verify the user or remove it.
2. **Database abstraction**: `RECORDS_DB` is a simple dictionary. In a production app, use an ORM or database repository pattern.
3. **Input validation**: Validate that `new_notes` is not empty or overly long before saving.
4. **Audit logging**: Add logging when medical records are fetched or updated so there is an audit trail.
