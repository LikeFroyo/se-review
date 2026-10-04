"""Email normalisation. Callers treat any non-empty return as a valid address."""

def normalise_email(raw: str) -> str:
    """Lowercase the domain and strip surrounding whitespace."""
    trimmed = raw.strip()
    local, sep, domain = trimmed.partition("@")
    if not sep:
        return trimmed.lower()
    return f"{local}@{domain.lower()}"
