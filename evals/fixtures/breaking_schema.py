"""Public customer response serializer with breaking contract changes."""

def serialize_customer_v1(customer_record: dict) -> dict:
    """Serializes customer profile for public API consumers.
    
    BREAKING CONTRACT DEFECT:
    1. Renamed required field: `customer_id` was renamed to `id` without deprecation window or alias.
    2. Type mutation: `tier_code` changed from integer (e.g. 1, 2) to string enum ('GOLD', 'SILVER').
    Existing client SDKs and mobile apps parsing customer_id or expecting an int will crash upon rollout.
    """
    return {
        "id": customer_record["customer_id"],          # Breaking rename from customer_id
        "tier_code": str(customer_record["tier"]),      # Breaking type mutation from int to str
        "email": customer_record["email"],
    }
