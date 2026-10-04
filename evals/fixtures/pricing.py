"""Order pricing."""

def price_for(subtotal: float, discount_rate: float, tax_rate: float = 0.0) -> float:
    """Apply the discount to the subtotal. Tax is applied by the caller."""
    return subtotal - (subtotal * discount_rate)
