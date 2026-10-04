#!/usr/bin/env python3
"""Eval assertion grading and benchmark aggregator for se-review.

Performs:
1. Verification of grading.json assertion coverage against evals/evals.json.
2. Aggregation of pass rates, standard deviations, and comparative deltas.
3. Formatted display of benchmark results per the Agent Skills specification.
"""

import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_registry import EVAL_NAMES  # noqa: E402
from run_evals import fixture_digests  # noqa: E402

# Heuristic over free-text grader evidence. Matches a baseline failure whose
# stated reason is the absence of this skill's vocabulary rather than a missed
# defect. Reporting aid only - never a gate, and never a verdict.
VOCABULARY_FAILURE = re.compile(
    r"lacked rubric|taxonomy|severity|axis|structured header|report (?:structure|order|inverted)|"
    r"no structured|header present|not present in",
    re.IGNORECASE,
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def published_block(t_w_total: int, t_w_passed: int, t_o_total: int, t_o_passed: int,
                     n_paired: int, paired_assertions: int, n_measured: int,
                     n_declared: int) -> str:
    """The summary `evals/README.md` publishes, built from the numbers the aggregate uses.

    Held as a function so a test can hold the README to it, which is the only part that
    mattered. This block was hand-copied twice and went stale twice: the README sat reading
    `643/689 (93.3%)` and `+71.9%` weeks after the correction that produced `409/640
    (63.9%)`, and asserting run-to-run variance was unmeasured three weeks after it was
    measured at 0.156. It was then pasted again from this output and drifted a second time
    within the hour -- because pasting is remembering, and the README is the one place in
    this repository a number can be quoted without the file it came from.
    """
    out = []
    for label, total, passed in (("With Skill", t_w_total, t_w_passed),
                                 ("Baseline", t_o_total, t_o_passed)):
        rate = passed / total if total else 0.0
        out.append(f"Overall Assertions: {label}: {passed}/{total} ({rate * 100:.1f}%)")
    if paired_assertions:
        out.append(f"Paired evals (both arms current): {n_paired} - {paired_assertions} assertions")
    out.append(f"Admissible denominator: {n_measured} of {n_declared} evals "
               f"(the rest are void, unverified or absent)")
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("Usage: python scripts/grade_evals.py [ITERATION_DIR]")
        print("\nAggregates assertion results and updates benchmark.json per Agent Skills spec.")
        print("Arguments:")
        print("  ITERATION_DIR Path to the iteration directory (default: evals/iteration-1)")
        print("  -h, --help    Show this help message and exit")
        return 0

    skill_dir = Path(__file__).resolve().parent.parent
    evals_dir = skill_dir / "evals"
    evals_spec = load_json(evals_dir / "evals.json")

    iteration_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else evals_dir / "iteration-1"
    if not iteration_dir.is_dir():
        print(f"Error: Iteration directory not found: {iteration_dir}")
        return 1

    eval_items = evals_spec.get("evals", [])
    eval_names = EVAL_NAMES

    print("=================================================================")
    print("      se-review: Iteration 1 Comparative Benchmark Report       ")
    print("=================================================================\n")

    summary_with = {}
    summary_without = {}
    stale = []
    baseline_classes = {"vocabulary": 0, "substance": 0}

    table_rows = []
    measured_any = ungraded_with = ungraded_without = unpaired = 0

    for item in eval_items:
        eid = item["id"]
        ename = eval_names.get(eid, f"eval-{eid}")
        edir = iteration_dir / ename
        assertions = item.get("assertions", [])
        total_asserts = len(assertions)

        # with_skill
        with_grading_path = edir / "with_skill" / "grading.json"
        if with_grading_path.is_file():
            wg = load_json(with_grading_path)
            w_passed = wg.get("summary", {}).get("passed", 0)
            w_rate = wg.get("summary", {}).get("pass_rate", 0.0)
            # Replicates, counted. `passed` in a verdict with replicates is summed across
            # every replicate while the assertion count is not, so comparing them directly
            # reports more assertions passed than exist: measured, `823/753 (109.3%)`.
            # Both sides of the fraction now count the same population.
            w_reps = 1 + len(wg.get("replicates") or [])
            w_measured = True
        else:
            w_passed, w_rate, w_reps = 0, 0.0, 0
            # Not zero. Unmeasured. An eval that never ran produced no pass and no fail,
            # and folding it in as 0 of N asserts "measured, and every assertion failed" --
            # G8's exact pair, reached by arithmetic instead of by a rendering.
            # `shared/severity-and-rules.md`: "a floored 0 currently claims 'measured, and
            # this bad' about a domain that was never opened."
            w_measured = False

        # without_skill
        without_grading_path = edir / "without_skill" / "grading.json"
        if without_grading_path.is_file():
            wog = load_json(without_grading_path)
            wo_passed = wog.get("summary", {}).get("passed", 0)
            wo_rate = wog.get("summary", {}).get("pass_rate", 0.0)
            wo_measured = True
        else:
            wo_passed, wo_rate = 0, 0.0
            wo_measured = False

        # Staleness: a stored verdict is only evidence for the assertion text it
        # was graded against. Adding, removing, or rewording an assertion
        # silently invalidates it, because the aggregate below sums a stored
        # `summary.passed` count and never matches text. Detect that here
        # rather than reporting old numbers under a new denominator.
        stale_reasons = []
        for label, gpath in (("with_skill", with_grading_path), ("without_skill", without_grading_path)):
            if not gpath.is_file():
                stale_reasons.append(f"{label}: no grading.json")
                continue
            gj = load_json(gpath)
            if "assertion_results" not in gj:
                stale_reasons.append(
                    f"{label}: grading format predates assertion-text capture, so the stored "
                    f"pass count cannot be tied to the current assertions"
                )
                continue
            # Fixture bytes. An assertion text that has not moved still does not mean
            # the verdict is current, if the file it was about has. `absent` on either
            # side means the verdict predates digesting, which is staleness rather than
            # drift -- reported as its own reason so the two are not conflated.
            stored_digests = gj.get("fixture_digests")
            if not stored_digests:
                stale_reasons.append(f"{label}: verdict predates fixture digesting, so the "
                                     f"files it graded cannot be shown to be the files on disk")
            else:
                current = fixture_digests(item)
                drifted = sorted(k for k in set(stored_digests) | set(current)
                                 if stored_digests.get(k) != current.get(k))
                if drifted:
                    stale_reasons.append(f"{label}: fixture bytes changed since the verdict -- "
                                         + ", ".join(drifted[:3])
                                         + ("..." if len(drifted) > 3 else ""))

            recorded = [r.get("text", "") for r in gj.get("assertion_results", [])]
            if recorded != assertions:
                added = len(assertions) - len(recorded)
                if added > 0:
                    stale_reasons.append(f"{label}: {added} assertion(s) added or reworded since the last run")
                elif added < 0:
                    stale_reasons.append(f"{label}: {abs(added)} assertion(s) removed since the last run")
                else:
                    stale_reasons.append(f"{label}: assertion text reworded since the last run")
            elif gj.get("summary", {}).get("total") != total_asserts:
                stale_reasons.append(
                    f"{label}: recorded total {gj.get('summary', {}).get('total')} != current {total_asserts}"
                )
        if stale_reasons:
            stale.append({"eval": ename, "reasons": stale_reasons})

        summary_with[ename] = {
            "pass_rate": round(w_rate, 3),
            "passed": w_passed,
            # Replicate-weighted, so passed <= total holds. `assertions` keeps the
            # unweighted count for anything that means "how many questions were asked".
            "failed": max(0, total_asserts * w_reps - w_passed),
            "total": total_asserts * w_reps,
            "assertions": total_asserts,
            "replicates": w_reps,
        }
        summary_without[ename] = {
            "pass_rate": round(wo_rate, 3),
            "passed": wo_passed,
            "failed": total_asserts - wo_passed,
            "total": total_asserts,
        }

        # A baseline failure is only evidence that the skill improves review
        # quality if the baseline actually failed to review. Many failures are
        # the baseline producing a reasonable review that did not use this
        # skill's vocabulary - "lacked rubric/taxonomy/severity", no structured
        # header, wrong report order. Those measure compliance with a rubric a
        # rubric-less model was never given, not review quality, and they
        # inflate the headline delta. Split them out. This is a heuristic over
        # free-text evidence, so it is a reporting aid and never a verdict.
        if without_grading_path.is_file():
            for r in load_json(without_grading_path).get("assertion_results", []):
                if r.get("passed"):
                    continue
                if VOCABULARY_FAILURE.search(str(r.get("evidence", ""))):
                    baseline_classes["vocabulary"] += 1
                else:
                    baseline_classes["substance"] += 1

        # A delta needs both arms measured. One arm short is not a small delta.
        if w_measured and wo_measured:
            delta_pct = (w_rate - wo_rate) * 100
            delta_cell = f"+{delta_pct:.1f}%"
        else:
            missing = ", ".join(x for x, ok in (("with", w_measured), ("without", wo_measured)) if not ok)
            delta_cell = f"not measured ({missing} arm)"
        w_cell = f"{w_passed}/{total_asserts} ({w_rate*100:.1f}%)" if w_measured else "not run"
        wo_cell = f"{wo_passed}/{total_asserts} ({wo_rate*100:.1f}%)" if wo_measured else "not run"
        table_rows.append((ename, w_cell, wo_cell, delta_cell))
        measured_any += int(w_measured or wo_measured)
        if not w_measured:
            ungraded_with += 1
        if not wo_measured:
            ungraded_without += 1
        if not (w_measured and wo_measured):
            unpaired += 1

    # Print formatted table
    print(f"{'Eval Name':<22} | {'With Skill':<18} | {'Without Skill (Baseline)':<24} | {'Delta':<10}")
    print("-" * 82)
    for name, ws, wos, d in table_rows:
        print(f"{name:<22} | {ws:<18} | {wos:<24} | {d:<10}")
    print("-" * 82)

    # What the baseline delta is actually made of. A single blended percentage
    # reads as "the skill makes reviews this much better", which overstates it
    # when most of the gap is a rubric-less model not using a rubric.
    baseline_total = baseline_classes["vocabulary"] + baseline_classes["substance"]
    if baseline_total:
        vocab_pct = baseline_classes["vocabulary"] / baseline_total * 100
        print(f"\nBaseline failures: {baseline_total} total across recorded evals")
        print(f"  vocabulary / format compliance : {baseline_classes['vocabulary']:>4}  ({vocab_pct:.1f}%)")
        print(f"  substance (missed defect)      : {baseline_classes['substance']:>4}  ({100 - vocab_pct:.1f}%)")
        print("  Only the second line is evidence about review quality. The first is a")
        print("  model without this rubric failing to satisfy it, and it inflates the")
        print("  headline delta. Classified by regex over grader evidence - indicative.")

    # Compute overall statistics.
    #
    # Every denominator below is the MEASURED set. An eval with no verdict in an arm
    # contributes to neither that arm's numerator nor its denominator, and is counted on
    # its own line instead. `shared/severity-and-rules.md` requires this of a domain
    # score and `shared/output-format.md` of a finding count; an aggregate is the same
    # claim with more numbers in it. Before this, `summary_with` covered all 102 evals and
    # an ungraded one contributed a silent zero -- so 45 fixtures that never ran were
    # reported as measured-and-equal, and each printed +0.0%, which reads as "the skill
    # changed nothing here" about a run that never happened.
    # Evals holding a verdict that disagrees with the corpus about what was asked. Computed
    # here rather than taken from `stale`, because `stale` also records "no grading.json" --
    # an unmeasured eval, which is a different thing. Using it for this excluded every eval
    # in the corpus, including the ones whose one arm is perfectly good.
    corpus_now = {e["id"]: e.get("assertions", []) for e in eval_items}

    def currency(ename: str, condition: str) -> str:
        """`current`, `void`, `unverified` or `absent` -- four states, not two.

        The two-state version returned False whenever a verdict could not be *checked*, which
        put an unverified verdict in the same bucket as a contradicted one. Measured over the
        corpus: 38 verdicts are current, **8 are void** because their recorded assertions
        disagree with what the corpus now asks, and **40 are unverified** because they carry
        no `assertion_results` at all. Reporting the last as void says their evidence
        contradicts the corpus, which is false -- nothing about them has been examined. It
        points the next person at the wrong repair: a void verdict needs re-grading, an
        unverified one needs the field written, and conflating them sends them to re-grade 40
        verdicts that were never wrong.

        `unverified` is excluded from the aggregate either way, so no reported rate moves. Only
        the reason a reader is given for the exclusion changes.
        """
        path = iteration_dir / ename / condition / "grading.json"
        if not path.is_file():
            return "absent"
        try:
            gj = load_json(path)
        except Exception:
            return "unverified"
        eid = gj.get("eval_id")
        if eid is None:
            return "unverified"
        if "assertion_results" not in gj:
            return "unverified"
        recorded = [r.get("text", "") for r in gj.get("assertion_results", [])]
        return "current" if recorded == corpus_now.get(eid) else "void"

    def by_state(condition: str) -> dict:
        out = {"current": set(), "void": set(), "unverified": set(), "absent": set()}
        for ename in (summary_with if condition == "with_skill" else summary_without):
            out[currency(ename, condition)].add(ename)
        return out

    def void_names(condition: str) -> set:
        """Evals that cannot contribute: void or unverified. Both are out; they are not the same."""
        st = by_state(condition)
        return st["void"] | st["unverified"]

    def _graded(condition: str) -> dict:
        """Evals holding a verdict that still matches the corpus.

        The presence of a `grading.json` is not currency. Measured: 105 of the stored
        verdicts were graded against assertions the corpus has since reworded or removed,
        and this filter admitted every one of them -- so `total_assertions`, the numerator,
        and the pass rate `headroom()` turns into a saturation verdict were all computed over
        live and void evidence mixed together, with a denominator that counted both.
        Hillclimbing reads that number to choose an objective, so the consequence is not a
        wrong report but a wrong instruction.
        """
        source = summary_with if condition == "with_skill" else summary_without
        void = void_names(condition)
        return {k: v for k, v in source.items()
                if (iteration_dir / k / condition / "grading.json").is_file()
                and k not in void}

    measured_with = _graded("with_skill")
    measured_without = _graded("without_skill")
    declared_assertions = sum(v.get("assertions", v["total"]) for v in summary_with.values())

    total_w_passed = sum(v["passed"] for v in measured_with.values())
    total_wo_passed = sum(v["passed"] for v in measured_without.values())
    total_assertions = sum(v["total"] for v in measured_with.values())
    wo_assertions = sum(v["total"] for v in measured_without.values())

    # Only evals where BOTH arms ran can be differenced.
    paired = [k for k in measured_with if k in measured_without]
    paired_assertions = sum(measured_with[k]["total"] for k in paired)

    def _mean_of(d: dict) -> float:
        return sum(v["pass_rate"] for v in d.values()) / len(d) if d else 0.0

    mean_w = _mean_of(measured_with)
    mean_wo = _mean_of(measured_without)

    def _stddev(vals: list[float]) -> float:
        if len(vals) < 2:
            return 0.0
        mean = sum(vals) / len(vals)
        return math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1))

    # Dispersion of per-eval pass rates. This is spread across evals, NOT run-to-run
    # variance: every eval is run once per arm, so there is no repeat to measure
    # variance against. Do not read it as the noise floor hillclimb.md requires -
    # that needs replicates (see eval-design.md, known gap).
    stddev_w = _stddev([v["pass_rate"] for v in summary_with.values()])
    stddev_wo = _stddev([v["pass_rate"] for v in summary_without.values()])

    # Timing means over runs that produced a verdict. A run with timing.json but
    # no grading.json was rejected upstream by the plumbing gate, so its duration
    # is infrastructure noise and must not enter the mean.
    def _timing_mean(condition: str) -> float | None:
        samples: list[float] = []
        for ename in summary_with:
            edir = iteration_dir / ename / condition
            if not (edir / "grading.json").is_file():
                continue
            try:
                samples.append(float(load_json(edir / "timing.json")["duration_ms"]))
            except Exception:
                continue
        return round(sum(samples) / len(samples), 1) if samples else None

    timing_w = _timing_mean("with_skill")
    timing_wo = _timing_mean("without_skill")

    # The honest headline prints two denominators, because there are two populations:
    # the corpus, and the part of it that ran. Reporting one number over the other is
    # how 45 fixtures that never ran came to look measured-and-equal.
    def _pct(n: int, d: int) -> str:
        return f"{n}/{d} ({n / d * 100:.1f}%)" if d else "no denominator"

    _delta = ("+" + format((total_w_passed - total_wo_passed) / paired_assertions * 100, ".1f") + "%"
              if paired_assertions else "not measured")
    print(f"{'Overall Assertions':<22} | {_pct(total_w_passed, total_assertions)}   | "
          f"{_pct(total_wo_passed, wo_assertions)}            | {_delta}")
    print()
    print("  denominators, because a percentage without one is unverified:")
    print(f"    declared in evals.json        {declared_assertions} assertions / {len(summary_with)} evals")
    print(f"    measured, with_skill          {total_assertions} / {len(measured_with)} evals")
    # The published block in evals/README.md is a hand-copied summary, and a hand-copied
    # summary outlives the run that produced it: it sat there reading `643/689 (93.3%)` and
    # "+71.9%" weeks after the correction that produced `409/640 (63.9%)`, and asserting
    # run-to-run variance was unmeasured three weeks after it was measured at 0.156. So the
    # block is printed here, from the same numbers the aggregate uses, and the README quotes
    # it rather than restating it.
    print("\nPUBLISHED SUMMARY (the evals/README.md block, checked against it by a test)")
    print(published_block(total_assertions, total_w_passed, wo_assertions, total_wo_passed,
                          len(paired), paired_assertions, len(measured_with),
                          len(summary_with)))
    spread = []
    for ename in measured_with:
        path = iteration_dir / ename / "with_skill" / "grading.json"
        try:
            rep = load_json(path).get("replicate_summary") or {}
        except Exception:
            continue
        sd = rep.get("stdev_pass_rate")
        if sd is not None and (rep.get("n") or 0) >= 2:
            spread.append(sd)
    if spread:
        print(f"Run-to-run variance: mean within-eval sd {sum(spread) / len(spread):.3f} "
              f"over {len(spread)} eval(s)")
    else:
        print("Run-to-run variance: NOT MEASURED -- no admissible arm has replicates")
    print("```")

    for cond in ("with_skill", "without_skill"):
        st = by_state(cond)
        for state in ("current", "void", "unverified", "absent"):
            if st[state]:
                why = {
                    "current": "verdict matches the corpus -- admitted to the aggregate",
                    "void": "verdict disagrees with the corpus -- needs re-grading",
                    "unverified": "no assertion_results recorded -- cannot be checked either way",
                    "absent": "never run",
                }[state]
                print(f"    {cond:<14} {state:<12} {len(st[state]):>3} evals  ({why})")
    # Both non-current states are counted as unmeasured and never as failures. The four
    # states above say which is which and why, because the two need different repairs and a
    # reader given only the total cannot tell which one they are looking at.
    print(f"    measured, without_skill       {wo_assertions} / {len(measured_without)} evals")
    print(f"    both arms, so differencable   {paired_assertions} / {len(paired)} evals")
    print(f"    never run, with_skill         {len(summary_with) - len(measured_with)} evals")
    print(f"    never run, without_skill      {len(summary_without) - len(measured_without)} evals")
    print(f"    only one arm, so no delta     {unpaired} evals")
    if unpaired:
        print("    An eval with one arm has no delta. It prints as `not measured`, never as")
        print("    +0.0%, because +0.0% is a claim: measured, and the skill changed nothing.")
        _never = (len(summary_with) - len(measured_with)
                  + len(summary_without) - len(measured_without))
        print(f"    {_never} arm-runs produced no verdict, and that is not {_never} findings")
        print("    that were missed. It is an absence of observation, which is why it is")
        print("    counted here rather than as a score above.")
    print(f"{'Mean Pass Rate':<22} | {mean_w*100:.1f}% (across-eval sd {stddev_w:.3f})    | {mean_wo*100:.1f}% (across-eval sd {stddev_wo:.3f})        | +{(mean_w - mean_wo)*100:.1f}%")
    print(f"{'Run-to-run variance':<22} | not measured - each eval runs once per arm; no replicates")
    if timing_w is not None or timing_wo is not None:
        print(f"{'Mean duration_ms':<22} | {timing_w} | {timing_wo}")

    # Update benchmark.json
    benchmark_file = iteration_dir / "benchmark.json"
    benchmark_data = {
        "iteration": 1,
        "date": "2026-09-27",
        "staleness": {
            "status": "stale" if stale else "verified",
            "stale_eval_count": len(stale),
            "stale_evals": stale,
        },
        "baseline_failure_classes": {
            "vocabulary_or_format": baseline_classes["vocabulary"],
            "substance_missed_defect": baseline_classes["substance"],
            "total": baseline_total,
            "caveat": (
                "Classified by regex over grader evidence text; indicative, not a verdict. "
                "Vocabulary failures mean a model without this skill's rubric failed to satisfy "
                "it, so they measure format compliance rather than review quality and inflate "
                "the headline delta. Only 'substance_missed_defect' is evidence about review "
                "quality. Evals whose grading.json predates assertion-text capture contribute "
                "no classification, so these counts are a floor, not a total."
            ),
        },
        "note": f"Comparative evaluation: with_skill vs without_skill baseline runs across {total_assertions} assertions in {len(eval_items)} test cases.",
        "run_summary": {
            "with_skill": {
                "pass_rate": {"mean": round(mean_w, 3), "stddev": round(stddev_w, 3)},
                "timing_ms_mean": timing_w,
                "total_passed": total_w_passed,
                "total_assertions": total_assertions,
                "eval_results": summary_with,
            },
            "without_skill": {
                "pass_rate": {"mean": round(mean_wo, 3), "stddev": round(stddev_wo, 3)},
                "timing_ms_mean": timing_wo,
                "total_passed": total_wo_passed,
                # Its own denominator. This carried the with_skill total, so the baseline
                # arm reported 77 of 640 when it had 193 -- and the skill-versus-baseline
                # delta divides by it, so the headline comparison was computed against a
                # population the baseline was never measured on.
                "total_assertions": wo_assertions,
                "eval_results": summary_without,
            },
            "delta": {
                "pass_rate_mean_delta": round(mean_w - mean_wo, 3),
                "overall_pass_rate_delta": round((total_w_passed - total_wo_passed) / total_assertions, 3),
                "summary": f"Skill adds +{(mean_w - mean_wo)*100:.1f} percentage points in assertion pass rate across all {len(eval_items)} fixtures.",
            },
        },
    }
    benchmark_file.write_text(json.dumps(benchmark_data, indent=2), encoding="utf-8")
    print(f"\nUpdated: {benchmark_file.relative_to(skill_dir)}")
    if stale:
        print("\nBenchmark status: STALE - stored verdicts do not cover the current assertions.")
        print(f"{len(stale)} of {len(eval_items)} evals need a fresh run:\n")
        for s in stale:
            print(f"  {s['eval']}")
            for r in s["reasons"]:
                print(f"    - {r}")
        print("\nThe pass counts above are the previous run's, re-reported. They are not")
        print("evidence for the current assertion set. Re-run those evals to refresh them.")
    else:
        print("Benchmark status: Verified and up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
