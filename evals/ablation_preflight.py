"""Pre-flight: can the grader reproduce its own verdict?

The suppression ablation proves or kills `project-tree/shared/deliberate.md`, and
its kill criterion is a 40-point difference in false-positive rate between two
arms. That criterion is only interpretable if the grader is reproducible: the
same review, graded twice, must score the same. Otherwise a 40-point spread is
inside the noise and the experiment cannot return a verdict in either direction.

So before spending ~120 calls on the ablation, replay reviews that **already have
a recorded verdict** and check the grader reproduces it:

- **oracle** — a stored review whose recorded score was 100%. The grader must
  return 100% again. Anything less means the grader is not reproducible against
  its own recorded output, which is a determinism defect, not a gate defect.
- **mismatch** — a stored review from a *different* eval, graded against this
  eval's assertions. It satisfies nothing by construction, so it must score near
  zero. A high score means the grader is pattern-matching on fluency rather than
  reading the review, which would inflate every arm equally and hide a real gate
  effect.

Two grader calls per panel. No reviewer call, no workspace, no fixture, no
replicate — the reviews are already on disk.

An earlier version of this preflight built its own oracle by restating each
assertion as a satisfied finding. That was wrong, and the result was a false alarm
on the grader: these assertions are behavioural ("evidence identifies the bare
except clause"), and no review can satisfy one by asserting it in prose. A
known-good reference has to be a review that genuinely scored well.

Usage:  python3 evals/ablation_preflight.py [--panels 4] [--model <id>]
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import run_evals as R  # noqa: E402
from eval_registry import eval_name  # noqa: E402

# Panels with a recorded 100% review on disk, plus a large non-ablation review as
# the mismatch body. Both shapes: an ablation panel and an ordinary one.
PANELS = (83, 43, 48, 39)
# A review of genuinely other code. Must NOT be any panel's own review: scoring a
# panel's stored review against that panel is the oracle test again, not a mismatch
# test, and reporting it as a mismatch makes a self-inconsistency look like a finding.
MISMATCH_FROM = "eval-weak-password-hash"
MISMATCH_NAME = "eval-weak-password-hash"
assert MISMATCH_NAME not in {eval_name(p) for p in PANELS}, \
    "the mismatch body must not also be a panel"


def stored(name: str) -> tuple[str, dict]:
    d = REPO / "evals/iteration-1" / name / "with_skill"
    return (d / "review.md").read_text(), json.loads((d / "grading.json").read_text())


def score(review: str, assertions: list[str], model: str | None, keep: Path) -> float | None:
    try:
        verdicts = R.grade(review, assertions, 240, Path(tempfile.mkdtemp()), model, keep)
    except Exception as exc:  # transport, quota, unparseable -- never a score
        print(f"        not run: {str(exc)[:100]}")
        return None
    return 100.0 * sum(1 for v in verdicts if v["passed"]) / len(verdicts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panels", type=int, default=len(PANELS))
    ap.add_argument("--model", default=None)
    ap.add_argument("--iter", default="iteration-1")
    args = ap.parse_args()

    corpus = {e["id"]: e for e in json.loads((REPO / "evals/evals.json").read_text())["evals"]}
    mismatch_review, _ = stored(MISMATCH_FROM)
    keep = REPO / "evals" / args.iter / "preflight_judge_replies"
    keep.mkdir(parents=True, exist_ok=True)

    print(f"grader determinism pre-flight · model={args.model or '(unpinned)'}\n")
    rows = []
    for eid in list(PANELS)[: args.panels]:
        name = eval_name(eid)
        try:
            review, recorded = stored(name)
        except FileNotFoundError:
            print(f"  panel {eid:<3} skipped: no stored review")
            continue
        assertions = corpus[eid]["assertions"]
        rec = 100.0 * recorded["summary"]["passed"] / recorded["summary"]["total"]
        rep = score(review, assertions, args.model, keep / f"oracle-{eid}")
        mis = score(mismatch_review, assertions, args.model, keep / f"mismatch-{eid}")
        rows.append({"panel": eid, "recorded": rec, "replay": rep, "mismatch": mis})
        r = "n/a" if rep is None else f"{rep:5.1f}%"
        m = "n/a" if mis is None else f"{mis:5.1f}%"
        print(f"  panel {eid:<3} recorded {rec:5.1f}%   replay {r}   drift "
              f"{'n/a' if rep is None else f'{rep - rec:+5.1f}'}   mismatch {m}")

    scored = [r for r in rows if r["replay"] is not None and r["mismatch"] is not None]
    print()
    if not scored:
        print("VERDICT: NOT RUN — the grader could not be reached. Not the same as the grader")
        print("         being defective, and the two must not be reported as one.")
        return 0
    worst_drift = max(abs(r["replay"] - r["recorded"]) for r in scored)
    best_mismatch = max(r["mismatch"] for r in scored)
    span = 100.0 - best_mismatch
    print(f"  worst replay drift : {worst_drift:5.1f} points from the recorded verdict")
    print(f"  best mismatch score: {best_mismatch:5.1f}%  (a review of other code, scored")
    print("                              against these assertions, must land near zero)")
    print(f"  usable span        : {span:5.1f} points")
    print()
    if worst_drift > 10:
        print("VERDICT: GRADER NOT REPRODUCIBLE — a review that scored 100% did not score 100%")
        print("         again. A 40-point kill criterion is inside that drift, so the ablation")
        print("         cannot return a verdict in either direction. Replicates are the fix;")
        print("         this is the replicate gap showing up as a blocked experiment.")
    elif best_mismatch > 20:
        print("VERDICT: GRADER TOO LENIENT — a review of unrelated code scored against these")
        print("         assertions did not fail. It is responding to fluency, not content, and")
        print("         would inflate both arms of the ablation equally.")
    elif span < 45:
        print("VERDICT: SPAN TOO NARROW — the grader cannot separate a right review from a wrong")
        print("         one by the 40 points the kill criterion requires.")
    else:
        print("VERDICT: GRADER USABLE — reproducible against its own recorded verdicts, and it")
        print("         can separate a satisfying review from an unrelated one. The ablation is")
        print("         worth running.")

    out = REPO / "evals" / args.iter / "ablation_preflight.json"
    out.write_text(json.dumps(
        {"model": args.model, "rows": rows, "worst_drift": worst_drift,
         "best_mismatch": best_mismatch, "span": span}, indent=2) + "\n")
    print(f"\n  written to {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())