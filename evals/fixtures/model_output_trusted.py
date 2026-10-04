"""Invoice summariser and triage classifier."""
import json
import re
import subprocess
from typing import Any, Dict, List

import httpx

from db import connection

SYSTEM_PROMPT = "Summarise the invoice and classify the ticket category."


def summarise_invoice(invoice: Dict[str, Any]) -> Dict[str, Any]:
    """Summarise an invoice and file it.

    CRITICAL DEFECT:
    The model's text is treated as structured data and then used directly:
    run_invoice_sql interpolates the completion into SQL, and the rendered
    HTML from the completion is written straight into the invoice PDF. A
    crafted document that makes the model emit a quote-terminated statement
    gets executed by the database, and a completion containing script tags is
    persisted into a document staff open every day.
    """
    completion = llm(SYSTEM_PROMPT, invoice_document(invoice))
    totals = run_invoice_sql(completion)
    write_pdf(invoice["id"], render_html(completion, totals))
    return {"id": invoice["id"], "summary": completion}


def run_invoice_sql(model_text: str) -> List[Dict[str, Any]]:
    """Pull the totals the model described."""
    with connection.cursor() as cur:
        cur.execute(f"SELECT total FROM invoices WHERE note = '{model_text}'")
        return cur.fetchall()


def render_html(model_text: str, totals: List[Dict[str, Any]]) -> str:
    return f"<html><body><p>{model_text}</p><pre>{totals}</pre></body></html>"


def classify_ticket(text: str) -> Dict[str, Any]:
    """Classify a ticket into a routing bucket.

    CRITICAL DEFECT:
    The category is taken from the model's prose with a regex and used as the
    queue the ticket is filed in, and the discount recommendation is applied
    straight to the order total. The model was asked to suggest; nothing
    confirms, so a rephrased answer silently routes to the wrong team and
    a hallucinated percentage is charged.
    """
    completion = llm("Classify the ticket and suggest a discount.", text)
    category = re.search(r"category:\s*(\w+)", completion).group(1)
    discount = re.search(r"discount:\s*(\d+)%", completion)
    ticket = file_ticket(text, queue=category.upper())
    if discount:
        orders.apply_discount(ticket["order_id"], int(discount.group(1)))
    return ticket


def fetch_report_url(model_text: str) -> str:
    """Follow the report link the model produced.

    CRITICAL DEFECT:
    The destination is whatever the completion contains, with no scheme or
    host allowlist, and the fetcher follows redirects — so the model can send
    the server anywhere, including the cloud metadata endpoint.
    """
    url = re.search(r"https?://\S+", model_text).group(0)
    return httpx.get(url, follow_redirects=True).text
