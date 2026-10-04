"""Exemplary production-ready payment verification service (Clean Control Fixture)."""
import logging
import random
import time
from typing import Optional
import sqlite3

logger = logging.getLogger("payment_service")

class PaymentVerificationService:
    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn

    def verify_payment(self, transaction_id: str, caller_tenant_id: str) -> Optional[dict]:
        """Verifies a payment record with full tenant isolation and parameterized query."""
        cursor = self.conn.cursor()
        # Parameterized query preventing SQL injection and scoped to caller tenant
        cursor.execute(
            "SELECT id, amount, status FROM transactions WHERE id = ? AND tenant_id = ?",
            (transaction_id, caller_tenant_id)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {"id": row[0], "amount": row[1], "status": row[2]}

    def execute_with_resilience(self, task_func, max_attempts: int = 3, base_delay: float = 0.5) -> dict:
        """Executes task with exponential backoff and jitter."""
        for attempt in range(1, max_attempts + 1):
            try:
                return task_func()
            except ConnectionError as exc:
                if attempt == max_attempts:
                    logger.warning("Payment verification failed after max retries", extra={"attempts": attempt})
                    raise
                # Exponential backoff with full jitter
                backoff = base_delay * (2 ** (attempt - 1))
                sleep_duration = random.uniform(0, backoff)
                time.sleep(sleep_duration)
