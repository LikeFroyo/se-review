#!/usr/bin/env python3
"""Freeze the file that judges a pass, for the duration of that pass.

`auditandevolve/SKILL.md` made `hillclimb.md` read-only while Phase 5 runs, because
that file holds the keep/revert table and the noise gate -- the procedure that decides
whether this round's patch is kept. "A round that rewrote the procedure judging it keeps
itself, and the edits that do the most damage are the ones that look like tidying."

One rule per phase does not generalise. The general rule is: **a pass may not edit any
file it read.** Every phase file is read by the phase it defines, and the gate file is
the one whose edit would be self-certifying, so this script makes that mechanical rather
than stated:

    python3 scripts/pass_freeze.py begin <phase>
    ... the pass runs ...
    python3 scripts/pass_freeze.py verify

`begin` snapshots the blob hash of the phase's own instruction file plus the orchestrator.
`verify` recomputes them and refuses if any moved. A file that is not a gate is
unaffected, so a pass may still do its actual work.

Zero model calls. Deterministic. No maintained list beyond the phase->gate table below,
and that table is data so it can be compared against the instruction files by test.

Usage:
  python3 scripts/pass_freeze.py begin <phase>
  python3 scripts/pass_freeze.py verify
  python3 scripts/pass_freeze.py status
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
FREEZE = SKILL_ROOT / "auditandevolve" / ".pass-freeze.json"

# phase -> the files that decide what that phase may do.
#
# Every phase file is its own gate, which is the general rule stated as a table: a file
# cannot be edited by the pass whose procedure it states. The orchestrator is in every
# set because it carries the measurement boundary, which is the rule that forbids the
# edits this script exists to catch.
PHASE_GATES: dict[int, tuple[str, ...]] = {
    1: ("auditandevolve/deep-research.md", "auditandevolve/SKILL.md"),
    2: ("auditandevolve/deep-upsert.md", "auditandevolve/SKILL.md"),
    3: ("auditandevolve/skill-adherence.md", "auditandevolve/SKILL.md"),
    4: ("auditandevolve/eval-design.md", "auditandevolve/eval-harness.md", "auditandevolve/SKILL.md"),
    5: ("auditandevolve/hillclimb.md", "auditandevolve/SKILL.md"),
    # A pass with no phase of its own: the research class, and the self-evolution pass.
    0: ("auditandevolve/research-sources.md", "auditandevolve/SKILL.md"),
}


def _blob(rel: str) -> str | None:
    """Content hash of a tracked path, or None if it is not there."""
    proc = subprocess.run(
        ["git", "hash-object", str(SKILL_ROOT / rel)],
        cwd=SKILL_ROOT, capture_output=True, text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None


def begin(phase: int) -> int:
    if phase not in PHASE_GATES:
        print(f"REFUSED -- no gate table for phase {phase}. Known: {sorted(PHASE_GATES)}")
        return 2
    if FREEZE.exists():
        print(f"REFUSED -- a freeze is already open at {FREEZE.relative_to(SKILL_ROOT)}.")
        print("           Run `verify` first. Two open freezes means one pass's gate could be")
        print("           edited while another pass claimed it.")
        return 1
    snapshot = {rel: _blob(rel) for rel in PHASE_GATES[phase]}
    missing = [rel for rel, digest in snapshot.items() if digest is None]
    if missing:
        print(f"REFUSED -- gate file(s) missing from the tree: {missing}")
        return 2
    FREEZE.write_text(json.dumps({"phase": phase, "hashes": snapshot}, indent=2) + "\n",
                      encoding="utf-8")
    print(f"froze phase {phase}: {len(snapshot)} file(s)")
    for rel, digest in snapshot.items():
        print(f"  {digest[:12]}  {rel}")
    return 0


def verify() -> int:
    if not FREEZE.exists():
        print("REFUSED -- no freeze is open, so there is nothing to verify.")
        print("           A pass that runs without `begin` has an unjudged gate.")
        return 1
    state = json.loads(FREEZE.read_text(encoding="utf-8"))
    moved = []
    for rel, was in state["hashes"].items():
        now = _blob(rel)
        if now != was:
            moved.append(rel)
    if moved:
        print(f"REFUSED -- phase {state['phase']} edited the file that judges it:")
        for rel in moved:
            print(f"  {rel}")
        print("Nothing about this pass can be self-certified. Revert, or re-open the gate")
        print("deliberately with a new phase and a named reason.")
        return 1
    FREEZE.unlink()
    print(f"verified: phase {state['phase']} left all {len(state['hashes'])} gate file(s) intact")
    return 0


def status() -> int:
    if not FREEZE.exists():
        print("no freeze open")
        return 0
    state = json.loads(FREEZE.read_text(encoding="utf-8"))
    print(f"phase {state['phase']} frozen on {len(state['hashes'])} file(s)")
    return 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        raise SystemExit(2)
    action = argv[0]
    if action == "begin":
        raise SystemExit(begin(int(argv[1]) if len(argv) > 1 else -1))
    if action == "verify":
        raise SystemExit(verify())
    if action == "status":
        raise SystemExit(status())
    print(__doc__)
    raise SystemExit(2)
