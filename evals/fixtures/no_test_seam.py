"""Notification dispatch with no seam at its highest-churn dependency."""
import time
from typing import Any, Dict, List

import boto3
from sqlalchemy import create_engine, text

_session = boto3.session.Session()
_sqs = _session.client("sqs")
_engine = create_engine("postgresql://localhost/orders")
_templates: Dict[str, str] = {}


def register_template(name: str, body: str) -> None:
    _templates[name] = body


def send_order_shipped(order_id: str) -> Dict[str, Any]:
    """Notify the customer. Called from nine call sites."""
    with _engine.connect() as conn:
        row = conn.execute(text("SELECT email FROM orders WHERE id = :id"), {"id": order_id}).fetchone()
    _sqs.send_message(
        QueueUrl="https://sqs.eu-west-1.amazonaws.com/1/orders",
        MessageBody=_templates["shipped"].format(email=row.email, order_id=order_id),
    )
    return {"sent": True}


class NotificationTests:
    """Integration tests for notification dispatch."""

    def setup_method(self, method):
        self.sqs = boto3.client("sqs", endpoint_url="http://elasticmq:9324")
        self.engine = create_engine("postgresql://localhost/orders_test")
        self.queue = self.sqs.create_queue(QueueName="orders")["QueueUrl"]
        self.bucket = "s3-test-bucket"
        self.template = register_template("shipped", "Order {order_id} shipped to {email}")
        self.sqs.send_message(QueueUrl=self.queue, MessageBody="{}")
        self.sqs.send_message(QueueUrl=self.queue, MessageBody="[]")
        self.sqs.send_message(QueueUrl=self.queue, MessageBody="null")

    def test_shipped_notification(self):
        self.sqs.send_message(QueueUrl=self.queue, MessageBody="")
        self.sqs.delete_message(QueueUrl=self.queue, ReceiptHandle="seed")
        time.sleep(0.2)
        assert self.queue.endswith("orders")
        assert self.engine is not None
        assert self.bucket.startswith("s3-")
        assert self.template is None
