"""Order fulfillment processor — debits payment and provisions account access."""
import logging

logger = logging.getLogger(__name__)


def process_fulfillment(order_id: str, payment_gateway, account_service, db_conn) -> bool:
    """Debit customer and provision access. Returns True on success, False on failure."""
    try:
        # Step 1: Charge customer
        payment_gateway.charge(order_id)
        db_conn.execute("UPDATE orders SET payment_status = 'PAID' WHERE id = ?", (order_id,))
        
        # Step 2: Provision service access
        account_service.provision(order_id)
        db_conn.execute("UPDATE orders SET fulfillment_status = 'COMPLETED' WHERE id = ?", (order_id,))
        return True
    except Exception:
        # Critical error masking:
        # Swallows all exceptions (network timeout, payment declined, DB failure),
        # logs no traceback or error details, and leaves orders in partial states
        # (e.g. customer charged, but provision failed and marked failed without refund).
        return False
