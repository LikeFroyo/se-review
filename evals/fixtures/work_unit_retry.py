"""Batch ledger — one unit of work, retried after a crash."""
import json


def apply_entry(store_path: str, entry: dict) -> None:
    """Append one entry to the ledger file."""
    with open(store_path, "r+") as fh:
        lines = fh.readlines()
        lines.append(json.dumps(entry) + "\n")
        fh.seek(0)
        fh.truncate()
        fh.writelines(lines)


def run_batch(store_path: str, entries: list, failed_index: int) -> None:
    """Process every entry; retrying re-runs the whole batch from the start."""
    for index, entry in enumerate(entries):
        apply_entry(store_path, entry)
        if index == failed_index:
            raise RuntimeError("transient failure mid-batch")
