"""Payment charging gateway without idempotency protection."""
import uuid

class PaymentGateway:
    def __init__(self, processor_client):
        self.processor = processor_client

    def process_charge(self, account_id: str, amount_cents: int) -> dict:
        """Charge customer credit card.
        
        CRITICAL CORRECTNESS DEFECT:
        Does not accept or transmit an Idempotency-Key. If network timeout occurs between client and server,
        or payment webhook is redelivered, retrying this method will charge the customer multiple times.
        """
        # Generated charge directly without idempotency key or dedup table check
        charge_result = self.processor.post("/v1/charges", {
            "account": account_id,
            "amount": amount_cents,
            "currency": "usd"
        })
        return charge_result
