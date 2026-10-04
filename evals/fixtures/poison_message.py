"""Message queue worker without Dead Letter Queue (DLQ) or poison message isolation."""
import json
import logging

logger = logging.getLogger("worker")

class OrderEventConsumer:
    def __init__(self, queue_client, db_session):
        self.queue = queue_client
        self.db = db_session

    def process_next_message(self):
        """Pulls and processes an order event.
        
        DISTRIBUTED SYSTEMS DEFECT:
        If a malformed message arrives that causes json.loads or schema parsing to raise,
        the exception is caught and the message is NOT acknowledged or routed to a Dead Letter Queue (DLQ).
        The message remains at the head of the queue and is redelivered indefinitely, blocking all subsequent orders.
        """
        msg = self.queue.receive_message()
        if not msg:
            return
            
        try:
            payload = json.loads(msg.body)
            self.db.orders.insert_one(payload)
            self.queue.acknowledge(msg.id)
        except Exception as e:
            logger.error(f"Failed to process message {msg.id}: {e}")
            # Message is not routed to DLQ or discarded after N attempts; loops infinitely!
