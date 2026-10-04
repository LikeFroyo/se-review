"""Order checkout and discount processing handler.
Demonstrates excessive cyclomatic complexity, deep nesting, god function smell,
and boolean flag arguments violating Single Responsibility.
"""

from typing import Any, Dict, List, Optional


def process_order_checkout(
    order: Dict[str, Any],
    user_tier: str,
    items: List[Dict[str, Any]],
    is_vip: bool,
    apply_override: bool,
    send_receipt: bool,
    audit_log: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Process order discounts, inventory validation, total computation, and dispatch.

    Smell: Deep nesting (>4 levels), cyclomatic complexity > 15, god method doing
    discount math, inventory checks, notification formatting, and audit trails.
    """
    total = 0.0
    discount = 0.0
    tax = 0.0
    currency = order.get("currency", "USD")

    if not items:
        return {"status": "error", "message": "Empty cart"}

    for item in items:
        price = item.get("price", 0.0)
        qty = item.get("quantity", 1)
        stock = item.get("stock", 0)

        if qty <= 0:
            continue

        if stock < qty:
            if not apply_override:
                return {"status": "error", "message": f"Out of stock: {item.get('name')}"}
            else:
                if audit_log is not None:
                    audit_log.append(f"Override: Backorder permitted for {item.get('id')}")

        line_price = price * qty

        if is_vip:
            if user_tier == "PLATINUM":
                if line_price > 1000.0:
                    discount += line_price * 0.25
                else:
                    discount += line_price * 0.20
            elif user_tier == "GOLD":
                if line_price > 500.0:
                    discount += line_price * 0.15
                else:
                    discount += line_price * 0.10
            else:
                discount += line_price * 0.05
        else:
            if user_tier == "SILVER":
                if qty > 10:
                    discount += line_price * 0.08
                else:
                    discount += line_price * 0.03
            else:
                if line_price > 5000.0:
                    discount += line_price * 0.02

        total += line_price

    taxable = max(0.0, total - discount)
    if currency == "USD":
        tax = taxable * 0.0825
    elif currency == "EUR":
        tax = taxable * 0.21
    else:
        tax = taxable * 0.10

    final_amount = taxable + tax

    if send_receipt:
        # Side-effect inside calculation function
        email = order.get("customer_email")
        if email:
            if "@" in email:
                if audit_log is not None:
                    audit_log.append(f"Notification queued for {email}")

    return {
        "status": "success",
        "subtotal": round(total, 2),
        "discount": round(discount, 2),
        "tax": round(tax, 2),
        "final_amount": round(final_amount, 2),
        "currency": currency,
    }
