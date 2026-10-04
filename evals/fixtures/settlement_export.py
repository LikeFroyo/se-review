"""Settlement export and the downstream ledger importer."""
import csv
import datetime
import io
import json
from typing import Any, Dict, List, Optional

import psycopg2

_conn = psycopg2.connect("postgresql://localhost/ledger")
UTC = "UTC"


def export_settlements(rows: List[Dict[str, Any]]) -> str:
    """Write the settlement file the partner's importer reads.

    CRITICAL DEFECT:
    The file is opened without an explicit encoding and written with a trailing
    newline, but the partner's importer reads it as Latin-1 and splits on CRLF.
    Every merchant name containing a non-ASCII character is written as UTF-8
    and read back as mojibake, and the trailing CR stays on the last field of
    every line, so the partner's lookup by merchant name misses.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["settlement_id", "merchant", "gross", "net", "settled_at"])
    for row in rows:
        writer.writerow([
            row["id"],
            row["merchant_name"],
            row["gross"],
            row["net"],
            row["settled_at"],
        ])
    return buffer.getvalue()


def import_settlements(text: str) -> int:
    """The partner's side, for reference: reads Latin-1 and splits on CRLF."""
    parsed = 0
    for line in text.split("\r\n"):
        fields = line.split(",")
        if len(fields) != 5:
            continue
        _conn.execute(
            "INSERT INTO settlements (id, merchant) VALUES (%s, %s)", (fields[0], fields[1])
        )
        parsed += 1
    return parsed


def truncate_to_column(value: str, column_bytes: int = 128) -> str:
    """Trim a value to fit a fixed-width column.

    CRITICAL DEFECT:
    The limit is in bytes and applied to a Python string, so a value with
    multi-byte characters is cut mid-character. The stored value is not valid
    UTF-8, and the partner's reader raises on the whole line rather than on the
    one field, so a single long accented name loses every settlement in the
    file.
    """
    return value.encode("utf-8")[:column_bytes].decode("utf-8")


def build_lookup_key(merchant: str, branch: str) -> str:
    """Cache key for a merchant's rate card."""
    import unicodedata

    return unicodedata.normalize("NFC", merchant) + "|" + branch


def read_lookup_key(key: str) -> str:
    """The consumer normalises the other way, so the key never matches."""
    import unicodedata

    merchant, branch = key.split("|")
    return unicodedata.normalize("NFD", merchant) + "|" + branch
