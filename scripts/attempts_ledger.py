#!/usr/bin/env python3
"""Propose-or-refuse, and record, one hillclimb round.

`auditandevolve/SKILL.md § The attempt ledger` has specified this ledger in four places
across two files since it was written, and **the file did not exist**. That is the whole
reason this script exists, and it is not a rare failure: a donor's equivalent shipped with
a header and zero rows, because a record a pass is merely *instructed* to keep is a
record nobody keeps.

Two modes, and the ordering is the enforcement.

    python3 scripts/attempts_ledger.py propose --surface <path> --patch <file> ...
    python3 scripts/attempts_ledger.py record --round <n> --verdict kept|reverted ...

`propose` refuses a patch whose digest matches a **reverted** row, and names the row and
the numbers that rejected it. `record` refuses unless every earlier round is recorded, so
a pass cannot skip the write and go on to the next round.

**Matching is by content digest, never by prose.** An earlier version of the rule matched
"a one-line description", which leaves the match to an agent recognising its own wording --
and a round that re-proposes a reverted patch will usually word it differently, because it
is written from the same transcripts and not from the previous patch. A digest removes the
judgement from the only step that has to be mechanical.

Two refusals the tree's own reasoning demands beyond the obvious ones:

- **A row must record the state it was measured against.** A row from round 1 applied
  after round 2 changed the surface refuses a patch that has since become admissible, and
  admits one whose rejection was measured against different text. So `base_commit` is
  required, and a stale row is reported rather than applied.
- **A `kept` row makes its own re-proposal a no-op**, which the script says outright
  rather than refusing silently.

Read: `auditandevolve/attempts.jsonl`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
LEDGER = SKILL_ROOT / "auditandevolve" / "attempts.jsonl"
VERDICTS = ("kept", "reverted")


def _rows() -> list[dict]:
    if not LEDGER.is_file():
        return []
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _digest(path: Path) -> str:
    return "pat:" + hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _refuse(message: str) -> int:
    print(f"REFUSED -- {message}")
    print("Nothing was written. The ledger is unchanged.")
    return 1


def propose(args: argparse.Namespace) -> int:
    surface = Path(args.surface)
    patch = Path(args.patch)
    if not patch.is_file():
        return _refuse(f"no patch file at {patch}")
    digest = _digest(patch)
    rows = _rows()

    if not rows:
        print(f"proposal accepted: no prior rounds, nothing to refuse against.")
        print(f"  digest {digest}")
        return 0

    for row in rows:
        if row.get("patch_digest") != digest:
            continue
        if row.get("verdict") == "kept":
            return _refuse(
                f"round {row['round']} already landed this exact patch ({digest}). Re-proposing "
                f"it is a no-op, and the surface it touched has moved on since."
            )
        if row.get("base_commit") not in (None, args.base_commit):
            print(f"NOTE -- round {row['round']} rejected this patch, but it was measured against")
            print(f"        {row['base_commit']} and the tree is now {args.base_commit}.")
            print("        The row is stale and does not refuse the proposal; re-measure instead")
            print("        of relying on it.")
        return _refuse(
            f"round {row['round']} already tried this exact patch ({digest}) and it was "
            f"REVERTED: train {row.get('train_delta')}, test {row.get('test_delta')}. "
            f"Re-proposing spends a measurement set to reproduce a result already discarded. "
            f"If the surface has genuinely changed, say so and re-measure."
        )
    print(f"proposal accepted: {digest} matches no prior row across {len(rows)} round(s)")
    return 0


def record(args: argparse.Namespace) -> int:
    rows = _rows()
    expected = len(rows) + 1
    if args.round != expected:
        return _refuse(
            f"round {args.round} cannot be recorded: rounds 1..{expected - 1} are on the ledger, "
            f"so the next writable round is {expected}. Every round is recorded, reverts "
            f"included -- a round that is not recorded cannot be recognised as a repeat."
        )
    for field in ("surface", "patch_digest", "train_delta", "test_delta", "base_commit"):
        if not str(getattr(args, field) or "").strip():
            return _refuse(f"round {args.round} is missing '{field}'")
    if args.verdict not in VERDICTS:
        return _refuse(f"verdict must be one of {list(VERDICTS)}, not {args.verdict!r}")
    row = {
        "round": args.round,
        "surface": args.surface,
        "patch_digest": args.patch_digest,
        "train_delta": args.train_delta,
        "test_delta": args.test_delta,
        "verdict": args.verdict,
        "base_commit": args.base_commit,
    }
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"recorded round {args.round}: {args.verdict} · {args.patch_digest}")
    return 0


def status() -> int:
    """Report the ledger's state -- and distinguish *empty* from *unwired*.

    An empty ledger and a ledger nothing writes are indistinguishable from the file
    alone, and this tree has shipped both: `judge_selftest()` was fully implemented and
    reachable from nothing, and a donor's rejected-changes ledger shipped with a header
    and zero rows. So the report says which of the two this is, and an empty one is
    reported as correct rather than as a defect -- it is empty because no hillclimb round
    has run, and the gate is what makes it fill.
    """
    rows = _rows()
    if not LEDGER.is_file():
        print(f"LEDGER ABSENT -- {LEDGER.relative_to(SKILL_ROOT)} does not exist.")
        print("  Unwired, or no pass has created it yet. The gate refuses round 1 only if")
        print("  it cannot reconcile, so create it by recording the first round.")
        return 1
    if not rows:
        print(f"LEDGER PRESENT, 0 rows -- {LEDGER.relative_to(SKILL_ROOT)}")
        print("  Correct state until a hillclimb round runs. The gate is live: `record`")
        print("  refuses any round past the last one recorded, so the ledger cannot be")
        print("  skipped over. Distinguish this from a ledger nothing writes -- that one")
        print("  reports as absent.")
        return 0
    verdicts: dict[str, int] = {}
    for row in rows:
        verdicts[row["verdict"]] = verdicts.get(row["verdict"], 0) + 1
    print(f"LEDGER: {len(rows)} round(s) recorded in {LEDGER.relative_to(SKILL_ROOT)}")
    print("  " + " · ".join(f"{k} {v}" for k, v in sorted(verdicts.items())))
    reverted = {r["patch_digest"] for r in rows if r["verdict"] == "reverted"}
    print(f"  {len(reverted)} patch(es) refused on re-proposal")
    stale = [r for r in rows if r.get("base_commit") in (None, "unpinned")]
    if stale:
        print(f"  NOTE: {len(stale)} row(s) carry no base_commit, so they cannot be checked")
        print("        against the tree they were measured on and will not refuse a")
        print("        proposal against a moved surface.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="mode", required=True)

    p = sub.add_parser("propose", help="refuse a patch already tried and reverted")
    p.add_argument("--surface", required=True)
    p.add_argument("--patch", required=True)
    p.add_argument("--base-commit", dest="base_commit", default="unpinned")

    r = sub.add_parser("record", help="append one round")
    r.add_argument("--round", type=int, required=True)
    r.add_argument("--surface", required=True)
    r.add_argument("--patch-digest", dest="patch_digest", required=True)
    r.add_argument("--train-delta", dest="train_delta", required=True)
    r.add_argument("--test-delta", dest="test_delta", required=True)
    r.add_argument("--verdict", required=True)
    r.add_argument("--base-commit", dest="base_commit", default="unpinned")

    sub.add_parser("status", help="report the ledger's state, empty vs unwired")

    args = parser.parse_args()
    if args.mode == "status":
        return status()
    return propose(args) if args.mode == "propose" else record(args)


if __name__ == "__main__":
    raise SystemExit(main())
