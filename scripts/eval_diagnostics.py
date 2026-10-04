"""Eval design diagnostics: headroom, trigger rate, task tells, grader determinism.

These are the checks that decide whether an eval can measure anything at all. A
saturated corpus or a grader that flips on identical output turns every reported
delta into noise, and a corpus whose tasks are broken rewards the wrong behaviour.

  headroom      with_skill pass rate; >= 95% means quality hillclimbing is impossible
  trigger rate  share of rollouts that actually opened the skill, from tool calls
  task tells    evals pinned at 0% (broken task) or 100% (no headroom)
  determinism   optional; re-grades stored reviews and reports the verdict flip rate

Usage:
  python scripts/eval_diagnostics.py
  python scripts/eval_diagnostics.py --determinism 5
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
ITERATION = SKILL_ROOT / "evals" / "iteration-1"
SATURATION_THRESHOLD = 0.95
# The suppression gate is judged on the delta it produces, not on the score it
# reaches. At this corpus size the smallest delta resolvable at p<0.05 is well
# below this, so a gate below the bar is a gate inside the noise.
KILL_DELTA = 0.40
SKILL_MARKERS = ("SKILL.md", "leaf.md", "shared/")


def looks_like_report(review: str) -> bool:
    """Same test the runner uses, so the two never disagree about a usable review."""
    if "## Findings" in review or "### [CRITICAL]" in review or "### [MAJOR]" in review:
        return True
    return bool(re.search(r"\bfindings\b.*\bC:\d+", review, re.S))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def headroom() -> tuple[float, int, int, bool]:
    path = ITERATION / "benchmark.json"
    if not path.is_file():
        raise SystemExit("no benchmark.json - run grade_evals.py first")
    summary = load_json(path)["run_summary"]["with_skill"]
    total, passed = summary["total_assertions"], summary["total_passed"]
    rate = passed / total if total else 0.0
    return rate, passed, total, rate >= SATURATION_THRESHOLD


def trigger_rate() -> tuple[float, int, int, list[str]]:
    """Share of rollouts that read the skill, judged from tool-call inputs only.

    Matching the path anywhere in the event stream would count the prompt echoing
    the skill's name, which is not evidence the model opened it.
    """
    consulted = total = 0
    missed: list[str] = []
    for events in sorted(glob.glob(str(ITERATION / "eval-*" / "with_skill" / "events.jsonl"))):
        reads: list[str] = []
        for line in Path(events).read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "tool_use":
                continue
            state = event.get("part", {}).get("state", {}) or {}
            inputs = state.get("input", {}) or {}
            for key in ("filePath", "path", "pattern"):
                if isinstance(inputs.get(key), str):
                    reads.append(inputs[key])
        if not reads:
            continue
        total += 1
        name = Path(events).parent.parent.name
        if any(marker in p.replace("\\", "/") for p in reads for marker in SKILL_MARKERS):
            consulted += 1
        else:
            missed.append(name)
    return (consulted / total if total else 0.0), consulted, total, missed


def task_tells() -> tuple[list[str], list[str], list[tuple[str, float]], list[str]]:
    """Split evals by where they sit, separating broken tasks from broken runs.

    An eval pinned at 0% is only a broken task if the rollout actually produced a
    review. A run cut short by a denied tool leaves a stub review and a recorded
    zero, and that is infrastructure noise, not evidence about the task.
    """
    zero: list[str] = []
    full: list[str] = []
    mid: list[tuple[str, float]] = []
    ungraded: list[str] = []
    for path in sorted(glob.glob(str(ITERATION / "eval-*" / "with_skill" / "grading.json"))):
        directory = Path(path).parent
        try:
            summary = load_json(Path(path)).get("summary", {})
        except json.JSONDecodeError:
            continue
        total = summary.get("total") or 0
        if not total:
            continue
        name = directory.parent.name
        review_path = directory / "review.md"
        plumbing_path = directory / "plumbing.json"
        review = ""
        if review_path.is_file():
            review = review_path.read_text(encoding="utf-8", errors="replace")
        if plumbing_path.is_file() or not review or not looks_like_report(review):
            ungraded.append(name)
            continue
        rate = summary["passed"] / total
        if rate == 0.0:
            zero.append(name)
        elif rate == 1.0:
            full.append(name)
        else:
            mid.append((name, rate))
    return zero, full, mid, ungraded


def replicate_spread() -> dict:
    """Within-eval standard deviation across replicates, per arm.

    This is the quantity hillclimb.md asks for before round one: how far a
    score moves by chance alone. It needs more than one replicate per eval to
    exist at all, so a corpus run once per arm has none and cannot gate a delta.

    Restricted to verdicts that still match the corpus. Without that filter this reported
    0.156 over 11 evals while the derived block in grade_evals.py reported 0.124 over 10
    from the same files -- two figures for one quantity, differing only in whether the
    inadmissible eval was counted, which is the failure mode this repository keeps meeting.
    A noise floor is only useful if every reader gets the same one.
    """
    corpus = {}
    try:
        corpus = {e["id"]: e.get("assertions", []) for e in
                  load_json(SKILL_ROOT / "evals" / "evals.json")["evals"]}
    except Exception:
        corpus = {}
    out = {}
    for arm in ("with_skill", "without_skill", "nosuppress"):
        sds, worst, worst_eval = [], 0.0, ""
        for path in sorted(glob.glob(str(ITERATION / "eval-*" / arm / "grading.json"))):
            try:
                grading = load_json(Path(path))
            except json.JSONDecodeError:
                continue
            if corpus:
                eid = grading.get("eval_id")
                recorded = [r.get("text", "") for r in grading.get("assertion_results", [])]
                if "assertion_results" not in grading or recorded != corpus.get(eid):
                    continue
            summary = grading.get("replicate_summary") or {}
            sd = summary.get("stdev_pass_rate")
            if sd is None or summary.get("n", 0) < 2:
                continue
            sds.append(sd)
            if sd > worst:
                worst, worst_eval = sd, grading.get("eval_name", Path(path).parent.parent.name)
        if sds:
            out[arm] = {
                "evals": len(sds),
                "mean_sd": sum(sds) / len(sds),
                "worst_sd": worst,
                "worst_eval": worst_eval,
            }
    return out


def verdict_rates() -> dict:
    """Pass rate over verdict-role assertions only, per arm.

    A panel that mixes verdict assertions with probe assertions cannot be read: probe
    assertions measure whether the mechanism ran, not whether the review was right, and
    averaging them lets narration substitute for correctness.

    Three states are kept apart, and the distinction is the whole point of this function:

    `current`      the recorded assertion text matches the corpus, so the score answers the
                   question the corpus currently asks. Admitted.
    `void`         the recorded assertion text disagrees with the corpus. The score answers a
                   question that has since been reworded, so it describes a target that no
                   longer exists. Excluded.
    `unverified`   no `assertion_results` recorded, so nothing about it can be examined.
                   Excluded -- and *not* called void, because "unexamined" and "contradicted"
                   are different facts pointing at different repairs. Re-grading 40 verdicts
                   that were never wrong is what collapsing them invites.

    A fourth, `no_roles`, is not an exclusion but a blindness: the fixture declares no
    assertion_roles, so a verdict-role assertion cannot be told from a probe-role one. Counted
    and named rather than quietly scored as though every assertion were a quality claim.

    Roles come from the corpus, not the verdict. They are a property of the question, so
    requiring the verdict to echo them meant the split stayed unreportable until the corpus
    was re-graded wholesale -- while the block sat under sections that do print.
    """
    corpus = {}
    try:
        corpus = {e["id"]: e for e in
                  load_json(SKILL_ROOT / "evals" / "evals.json")["evals"]}
    except Exception:
        corpus = {}
    out, tally = {}, {"stale": 0, "no_eval_id": 0, "no_roles": 0}
    tally_by_role = {}
    per_eval = {"with_skill": {}, "nosuppress": {}}
    for arm in ("with_skill", "nosuppress"):
        passed = total = probe_passed = probe_total = 0
        for path in sorted(glob.glob(str(ITERATION / "eval-*" / arm / "grading.json"))):
            try:
                grading = load_json(Path(path))
            except json.JSONDecodeError:
                continue
            eid = grading.get("eval_id")
            if eid is None:
                tally["no_eval_id"] += 1
                continue
            results = grading.get("assertion_results")
            if not results:
                tally["no_roles"] += 1
                continue
            entry = corpus.get(eid)
            if entry is not None and [r.get("text", "") for r in results] != entry.get("assertions"):
                tally["stale"] += 1
                continue
            roles = grading.get("assertion_roles") or (entry or {}).get("assertion_roles")
            if not roles or len(roles) != len(results):
                tally["no_roles"] += 1
                continue
            samples = [grading] + [r for r in grading.get("replicates", [])
                                   if "assertion_results" in r]
            # Per file first, then into the arm total. Recording the running accumulator as
            # though it were this file's figure makes every eval's paired entry the sum of
            # every eval before it, so the shared population comes out empty.
            f_passed = f_total = f_probe_passed = f_probe_total = 0
            for sample in samples:
                for role, result in zip(roles, sample.get("assertion_results", [])):
                    if role == "verdict":
                        f_total += 1
                        f_passed += bool(result.get("passed"))
                    elif role == "probe":
                        f_probe_total += 1
                        f_probe_passed += bool(result.get("passed"))
                    else:
                        # `strict` grades the *fix* -- "Fix replaces the price-keyed guard
                        # with an identity-keyed one" -- which is a quality claim about
                        # remediation, not a mechanism check. It was falling through both
                        # branches, so it counted in neither numerator nor denominator: 7
                        # assertions across ids 86-91 were excluded from every rate, with
                        # nothing printed to say so. Dropping them flatters the skill, since
                        # finding a defect and then proposing the wrong repair both score.
                        tally_by_role[role] = tally_by_role.get(role, 0) + 1
                        if role == "strict":
                            f_total += 1
                            f_passed += bool(result.get("passed"))
            passed += f_passed
            total += f_total
            probe_passed += f_probe_passed
            probe_total += f_probe_total
            # Kept per eval so the two arms can be differenced on the *same* fixtures.
            # Aggregating each arm over its own population and subtracting the rates is the
            # defect already fixed once in grade_evals.py, reintroduced here: it reported a
            # +17.4-point ablation delta computed over 594 assertions against 272 -- two
            # different experiments subtracted from each other, with "KILLED" printed
            # underneath. A verdict to cut a gate must not rest on that.
            per_eval[arm][eid] = (f_passed, f_total, f_probe_passed, f_probe_total, len(samples))
        if total:
            out[arm] = {
                "verdict_passed": passed,
                "verdict_total": total,
                "verdict_rate": passed / total,
                "probe_rate": (probe_passed / probe_total) if probe_total else 0.0,
            }

    # The paired figures: only fixtures current in both arms, over one shared population.
    shared = sorted(set(per_eval["with_skill"]) & set(per_eval["nosuppress"]))
    paired = {}
    for arm in ("with_skill", "nosuppress"):
        if not shared:
            paired[arm] = {"verdict_passed": 0, "verdict_total": 0, "verdict_rate": 0.0}
            continue
        pp = sum(per_eval[arm][e][0] for e in shared)
        nn = sum(per_eval[arm][e][1] for e in shared)
        # Sample counts, not just assertion counts. Two arms over the same fixtures can
        # still differ in how many replicates each contributed, so a rate averaged over 22
        # samples is not the same quantity as one averaged over 19. n is carried beside the
        # rate rather than left for a reader to infer from a denominator.
        paired[arm] = {"verdict_passed": pp, "verdict_total": nn,
                       "verdict_rate": (pp / nn) if nn else 0.0,
                       "samples": sum(per_eval[arm][e][4] for e in shared)}
    out["_paired"] = {"evals": len(shared), "ids": shared, **paired}
    out["_excluded"] = tally
    out["_roles"] = tally_by_role
    return out


def find_recoverable(limit: int | None = None) -> tuple[list, list]:
    """Which verdicts lack `assertion_results`, split by whether that is repairable at all.

    Split out from `recover_verdicts` so it can be checked without spending a grading call,
    and so the split is a fact about the corpus rather than something discovered only after
    paying for the re-grades that then fail.
    """
    corpus = {e["id"]: e for e in load_json(SKILL_ROOT / "evals" / "evals.json")["evals"]}
    recoverable, unrecoverable = [], []
    for path in sorted(glob.glob(str(ITERATION / "eval-*" / "with_skill" / "grading.json"))):
        try:
            grading = load_json(Path(path))
        except Exception:
            continue
        if "assertion_results" in grading:
            continue
        name = Path(path).parent.parent.name
        if grading.get("eval_id") is None:
            unrecoverable.append((name, "no eval_id, so no fixture to grade against"))
            continue
        entry = corpus.get(grading["eval_id"])
        if not entry:
            unrecoverable.append((name, "eval_id not in the corpus"))
            continue
        review = Path(path).with_name("review.md")
        if not review.is_file():
            unrecoverable.append((name, "no review body on disk"))
            continue
        recoverable.append((Path(path), review, entry["assertions"], grading))
        if limit and len(recoverable) >= limit:
            break
    return recoverable, unrecoverable


def recover_verdicts(limit: int | None, judge: str | None) -> dict:
    """Supply `assertion_results` for verdicts that recorded a score without the evidence.

    A verdict carrying `summary.pass_rate` but no `assertion_results` is a number with nothing
    behind it: it cannot be checked against the corpus, so it is excluded from every aggregate
    and correctly so. But excluding it is not the same as repairing it, and the two repairs are
    not interchangeable.

    Where a **review body is on disk**, the evidence is recoverable for the price of one
    grading call -- re-grade the stored review against the assertions the corpus asks now, and
    write the per-assertion results. That is a re-grade and is recorded as one, carrying the
    grader digest it ran under, because the stored `summary` came from an earlier grader and
    the two numbers will not necessarily agree.

    Where **no body is on disk** there is nothing to re-grade, and no number of grading calls
    buys anything: the reviewer has to run again. Measured: of 40 verdicts in that state, 4 have
    a body and 36 do not. The cheap half is 4 calls, not 40 -- which is the correction, because
    the natural reading of "no assertion_results recorded" is that the field is missing and can
    be filled in, when in most cases the review it would be filled from is not there.
    """
    import run_evals as R
    from grade_evals import EVAL_NAMES

    import tempfile

    recoverable, unrecoverable = find_recoverable(limit)
    out = {"recoverable": len(recoverable), "unrecoverable": len(unrecoverable),
           "recovered_current": 0, "recovered_void": 0, "failed": 0, "rows": []}
    corpus = {e["id"]: e for e in load_json(SKILL_ROOT / "evals" / "evals.json")["evals"]}
    for path, review, assertions, grading in recoverable:
        try:
            verdicts = R.grade(review.read_text(encoding="utf-8"), assertions, 900,
                               Path(tempfile.mkdtemp()), judge)
        except Exception as exc:  # noqa: BLE001 -- the reason is reported, not swallowed
            out["failed"] += 1
            out["rows"].append({"eval": path.parent.parent.name, "state": "ungradeable",
                                "detail": f"{type(exc).__name__}: {str(exc)[:70]}"})
            continue
        results = [{"text": t, "passed": bool(v.get("passed")),
                    "evidence": str(v.get("evidence", ""))[:200]} for t, v in zip(assertions, verdicts)]
        recorded = [r["text"] for r in results]
        state = "current" if recorded == assertions else "void"
        grading["assertion_results"] = results
        # Looked up from the corpus rather than carried through `find_recoverable`, which
        # returns the assertions and the verdict but not the fixture record. Referencing the
        # name it used to have raised NameError on the first verdict written -- found by
        # stubbing the grader rather than by spending quota on it.
        grading["assertion_roles"] = (corpus.get(grading["eval_id"]) or {}).get("assertion_roles")
        # The summary is rewritten to agree with the evidence, because the aggregate reads
        # `summary` and a file whose two halves disagree has to pick one. Leaving them
        # disagreeing would mean either a special case in the aggregator or a headline
        # number that two fields in the same file contest.
        #
        # The rewrite is recorded rather than silent: `summary_before` keeps what the earlier
        # grader said, so nothing is lost. This is the one place a stored field is overwritten
        # rather than added to, and the reason is that a summary is derived from the results
        # beside it -- a summary that contradicts them is not a second opinion, it is a
        # miscount, and it flattered every verdict it touched.
        prior = dict(grading.get("summary") or {})
        grading["summary"] = {
            "passed": sum(1 for r in results if r["passed"]),
            "failed": sum(1 for r in results if not r["passed"]),
            "total": len(results),
            "pass_rate": round(sum(1 for r in results if r["passed"]) / len(results), 4)
            if results else 0.0,
        }
        grading["recovered"] = {
            "note": "assertion_results and summary supplied by re-grading the stored review "
                    "body; summary_before is what the earlier grader recorded, and it is "
                    "kept because it disagreed",
            "summary_before": prior,
            "grader_config": R.grader_digest(),
        }
        path.write_text(json.dumps(grading, indent=2) + "\n", encoding="utf-8")
        out[f"recovered_{state}"] += 1
        out["rows"].append({"eval": path.parent.parent.name, "state": state,
                            "detail": f"{sum(r['passed'] for r in results)}/{len(results)} passed"})
    out["unrecoverable_detail"] = unrecoverable
    return out


def print_recovered(got: dict) -> None:
    print("\nRECOVERY (supplying the evidence behind scores that recorded none)")
    print(f"  verdicts with a score but no assertion_results: "
          f"{got['recoverable'] + got['unrecoverable']}")
    print(f"  recoverable -- a review body is on disk: {got['recoverable']}")
    for r in got["rows"]:
        print(f"    {str(r['eval'])[:38]:<40} {r['state']:<12} {r['detail']}")
    print(f"  recoverable, now current: {got['recovered_current']}  ·  now void: "
          f"{got['recovered_void']}  ·  ungradeable: {got['failed']}")
    print(f"  NOT recoverable: {got['unrecoverable']}")
    for name, why in (got.get("unrecoverable_detail") or [])[:10]:
        print(f"    {str(name)[:38]:<40} {why}")
    if got["unrecoverable"]:
        print("  These are not a missing field. Each recorded a pass rate with no review body "
              "behind it,")
        print("  so there is nothing to re-grade -- the reviewer has to run again. No count of "
              "grading")
        print("  calls recovers them, and that is the difference between repairing evidence and "
              "regenerating it.")


def determinism(sample: int, judge: str | None = None) -> None:
    """Re-grade stored reviews and report how often the verdict changes.

    Costs one model call per sample. A non-zero flip rate means the grader puts
    its own noise floor above any improvement worth measuring.
    """
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    try:
        import run_evals
    except ImportError:
        print("  cannot import run_evals for the grader; skipping")
        return

    candidates = sorted(
        (Path(p) for p in glob.glob(str(ITERATION / "eval-*" / "with_skill" / "grading.json"))),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    # Filter to what can actually be replayed BEFORE taking the sample. An earlier
    # version sliced first and skipped after, so it announced "replaying 6" and
    # re-graded one: five of the six it picked had no stored review, and the skip lines
    # scrolled past a flip rate computed over a fifth of the requested sample. A count
    # printed beside a much smaller population is the same defect as a denominator that
    # does not name itself.
    replayable = []
    for path in candidates:
        if not (path.parent / "review.md").is_file():
            continue
        stored = load_json(path)
        if stored.get("eval_id") is None:
            continue
        if not any(e["id"] == stored["eval_id"]
                   for e in load_json(SKILL_ROOT / "evals" / "evals.json")["evals"]):
            continue
        replayable.append(path)
    candidates = replayable[:sample]
    if not candidates:
        print("  no stored review on disk can be replayed -- every stored verdict lacks a")
        print("  review body or an eval_id. The determinism check needs both, so there is")
        print("  nothing to measure and no rate is reported.")
        return
    if len(replayable) < sample:
        print(f"  only {len(replayable)} of {sample} requested are replayable; "
              f"the rate below covers those, not the sample size")

    flips = graded = diff_prompt = 0
    current_grader = None
    try:
        import run_evals as _R
        current_grader = _R.grader_digest()
    except Exception:
        pass
    for grading_path in candidates:
        name = grading_path.parent.parent.name
        review_path = grading_path.parent / "review.md"
        stored = load_json(grading_path)
        evals = load_json(SKILL_ROOT / "evals" / "evals.json")["evals"]
        assertions = next((e["assertions"] for e in evals if e["id"] == stored.get("eval_id")), None)
        if not assertions:
            continue
        import tempfile

        try:
            with tempfile.TemporaryDirectory() as work:
                replay = run_evals.grade(review_path.read_text(encoding="utf-8"), assertions, 900,
                 Path(work), judge)
        except Exception as exc:
            print(f"  {name:<34} replay failed: {exc}")
            continue
        graded += 1
        # A verdict graded by different instructions is not a reproducibility sample.
        # Reporting it as one measures the prompt change and calls it judge variance,
        # which is how a known variable gets mistaken for a random one.
        stored_grader = stored.get("grader_config")
        if current_grader and stored_grader and stored_grader != current_grader:
            diff_prompt += 1
            graded -= 1
            print(f"  {grading_path.parent.parent.name:<34} skipped: graded by "
                  f"{stored_grader}, current prompt is {current_grader} -- a prompt "
                  f"difference is not a reproducibility sample")
            continue
        if current_grader and not stored_grader:
            diff_prompt += 1
            graded -= 1
            print(f"  {grading_path.parent.parent.name:<34} skipped: verdict predates "
                  f"grader-prompt digesting, so it cannot be compared to a replay today")
            continue
        original = [r["passed"] for r in stored["assertion_results"]]
        again = [v["passed"] for v in replay]
        differing = [a for a, b in zip(original, again) if a != b]
        if differing:
            flips += 1
        print(f"  {name:<34} {len(differing)} of {len(original)} verdicts flipped")
        # Which assertions, and what each attempt said. A count localises nothing: the
        # prompt can only be fixed once you can see whether the flips share a shape --
        # a phrasing near-miss, a severity label the review spelled differently, or one
        # finding being asked about by three assertions at three granularities.
        for idx, (a, b) in enumerate(zip(original, again)):
            if a == b:
                continue
            stored_ev = next((r.get("evidence", "") for r in stored["assertion_results"]
                              if r.get("text") == assertions[idx]), "")
            replay_ev = replay[idx].get("evidence", "") if idx < len(replay) else ""
            print(f"      [{idx}] was {'PASS' if a else 'fail'} -> "
                  f"{'PASS' if b else 'fail'}   assertion: {assertions[idx][:78]}")
            if stored_ev:
                print(f"          recorded: {str(stored_ev)[:110]}")
            if replay_ev:
                print(f"          replayed: {str(replay_ev)[:110]}")
    if graded:
        print(f"  flip rate: {flips}/{graded} reviews produced a different verdict")
        if flips:
            print("  A non-zero rate is a finding about the grader, not about the review: the")
            print("  same text must score the same way twice, or no delta in this repository")
            print("  is attributable to the change being measured.")


def no_axis_population(root: Path) -> dict:
    """How many findings fit no axis code — and whether we can know at all.

    `shared/output-format.md` requires every report to carry `Unclassified: <n>`, and
    `shared/domain-fanout.md` gives every agent a `fits-no-axis` exit token so the
    orchestrator has something to count. Between them the population is *sized*, which is
    what axis-codes.md says is missing: "a reserved code with no periodic review is a
    defect nobody can size, and it cannot be sized if nothing records its occurrences."

    Three states, never two, because collapsing them is the failure this tree exists to
    prevent:

      stated   -- the header carries a value
      absent   -- the review has no such header
      ungraded -- no review body on disk

    A review with `Unclassified: 0` and a review with no header at all are **different
    facts**: the first says the reviewer looked and the axis registry covered everything;
    the second says nothing was recorded. Averaging them, or reporting the total as 0,
    would claim "measured, and nothing found" about runs where the measurement never
    happened -- which is G8's exact pair, and this block is the place it would otherwise
    have appeared a second time.
    """
    # Preferred source is the verdict field the harness writes, which exists whether or
    # not the reviewer complied. The prose header is the fallback for verdicts written
    # before that field existed.
    slot = re.compile(r"^Unclassified:\s*(\d+)", re.MULTILINE)
    stated: list[tuple[str, int]] = []
    recorded_null: dict[str, int] = {}
    absent = ungraded = 0
    for path in sorted(root.glob("evals/iteration-*/*/*/grading.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "no_axis_count" not in doc:
            continue
        value = doc.get("no_axis_count")
        where = path.parent.as_posix()
        if value is None:
            reason = doc.get("no_axis_count_reason") or "unspecified"
            recorded_null[reason] = recorded_null.get(reason, 0) + 1
        else:
            stated.append((where, int(value)))
    for path in sorted(root.glob("evals/iteration-*/*/*/review.md")):
        match = slot.search(path.read_text(encoding="utf-8", errors="replace"))
        if match:
            stated.append((path.parent.as_posix(), int(match.group(1))))
        else:
            absent += 1
    for path in sorted(root.glob("evals/iteration-*/*/*/grading.json")):
        if not (path.parent / "review.md").is_file():
            ungraded += 1
    return {
        "stated": stated,
        "recorded_null": recorded_null,
        "absent": absent,
        "ungraded": ungraded,
        "total": len(stated) + absent,
        "sum": sum(n for _, n in stated),
        "nonzero": sum(1 for _, n in stated if n),
    }


def no_axis_from_findings(root: Path) -> dict:
    """Size the uncoded population from the findings themselves, not a self-reported header.

    The header was the wrong instrument. Every finding carries its axis code inline as
    `- **Domain:** Correctness (A1)`, so the population was readable from the evidence all
    along while the counter reported that it could not be read: 16 of 26 reviews with
    findings carried no header, so the header-only reader saw 9 reviews and the other 17
    contributed nothing rather than being counted as zero.

    A finding is counted per finding block, never by pairing two independent lists of
    heading and domain lines -- pairing them desynchronises at the first finding that
    omits a field, which is precisely the one worth seeing.

    Three shapes are distinguished rather than merged, because they call for different
    remedies: a code in the canonical `(A1)` form, the same code wrapped in backticks, and no
    Domain line at all. The second is a formatting variance that hides a finding from a
    reader; the third is a finding the reviewer failed to place.
    """
    import re
    head_re = re.compile(r"^###\s*\[(\w+)\]", re.M)
    canonical = re.compile(r"\(([A-Z]\d{1,2})\)")
    backticked = re.compile(r"\(\s*`?([A-Z]\d{1,2})`?\s*\)")
    out = {"reviews": 0, "findings": 0, "canonical": 0, "backticked": 0,
           "uncoded": 0, "uncoded_detail": []}
    for path in sorted(root.glob("evals/*/*/*/review.md")):
        try:
            text = path.read_text()
        except Exception:
            continue
        if "## Findings" not in text:
            continue
        body = text.split("## Findings", 1)[1].split("## Aligns well")[0]
        spans = [m.start() for m in head_re.finditer(body)]
        if not spans:
            continue
        out["reviews"] += 1
        name = path.parent.parent.name
        for i, s in enumerate(spans):
            block = body[s:spans[i + 1] if i + 1 < len(spans) else len(body)]
            if "None" in block.splitlines()[0]:
                continue
            out["findings"] += 1
            dom = [ln for ln in block.splitlines() if "**Domain:**" in ln]
            title = block.splitlines()[0].lstrip("# ").strip()[:58]
            if not dom:
                out["uncoded"] += 1
                out["uncoded_detail"].append((name, title, "no Domain line"))
            elif canonical.search(dom[0]):
                out["canonical"] += 1
            elif backticked.search(dom[0]):
                out["backticked"] += 1
                out["uncoded_detail"].append((name, title, "code wrapped in backticks"))
            else:
                out["uncoded"] += 1
                out["uncoded_detail"].append((name, title, dom[0].strip()[:48]))
    return out


def replicates_required(sd: float, effect: float, alpha: float = 0.05,
                        power: float = 0.80) -> int:
    """Replicates per arm to resolve `effect` against spread `sd`.

    "Underpowered" is an adjective; this is the count. Two-sided normal approximation:

        n = 2 (z_{alpha/2} + z_{power})^2 sd^2 / effect^2

    Ceiling at 400, and it refuses a non-positive effect rather than dividing by it. The
    result is a floor, not a promise: it assumes replicates are independent and share one
    spread, and a corpus whose spread grows with n would need more than this says.
    """
    from math import ceil, log, sqrt

    def z(p: float) -> float:
        # Acklam's rational approximation, adequate to three digits for a planning figure.
        a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
             1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
        b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
             6.680131188771972e+01, -1.328068155288572e+01)
        c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
             -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
        d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
             3.754408661907416e+00)
        pl, ph = 0.02425, 1 - 0.02425
        if p < pl:
            q = sqrt(-2 * log(p))
            return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
        if p > ph:
            q = sqrt(-2 * log(1 - p))
            return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
        q = p - 0.5
        r = q * q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)

    if effect <= 0:
        return 400
    n = ceil(2 * (z(1 - alpha / 2) + z(power)) ** 2 * sd ** 2 / effect ** 2)
    return min(n, 400)


def print_power(spread: dict) -> None:
    """State what this corpus can resolve, and what it cannot."""
    floor = (spread or {}).get("with_skill") or next(iter((spread or {}).values()), None)
    if not floor:
        print("\nRESOLVABLE EFFECT")
        print("  NOT MEASURED -- no arm has replicates, so there is no spread to power against.")
        return
    sd = floor["mean_sd"]
    print("\nRESOLVABLE EFFECT (how large a difference this design can see)")
    print(f"  measured spread: mean within-eval sd {sd:.3f} over {floor['evals']} eval(s)")
    for effect in (40, 20, 10, 5):
        n = replicates_required(sd, effect / 100)
        cost = "beyond any practical sweep" if n >= 400 else f"~{n * 2} replicate runs"
        print(f"  a {effect:>2}-point effect needs {n:>3} replicates per arm  ({cost})")
    print("  Read this as the instrument's reach, not a verdict. A design powered for 40 points")
    print("  cannot report on 5, so an ablation returning a null bounds the effect at the reach")
    print("  and never at zero.")


def concern_rates() -> dict:
    """Pass rate per concern, per arm -- the split G19 asks for.

    Three concerns, matching the independent blind re-measurement: whether the defect was
    detected, whether it was graded at the right severity, and whether the proposed fix was
    right. One rate over all three cannot say which the skill contributes, and that is not a
    presentational quibble: the blind measurement has detection at **+4.2 points** and severity
    at **+33.3**, so a headline that merges them optimises the axis the skill barely moves.

    Restricted to fixtures current in *both* arms. Comparing each arm over its own population is
    the defect already fixed twice in this file, and it would do the same damage here -- the two
    arms currently share 22 fixtures and admitting more would mean comparing different question
    sets and calling it a delta.

    The grades come from stored evidence, not from a live call, so this costs no quota. Where a
    concern has no assertions on the shared fixtures it reports NOT MEASURED rather than 0.0%,
    because an empty panel and a failing one are not the same result.
    """
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    import mismatch_probe as MP
    from grade_evals import EVAL_NAMES

    corpus = {e["id"]: e for e in load_json(SKILL_ROOT / "evals" / "evals.json")["evals"]}
    want = {"detection", "severity", "remediation"}
    per_arm: dict[str, dict[int, dict]] = {}
    for arm in ("with_skill", "without_skill"):
        got: dict[int, dict] = {}
        for path in sorted(glob.glob(str(ITERATION / "eval-*" / arm / "grading.json"))):
            try:
                grading = load_json(Path(path))
            except Exception:
                continue
            eid = grading.get("eval_id")
            results = grading.get("assertion_results")
            entry = corpus.get(eid)
            if not results or entry is None:
                continue
            if [r.get("text", "") for r in results] != entry.get("assertions"):
                continue
            roles = grading.get("assertion_roles") or entry.get("assertion_roles") or []
            if len(roles) != len(results):
                continue
            bucket = {k: [0, 0] for k in want}
            for role, text, res in zip(roles, entry["assertions"], results):
                if role != "verdict":
                    continue
                c = bucket[MP.concern(text)]
                c[0] += bool(res.get("passed"))
                c[1] += 1
            got[eid] = bucket
        per_arm[arm] = got

    shared = sorted(set(per_arm["with_skill"]) & set(per_arm["without_skill"]))
    out = {"shared": len(shared), "concerns": {}}
    for concern_name in sorted(want):
        wp = wt = bp = bt = 0
        for eid in shared:
            for src, acc in (("with_skill", "wp"), ("without_skill", "bp")):
                p, n = per_arm[src][eid][concern_name]
                if src == "with_skill":
                    wp += p; wt += n
                else:
                    bp += p; bt += n
        out["concerns"][concern_name] = {
            "with": (wp, wt), "without": (bp, bt),
            "delta": ((wp / wt - bp / bt) * 100) if wt and bt else None,
        }
    out["split"] = MP.concern_split(corpus)["totals"]
    return out


def print_concern_rates() -> None:
    got = concern_rates()
    sp = got["split"]
    print("\nCONCERN SPLIT (G19: which claim does each assertion test?)")
    print(f"  verdict-role assertions: detection {sp['detection']} · severity {sp['severity']}"
          f" · remediation {sp['remediation']}")
    print(f"  scored from stored evidence, so this costs no quota. Nothing is called live.")
    if not got["shared"]:
        print("  NOT MEASURED -- no fixture is current in both arms, so there is no shared")
        print("  population on which an arm can be compared with the other.")
        return
    print(f"  paired on {got['shared']} fixture(s) current in both arms\n")
    print(f"    {'concern':<14} {'with skill':>14} {'without':>14} {'delta':>10}")
    for name, c in got["concerns"].items():
        wp, wt = c["with"]
        bp, bt = c["without"]
        if not wt or not bt:
            print(f"    {name:<14} {'NOT MEASURED':>14}")
            continue
        d = c["delta"]
        print(f"    {name:<14} {wp:>4}/{wt:<3} {wp/wt:>6.1%} {bp:>4}/{bt:<3} {bp/bt:>6.1%}"
              f" {d:>+9.1f}")
    print("\n  Read the columns against each other, not against each other's size. The blind")
    print("  re-measurement in evals/README.md has detection at +4.2 points and severity at")
    print("  +33.3, so a skill whose headline is a single rate is optimising the smaller axis.")


def print_no_axis_from_findings(root: Path) -> None:
    """Report the no-axis population read from the findings, with the header as corroboration."""
    pop = no_axis_from_findings(root)
    print("\nNO-AXIS POPULATION (G9: sized from the findings, not from a header)")
    if not pop["reviews"]:
        print("  NOT MEASURED -- no review on disk carries a Findings section with findings in it.")
        return
    print(f"  reviews read:           {pop['reviews']}")
    print(f"  findings counted:       {pop['findings']}")
    print(f"  axis code, canonical:   {pop['canonical']}   `**Domain:** Correctness (A1)`")
    print(f"  axis code, backticked:  {pop['backticked']}   `**Domain:** Correctness (`A1`)` -- "
          f"a reader misses it")
    print(f"  no axis code:           {pop['uncoded']}   placed nowhere")
    for name, title, why in pop["uncoded_detail"]:
        print(f"    {name[:34]:<36} {why:<34} {title}")
    unreadable = pop["backticked"] + pop["uncoded"]
    if pop["findings"]:
        print(f"\n  {unreadable} of {pop['findings']} findings are not machine-readable as coded "
              f"({unreadable / pop['findings']:.1%}).")
    if unreadable:
        print("  A finding a reader cannot resolve to a code is indistinguishable from one the")
        print("  registry does not cover, so this is the population's floor, not its size.")
        print("  VERDICT: MEASURED, and non-zero. The population was readable all along; the")
        print("  header-only reader was the instrument that could not read it.")
    else:
        print("  VERDICT: MEASURED. Every finding resolves to an axis code a reader recognises,")
        print("  which is not the same as every finding being correctly placed.")


def print_no_axis(root: Path) -> None:
    pop = no_axis_population(root)
    print("\nNO-AXIS POPULATION (G9: can the uncoded population be sized?)")
    if not pop["total"]:
        print("  NOT MEASURED -- no review bodies on disk to read a header from.")
        return
    print(f"  review bodies read: {pop['total']}")
    print(f"  stated:                {len(pop['stated'])}  (sum {pop['sum']}, "
          f"non-zero in {pop['nonzero']})")
    for reason, count in sorted(pop["recorded_null"].items()):
        print(f"  recorded null ({reason}): {count}")
    print(f"  header absent:         {pop['absent']}")
    print(f"  runs with no body:     {pop['ungraded']}")
    if pop["recorded_null"]:
        print("  A run that recorded `null` is not a run that found nothing. It is a run that")
        print("  did not say, and the reason is on the record per run rather than lost in an")
        print("  aggregate. Fix the reviewer before reading anything into the sum.")
    if not pop["stated"]:
        print("  VERDICT: NOT MEASURED. Every review read is missing the header, so there is")
        print("  no observation to aggregate. This is not a finding of zero -- it is the absence")
        print("  of the observation, and the two must never render alike.")
        print("  The slot is required by output-format.md and no run in this corpus emits it, so")
        print("  the population cannot be sized from stored evidence until they do.")
        return
    if pop["absent"]:
        print(f"  VERDICT: PARTIAL. {len(pop['stated'])} read, {pop['absent']} carried no")
        print("  header. The sum above covers the reviews that stated one and nothing else.")
    else:
        print("  VERDICT: MEASURED across every review body on disk.")
    if pop["nonzero"] == 0 and not pop["absent"]:
        print("  Every reviewer recorded zero. Read that as 'the axis registry covered every")
        print("  finding these runs produced' -- not as 'the axis registry is complete'.")


def stale_verdicts() -> dict:
    """Which stored verdicts were graded against assertions the corpus no longer holds.

    Editing an assertion invalidates every verdict graded against it, and nothing here
    said so. Discovered by doing it: three assertions on one fixture were rewritten to
    stop being collectable by silence, the fixture bytes were untouched, so every
    fixture-digest check still read clean and this script printed nothing at all.
    `run_evals.already_current` had been answering the question correctly the whole time
    -- and was called from nowhere in the diagnostics.

    That is the shape this file already documents elsewhere: a check that produces no
    answer is not a check that found nothing, and only one of them is safe to ignore.
    """
    import run_evals as R

    try:
        evals = {e["id"]: e["assertions"]
                 for e in load_json(SKILL_ROOT / "evals" / "evals.json")["evals"]}
    except Exception:
        return {"checked": 0, "stale": [], "unknown": [], "ok": False}

    stale, unknown, checked = [], [], 0
    for path in sorted(glob.glob(str(ITERATION / "eval-*" / "*" / "grading.json"))):
        try:
            doc = load_json(Path(path))
        except Exception:
            continue
        eid = doc.get("eval_id")
        if eid is None:
            continue
        checked += 1
        name = Path(path).parent.parent.name
        if eid not in evals:
            unknown.append(name)
            continue
        if [r.get("text", "") for r in doc.get("assertion_results", [])] != evals[eid]:
            stale.append(name)
    return {"checked": checked, "stale": stale, "unknown": unknown, "ok": True}


def print_stale() -> None:
    print("\nSTALE VERDICTS (graded against assertions the corpus no longer holds)")
    got = stale_verdicts()
    if not got["ok"]:
        print("  could not read the corpus; nothing is reported current or stale")
        return
    if not got["checked"]:
        print("  no stored verdict carries an eval_id, so none can be checked")
        return
    if got["stale"]:
        print(f"  {len(got['stale'])} of {got['checked']} verdicts are void. Their assertions were")
        print("  edited after they were graded, so their scores describe a corpus that no")
        print("  longer exists. Fixture bytes unchanged is NOT enough -- an assertion edit moves")
        print("  the target without touching the fixture.")
        for name in got["stale"][:12]:
            print(f"    stale: {name}")
        if len(got["stale"]) > 12:
            print(f"    ... and {len(got['stale']) - 12} more")
    else:
        print(f"  none of {got['checked']} verdicts disagree with the current assertions")
    if got["unknown"]:
        print(f"  {len(got['unknown'])} name an eval_id absent from the corpus and were skipped")


def isolation_report() -> dict:
    """What isolation does each stored verdict actually claim?

    Measured 2026-10-05, and it is the most consequential thing found this session: a
    probe of the runner showed the shell tool's working directory is the real repository,
    even with the staged workspace as the process cwd, `--standalone` passed, and the
    workspace named as the trailing positional. This runner has no flag for setting the
    project directory, so the staged workspace cannot be made true through the CLI. A
    reviewer reaches `evals/evals.json` -- the answer key -- with one relative path.

    Ten of 44 event streams did, and three arms hold a stored verdict. One of those
    records `reason: contamination` in plumbing.json with a grading.json beside it.

    So a count is reported here rather than a verdict: the isolation field exists on new
    verdicts and not on the legacy ones, and which of those is usable is a judgement about
    a corpus, not something a scan may decide. What the scan does is make sure the
    question is asked where someone will see it.
    """
    claimed = unverified = absent = 0
    for path in sorted(glob.glob(str(ITERATION / "eval-*" / "*" / "grading.json"))):
        try:
            doc = load_json(Path(path))
        except Exception:
            continue
        if doc.get("reviewer_project_root") in ("unverified", "workspace"):
            claimed += 1
        elif doc.get("reviewer_project_root") is None:
            absent += 1
        else:
            unverified += 1
    return {"with_field": claimed, "without_field": absent, "other": unverified}


def print_isolation() -> None:
    got = isolation_report()
    total = got["with_field"] + got["without_field"] + got["other"]
    print("\nREVIEWER ISOLATION (could this reviewer reach the answer key?)")
    if not total:
        print("  no stored verdicts to describe")
        return
    if got["without_field"]:
        print(f"  {got['without_field']} of {total} stored verdicts predate the isolation record,")
        print("  so they say nothing about it. Recorded as unverified rather than assumed:")
        print("  a verdict that does not describe its own isolation is not evidence about it.")
    if got["with_field"]:
        print(f"  {got['with_field']} of {total} record reviewer_project_root=unverified.")
    print("  Measured: the runner resolves its own project root and the shell tool runs in the")
    print("  real repository, so evals/evals.json is one relative path away for every reviewer.")
    print("  No staged-workspace claim in this corpus is currently established. See G17.")


def path_stat(path: str) -> float:
    try:
        return Path(path).stat().st_mtime
    except OSError:
        return 0.0


def trend() -> dict:
    """Per-eval pass rate at each recorded base, and the delta between the latest two.

    The gap this closes said nothing compared this run's grades against a prior run of the
    same scope. Every verdict records the base it was graded at, so the comparison is
    possible -- but only between bases that both have verdicts, and the honest report of a
    one-base corpus is that there is nothing to compare. Printing a trend line from a
    single point would be a chart of nothing.

    A base is reported as a short digest, never a name, and an eval missing from either base
    is named rather than skipped: an eval that ran once and then stopped is a finding, and
    averaging over the ones that happened to run twice hides it.
    """
    import run_evals as R

    try:
        corpus = {e["id"]: e.get("name") for e in
                  load_json(SKILL_ROOT / "evals" / "evals.json")["evals"]}
    except Exception:
        return {"bases": [], "ok": False}

    by_base: dict[str, dict[int, list]] = {}
    written: dict[str, float] = {}
    names: dict = {}
    for path in sorted(glob.glob(str(ITERATION / "eval-*" / "*" / "grading.json"))):
        try:
            doc = load_json(Path(path))
        except Exception:
            continue
        base = doc.get("base_commit")
        eid = doc.get("eval_id")
        summary = doc.get("summary") or {}
        if not base or eid is None or not summary.get("total"):
            continue
        names.setdefault(eid, Path(path).parent.parent.name)
        slot = by_base.setdefault(base, {}).setdefault(eid, [])
        slot.append(summary["pass_rate"])
        written.setdefault(base, 0.0)
        written[base] = max(written[base], path_stat(path))

    # By when they were written, not by digest. Two short hex strings have no meaningful
    # order, so sorting them lexicographically put an older base after a newer one and the
    # delta came out backwards -- the comparison reported the change in the wrong direction,
    # which for a trend is worse than reporting none.
    bases = sorted(by_base, key=lambda b: (written.get(b, 0.0), b))
    rows = []
    if len(bases) >= 2:
        older, newer = bases[-2], bases[-1]
        for eid in sorted(set(by_base[older]) | set(by_base[newer])):
            a = by_base[older].get(eid)
            b = by_base[newer].get(eid)
            rows.append({
                "eval_id": eid,
                "older": round(sum(a) / len(a), 4) if a else None,
                "newer": round(sum(b) / len(b), 4) if b else None,
                "delta": round((sum(b) / len(b)) - (sum(a) / len(a)), 4)
                if a and b else None,
            })
    return {"bases": bases, "older": bases[-2] if len(bases) >= 2 else None,
            "newer": bases[-1] if bases else None, "rows": rows, "ok": True,
            "corpus": corpus, "names": names}


def label(got: dict, eid) -> str:
    """A name for an eval, falling back rather than rendering None."""
    return got["corpus"].get(eid) or got["names"].get(eid) or f"eval-{eid}"


def print_trend() -> None:
    got = trend()
    print("\nTREND (this run against the prior run of the same scope)")
    if not got["ok"]:
        print("  could not read the corpus; no trend reported")
        return
    bases = got["bases"]
    print(f"  bases with stored verdicts: {len(bases)}  {[b[:7] for b in bases]}")
    if len(bases) < 2:
        print("  NOT MEASURED -- verdicts exist at one base only, so there is no prior run of")
        print("  the same scope to compare against. A delta needs two points; a trend drawn")
        print("  through one is a chart of nothing, and reporting 0.0 here would be the same")
        print("  conflation this file exists to prevent.")
        return
    print(f"  comparing {got['older'][:7]} -> {got['newer'][:7]}")
    moved = 0
    for row in got["rows"]:
        if row["delta"] is None:
            print(f"    {label(got, row['eval_id']):<38} "
                  f"ran at only one base -- not comparable")
            continue
        moved += 1
        print(f"    {label(got, row['eval_id']):<38} "
              f"{row['older']:.3f} -> {row['newer']:.3f}  delta {row['delta']:+.3f}")
    print(f"  {moved} eval(s) comparable; the rest are named above rather than averaged away")


def cross_judge(sample: int, judge_a: str, judge_b: str) -> dict:
    """Do two judges grade the same review the same way?

    `judge_disjoint` is only meaningful if the judges would agree anyway. If they do not,
    a delta that moves when the judge changes is a property of the judge, not of the skill
    under test -- and the corpus has one such disagreement, reproducible within each judge
    and not across them, on an assertion about how many findings are above a severity.

    So this measures it rather than asserting it: the same stored reviews, graded twice,
    once by each judge, compared assertion by assertion. Disagreement is not automatically a
    defect -- two judges may both be right -- but an unmeasured disagreement means the
    instrument's own noise is unknown, and an unknown instrument cannot gate a delta.
    """
    import run_evals as R

    try:
        corpus = {e["id"]: e["assertions"] for e in
                  load_json(SKILL_ROOT / "evals" / "evals.json")["evals"]}
    except Exception:
        return {"ok": False}

    import tempfile
    picked, rows = [], []
    for path in sorted(glob.glob(str(ITERATION / "eval-*" / "with_skill" / "review.md"))):
        if len(picked) >= sample:
            break
        gj = Path(path).with_name("grading.json")
        if not gj.is_file():
            continue
        try:
            doc = load_json(gj)
        except Exception:
            continue
        eid = doc.get("eval_id")
        if eid is None or eid not in corpus:
            continue
        picked.append((path, corpus[eid], doc.get("eval_name") or Path(path).parent.parent.name))
    if not picked:
        return {"ok": True, "rows": [], "compared": 0, "agree": 0, "total": 0}

    agree = total = 0
    for path, assertions, name in picked:
        body = Path(path).read_text()
        out = []
        for model in (judge_a, judge_b):
            try:
                out.append([bool(v.get("passed")) for v in
                             R.grade(body, assertions, 240, Path(tempfile.mkdtemp()), model)])
            except Exception:
                out.append(None)
        a, b = out
        if a is None or b is None or len(a) != len(b):
            continue
        same = sum(1 for x, y in zip(a, b) if x == y)
        agree += same
        total += len(a)
        rows.append({"eval": name, "assertions": len(a), "agree": same,
                     "differ": [i for i, (x, y) in enumerate(zip(a, b)) if x != y]})
    return {"ok": True, "rows": rows, "compared": len(rows), "agree": agree, "total": total}


def print_cross_judge(sample: int, judge_a: str, judge_b: str) -> None:
    got = cross_judge(sample, judge_a, judge_b)
    print("\nCROSS-JUDGE AGREEMENT (same reviews, two judges)")
    if not got.get("ok"):
        print("  could not read the corpus; no agreement is reported")
        return
    if not got["total"]:
        print(f"  NOT MEASURED -- none of the {sample} sampled reviews could be graded by both "
              f"judges.")
        return
    rate = got["agree"] / got["total"]
    for r in got["rows"]:
        mark = "" if not r["differ"] else f"  differs on {r['differ']}"
        print(f"  {r['eval'][:40]:<42} {r['agree']}/{r['assertions']}{mark}")
    print(f"\n  agreement {got['agree']}/{got['total']} = {rate:.1%} over {got['compared']} reviews")
    print("  Disagreement here is the instrument's own noise. It bounds how small a delta can be")
    print("  attributed to the change rather than to the judge, and it is not a defect on its own.")
def print_verdict_probe(verdict: dict) -> None:
    """Report the verdict/probe split, or that it cannot be measured.

    A block that iterates nothing prints nothing, and prints nothing is
    indistinguishable from a block that ran and found nothing -- except that the
    second is evidence and the first is silence. Both states are reported here.
    """
    arms = {k: v for k, v in verdict.items() if not k.startswith("_")}
    excluded = verdict.get("_excluded", {})
    if not arms:
        print("\nVERDICT vs PROBE ASSERTIONS")
        print("  NOT MEASURED -- no stored verdict's fixture declares `assertion_roles`, so "
              "a verdict-role assertion cannot be told from a probe-role one. Counted as "
              "unmeasured rather than as passing everything.")
    roles_seen = verdict.get("_roles") or {}
    if roles_seen:
        known = {"verdict", "probe"}
        unknown = {r: n for r, n in roles_seen.items() if r not in known}
        print(f"  roles counted: " + ", ".join(f"{r} {n}" for r, n in sorted(roles_seen.items())))
        if unknown:
            print(f"  UNRECOGNISED role(s): {unknown} -- counted as quality claims because a "
                  f"role nothing")
            print("    defines cannot be excluded from a quality rate on the strength of its "
                  "own label.")
    if excluded.get("no_roles"):
        print(f"  excluded, roles undeclared: {excluded['no_roles']} verdict(s) whose fixture "
              f"names no roles, so no assertion can be identified as a quality claim")
    if excluded.get("stale"):
        print(f"  excluded as void: {excluded['stale']} verdict(s) whose recorded assertions "
              f"disagree with the corpus")
    if not arms:
        return
    print("\nVERDICT vs PROBE ASSERTIONS")
    for arm, stats in arms.items():
        print(
            f"  {arm:<14} verdict {stats['verdict_passed']}/{stats['verdict_total']}"
            f" ({stats['verdict_rate'] * 100:.1f}%) · probe {stats['probe_rate'] * 100:.0f}%"
        )
    print("  fp_rate and fn_rate read verdict assertions only, so a review that")
    print("  narrates the probe without acting on it earns nothing on them.")
    suppress, nosuppress = arms.get("with_skill"), arms.get("nosuppress")
    if suppress and nosuppress and suppress["verdict_total"] and nosuppress["verdict_total"]:
        # Direction: the false-positive panel's assertions assert that a finding
        # was NOT made, so the gate arm scores higher there. The
        # false-negative panel asserts a planted defect WAS found, so a gate
        # that went blind scores lower. This figure is the net of those two
        # opposing pressures and is necessary, never sufficient - the
        # false-negative bound gates it separately.
        #
        # And it is differenced over the *paired* fixtures, never over each arm's own
        # population. Reported that way it came out at +17.4 points from 594 assertions
        # against 272 -- two different experiments subtracted from each other, and a
        # "KILLED" verdict printed underneath. That is the same defect grade_evals.py had
        # in its baseline denominator, and a verdict of "cut the gate" must not rest on it.
        pr = verdict.get("_paired") or {}
        if not pr.get("evals"):
            print("  SUPPRESSION ABLATION: NOT MEASURED -- no fixture is current in both arms, "
                  "so there is no shared population to difference.")
            return
        print(f"  paired on {pr['evals']} fixture(s) current in both arms: "
              f"{', '.join(str(i) for i in pr.get('ids', []))}")
        for arm in ("with_skill", "nosuppress"):
            s = pr[arm]
            print(f"    {arm:<11} {s['verdict_passed']}/{s['verdict_total']} "
                  f"({s['verdict_rate'] * 100:.1f}%)  over {s.get('samples', 0)} samples")
        if pr["with_skill"].get("samples") != pr["nosuppress"].get("samples"):
            print("    Different replicate counts, so these are means over different sample")
            print("    sizes. That is a power limitation, not a population mismatch: the")
            print("    fixtures and their assertions are the same.")
        print("    The two rates above the ablation are over different populations "
              f"({arms['with_skill']['verdict_total']} against "
              f"{arms['nosuppress']['verdict_total']} assertions), so they are not "
              "differenced against each other.")
        suppress, nosuppress = pr["with_skill"], pr["nosuppress"]
        delta = suppress["verdict_rate"] - nosuppress["verdict_rate"]
        print(f"\n  SUPPRESSION ABLATION: verdict rate {nosuppress['verdict_rate'] * 100:.1f}%"
              f" -> {suppress['verdict_rate'] * 100:.1f}%  (delta {delta * 100:+.1f} pts)")
        print("  Net of two opposing panels: false-positive assertions reward")
        print("  silence, false-negative assertions reward catching the planted")
        print("  defect. A gate that deletes everything scores high on the first")
        print("  and zero on the second, so read this against the FN bound.")
        if delta < KILL_DELTA:
            print(f"  KILLED. Below the {KILL_DELTA * 100:.0f}-point bar this corpus can")
            print("  resolve. The gate is not earning its place and must be cut.")
        else:
            print(f"  Above the {KILL_DELTA * 100:.0f}-point bar. Still not sufficient on its")
            print("  own; the false-negative bound and silence rate gate it too.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Eval design diagnostics.")
    parser.add_argument("--determinism", type=int, metavar="N", help="re-grade N stored reviews")
    parser.add_argument("--cross-judge", type=int, metavar="N",
                        help="grade N stored reviews with two judges and compare")
    parser.add_argument("--recover-verdicts", type=int, nargs="?", const=0, metavar="N",
                        help="re-grade stored review bodies to supply missing "
                             "assertion_results; N limits it, default all")
    parser.add_argument("--judge-a", default=None,
                        help="judge to use: first judge for --cross-judge, and the judge for "
                             "--determinism and --recover-verdicts. Pin it. With no value these "
                             "fall back to the runner's own default, which is the model most "
                             "likely to be exhausted, and every replay then fails with a quota "
                             "error instead of naming the judge it tried")
    parser.add_argument("--judge-b", default=None, help="second judge, for --cross-judge")
    args = parser.parse_args()

    rate, passed, total, saturated = headroom()
    print("HEADROOM")
    print(f"  with_skill: {passed}/{total} = {rate * 100:.1f}%")
    if saturated:
        print(f"  SATURATED at or above {SATURATION_THRESHOLD * 100:.0f}%.")
        print("  Quality hillclimbing cannot work: every change is inside the noise.")
        # This line is machine-printed, and Phase 5 reads this file's output before
        # choosing an objective. It used to recommend cost, which hillclimb.md forbids
        # because this harness records no metric for it -- so the diagnostic was
        # instructing the loop to adopt an objective the tree has ruled out. A refusal
        # stated in five files and permitted in a sixth, by a script, resolves by
        # whichever the reader reads last.
        print("  Latency remains measurable (timing.json: duration_ms).")
        print("  Cost is NOT measurable here and is not offered; see hillclimb.md.")

    trig, consulted, rollouts, missed = trigger_rate()
    print("\nTRIGGER RATE")
    if rollouts:
        print(f"  rollouts that opened the skill: {consulted}/{rollouts} = {trig * 100:.1f}%")
        if missed:
            print(f"  did not trigger ({len(missed)}): {', '.join(missed[:8])}")
            if len(missed) > 8:
                print(f"    ... and {len(missed) - 8} more")
    else:
        print("  no events.jsonl recorded - run scripts/run_evals.py first")

    zero, full, mid, ungraded = task_tells()
    print_verdict_probe(verdict_rates())
    print_concern_rates()
    print_power(replicate_spread())
    print_no_axis_from_findings(SKILL_ROOT)
    print_no_axis(SKILL_ROOT)
    print_trend()
    print_isolation()
    print_stale()

    print("\nTASK TELLS")
    print(f"  pinned at 0%  (broken task, fails every run): {len(zero)} {', '.join(zero) if zero else ''}")
    print(f"  pinned at 100% (no headroom)                  : {len(full)}")
    print(f"  with headroom                                 : {len(mid)}")
    for name, r in mid:
        print(f"    {name:<34} {r * 100:.0f}%")
    if ungraded:
        print(f"  EXCLUDED, rollout did not produce a review   : {len(ungraded)}")
        print(f"    {', '.join(ungraded[:8])}")
        if len(ungraded) > 8:
            print(f"    ... and {len(ungraded) - 8} more")
        print("    A recorded score here is infrastructure noise, not a task result.")
        print("    Re-run these; scripts/run_evals.py now refuses to grade them.")

    print("\nPLUMBING (timeouts, API errors, denied tools, cut-offs)")
    plumbing_hits: list[str] = []
    for path in sorted(glob.glob(str(ITERATION / "eval-*" / "with_skill" / "plumbing.json"))):
        name = Path(path).parent.parent.name
        try:
            detail = load_json(Path(path))
        except Exception:
            detail = {}
        reason = detail.get("reason", "") or f"{len(detail.get('tool_errors', []))} tool error(s)"
        plumbing_hits.append(f"{name}: {reason}"[:160])
    for path in sorted(glob.glob(str(ITERATION / "eval-*" / "without_skill" / "plumbing.json"))):
        name = Path(path).parent.parent.name + "/baseline"
        try:
            detail = load_json(Path(path))
        except Exception:
            detail = {}
        reason = detail.get("reason", "") or f"{len(detail.get('tool_errors', []))} tool error(s)"
        plumbing_hits.append(f"{name}: {reason}"[:160])
    if plumbing_hits:
        print(f"  {len(plumbing_hits)} run(s) excluded by the plumbing gate:")
        for hit in plumbing_hits[:10]:
            print(f"    {hit}")
        if len(plumbing_hits) > 10:
            print(f"    ... and {len(plumbing_hits) - 10} more")
    else:
        print("  no plumbing blocks recorded")

    spread = replicate_spread()
    if spread:
        print("\nREPLICATE SPREAD (the noise floor hillclimb.md requires)")
        for arm, stats in spread.items():
            print(
                f"  {arm:<14} {stats['evals']} eval(s) with replicates · "
                f"mean within-eval sd {stats['mean_sd']:.3f} · "
                f"worst {stats['worst_sd']:.3f} ({stats['worst_eval']})"
            )
        floor = spread.get("with_skill") or next(iter(spread.values()))
        if floor["mean_sd"] <= 0:
            print("  No eval has more than one replicate, so run-to-run variance is")
            print("  still unmeasured and no delta can be gated. Use --reps > 1.")
        else:
            print(f"  A delta smaller than ~{floor['mean_sd']:.3f} on a single eval is")
            print("  inside the noise. Do not act on one.")


    if args.recover_verdicts is not None:
        print_recovered(recover_verdicts(args.recover_verdicts or None, args.judge_a))
        return 0

    if args.cross_judge:
        if not (args.judge_a and args.judge_b):
            print("  --cross-judge needs --judge-a and --judge-b")
            return 1
        print_cross_judge(args.cross_judge, args.judge_a, args.judge_b)
        return 0

    if args.determinism:
        print(f"\nGRADER DETERMINISM (requested {args.determinism}; the rate below names its own denominator)")
        determinism(args.determinism, args.judge_a)
    else:
        print("\nGRADER DETERMINISM: not sampled — pass --determinism N before trusting a delta")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())