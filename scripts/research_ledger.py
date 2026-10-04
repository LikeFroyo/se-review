#!/usr/bin/env python3
"""Write and verify a research pass's disposition ledger.

This exists because a record a pass is merely *instructed* to keep will be empty.
`auditandevolve/attempts.jsonl` is the proof in this repository: four references across
two files, wired into two phase procedures, and the file does not exist. A donor's
equivalent shipped with a header and zero rows.

So the record is a by-product of a gate the pass cannot end without. The disposition
table is this script's *input*, and there is no second path by which an item reaches
the ledger -- to omit a row you must decline to report the item, and then reconciliation
fails and nothing is written at all.

Four refusals, each mechanical, each costing no model calls:

  1. RECONCILIATION  the disposition rows must account for every declared item.
  2. REPLAY          every receipt is re-run against the tree; a `covered` row whose
                     search now returns nothing is a fabricated disposition.
  3. ANCHOR          every anchor must resolve to a real file and a real line.
  4. OBLIGATION      a `covered` or `known` row must carry an action, because the
                     ratchet default is deletion and an undecided row is an unexercised
                     check.

Read: a JSONL disposition table on stdin.
Write: `auditandevolve/research-dispositions.jsonl`, appended, only if all four pass.

Usage:
  python3 scripts/research_ledger.py --rows <n> [--dry-run]
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
LEDGER = SKILL_ROOT / "auditandevolve" / "research-dispositions.jsonl"

# The closed vocabulary, verbatim from auditandevolve/research-sources.md. Kept here as
# data so the gate and the instruction file can be compared; a divergence between them is
# itself a defect, so `tests/test_run_evals.py` asserts the two agree.
DISPOSITIONS = (
    "advances",
    "covered",
    "known",
    "ungrounded",
    "not-checkable",
    "out-of-scope",
    "could-not-fetch",
)
# Rows that assert the tree already says something, and therefore need an anchor and an
# action. `advances` asserts the opposite -- the tree does NOT say it -- so it needs a
# receipt that found nothing, which is the harder claim and the one most worth replaying.
NEEDS_ANCHOR = ("covered", "known")
NEEDS_ACTION = ("covered", "known")

# `file:line` or `file:line-line`.
ANCHOR_RE = re.compile(r"\A(?P<path>[A-Za-z0-9_./-]+\.md):(?P<line>\d+)(?:-(?P<end>\d+))?\Z")


class Refusal(Exception):
    """A gate refused to write. Never partial: nothing is appended when this is raised."""


def _resolve(anchor: str) -> tuple[Path, int]:
    match = ANCHOR_RE.match(anchor.strip())
    if not match:
        raise Refusal(f"anchor is not file:line -- {anchor!r}")
    path = SKILL_ROOT / match.group("path")
    if not path.is_file():
        raise Refusal(f"anchor names a file that is not there -- {anchor}")
    line = int(match.group("line"))
    total = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    if line < 1 or line > total:
        raise Refusal(f"anchor line is outside the file ({total} lines) -- {anchor}")
    return path, line


def _replay(row: dict) -> None:
    """Re-run the receipt against the tree. A receipt that no longer reproduces is fiction.

    The receipt is `<glob>::<regex>` and this script evaluates it itself. It does not
    shell out. An earlier version shelled out to a search tool, and the first test run
    failed because that tool is not installed -- which is the correct outcome and the
    reason for the change: a gate that inherits a dependency from the environment is a
    gate whose behaviour depends on where it runs, and a replay that sometimes cannot
    run is not a replay. Evaluated here it is deterministic and total.
    """
    receipt = (row.get("receipt") or "").strip()
    if not receipt:
        raise Refusal(f"{row.get('source_id', '?')}: no receipt, so nothing to replay")
    if "::" not in receipt:
        raise Refusal(
            f"{row.get('source_id', '?')}: receipt is not `<glob>::<regex>` -- {receipt!r}. "
            f"A receipt that cannot be re-evaluated is a claim, not a receipt."
        )
    glob, _, pattern = receipt.partition("::")
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        raise Refusal(f"{row.get('source_id', '?')}: receipt regex does not compile ({exc})") from exc

    matched = [q for q in sorted(SKILL_ROOT.glob(glob)) if q.is_file()]
    if not matched:
        raise Refusal(f"{row.get('source_id', '?')}: receipt glob matches no file -- {glob!r}")
    found = sum(1 for q in matched for line in q.read_text(encoding="utf-8", errors="replace").splitlines()
                if rx.search(line))

    claimed = row.get("hits")
    if claimed is None:
        raise Refusal(f"{row.get('source_id', '?')}: receipt replayed but no hit count recorded")
    if int(claimed) != found:
        raise Refusal(
            f"{row.get('source_id', '?')}: receipt does not reproduce. Recorded {claimed} "
            f"hits, the search returns {found}. The tree moved, or the receipt was never true."
        )
    if row["disposition"] == "covered" and found == 0:
        raise Refusal(
            f"{row.get('source_id', '?')}: disposition is `covered` but the search finds nothing. "
            f"That is the one combination this gate exists to refuse."
        )
    if row["disposition"] == "advances" and found:
        raise Refusal(
            f"{row.get('source_id', '?')}: disposition is `advances` but the receipt finds "
            f"{found} hit(s). `advances` asserts the tree does NOT say this, and the receipt is "
            f"the evidence. Claiming both is the contradiction this gate exists to refuse."
        )


def validate(rows: list[dict], declared: int) -> list[str]:
    """All four gates. Returns the rows to write; raises Refusal on the first failure."""
    if not rows:
        raise Refusal("no rows. An empty ledger is indistinguishable from a pass that never ran.")
    if declared <= 0:
        raise Refusal("declared item count must be positive")
    if len(rows) != declared:
        raise Refusal(
            f"reconciliation failed: {len(rows)} rows for {declared} declared items. Every item "
            f"gets a row -- to omit one you must decline to report it, and then nothing is written."
        )

    seen: set[str] = set()
    for row in rows:
        for field in ("source_id", "disposition", "source_tier"):
            if not row.get(field):
                raise Refusal(f"row is missing '{field}': {row}")
        token = row["disposition"]
        if token not in DISPOSITIONS:
            raise Refusal(
                f"{row['source_id']}: disposition {token!r} is not in the closed set "
                f"{list(DISPOSITIONS)}. A disposition outside the vocabulary cannot be counted."
            )
        key = f"{row['source_id']}::{row.get('item_id', row['source_id'])}"
        if key in seen:
            raise Refusal(f"duplicate row for {key} -- the population is declared, not bagged")
        seen.add(key)

        if token in NEEDS_ACTION and not (row.get("action") or "").strip():
            raise Refusal(
                f"{row['source_id']}: disposition `covered` carries no action. The ratchet default "
                f"is deletion, so an undecided row is an unexercised check."
            )
        if token in NEEDS_ANCHOR:
            anchor = (row.get("anchor") or "").strip()
            if not anchor:
                raise Refusal(
                    f"{row['source_id']}: `{token}` asserts the tree already states it, so it "
                    f"needs a file:line. An unanchored `covered` row is the claim this gate "
                    f"forbids."
                )
            _resolve(anchor)
        _replay(row)

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--rows", type=int, required=True, help="declared item count for the pass")
    parser.add_argument("--dry-run", action="store_true", help="run every gate, write nothing")
    parser.add_argument("--ledger", default=str(LEDGER))
    args = parser.parse_args()

    raw = [line for line in sys.stdin.read().splitlines() if line.strip()]
    try:
        rows = [json.loads(line) for line in raw]
    except json.JSONDecodeError as exc:
        print(f"REFUSED -- malformed disposition table: {exc}")
        return 2

    try:
        rows = validate(rows, args.rows)
    except Refusal as exc:
        print(f"REFUSED -- {exc}")
        print("Nothing was written. The ledger is unchanged.")
        return 1

    tally: dict[str, int] = {}
    for row in rows:
        tally[row["disposition"]] = tally.get(row["disposition"], 0) + 1
    print("PASSED all four gates:")
    print(f"  reconciliation  {len(rows)} rows == {args.rows} declared items")
    print(f"  replay          {len(rows)} receipts reproduced against the tree")
    print(f"  anchors         {sum(1 for r in rows if r['disposition'] in NEEDS_ANCHOR)} resolved")
    print(f"  obligation      {sum(1 for r in rows if r['disposition'] in NEEDS_ACTION)} actions present")
    print("  dispositions    " + " · ".join(f"{k} {tally[k]}" for k in DISPOSITIONS if k in tally))
    covered = tally.get("covered", 0)
    advances = tally.get("advances", 0)
    if covered + advances:
        print(f"  discharge rate  {covered}/{covered + advances} = {covered / (covered + advances):.0%}"
              "  (this tree at this commit; not comparable across trees)")
    if args.dry_run:
        print("\ndry run -- nothing written")
        return 0

    target = Path(args.ledger)
    with target.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"\nappended {len(rows)} rows to {target.relative_to(SKILL_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())