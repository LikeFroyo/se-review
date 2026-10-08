"""Run se-review evals and record verdicts that bind to assertion text.

Why this exists: 102 of the 156 grading.json files in iteration-1 predate
assertion-text capture, so their pass counts cannot be tied to any assertion.
`grade_evals.py` reports those as stale. This script produces grading.json that
always carries the assertion text, which is what makes a verdict checkable.

Two conditions, one mechanism. `with_skill` runs with the skill root as the
working directory, so the skill is discoverable. `without_skill` copies the
fixture into a throwaway directory and runs there, so the skill is physically
absent - which is the only way to get a baseline that has not read the rubric.

Integrity checks, because a mislabelled run is worse than no run:
  - with_skill is rejected unless the event stream shows the skill was actually
    read, so a silent no-skill review cannot be filed as with_skill.
  - the grader returns pass/fail positions only; the assertion text is attached
    from evals.json here, so a grader cannot corrupt it.
  - a grading reply whose length does not match the assertion count is discarded,
    never written.

This script never invents a verdict. A failed run writes no grading.json.

Usage:
  python scripts/run_evals.py --condition both --limit 2
  python scripts/run_evals.py --condition with_skill --eval 79
  python scripts/run_evals.py --condition both --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_registry import eval_name  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parent.parent

# This harness runs a review through an external session runner and deliberately
# names none. Everything runner-specific -- the executable, the subcommand, the
# output format, whether auto-approval is granted, whether the session is isolated
# -- is supplied by the operator, so the repository carries no vendor name and the
# harness is not welded to one tool. Defaults match the runner this was developed
# against; override any of them to point at another.
RUNNER_ENV = "SE_EVAL_RUNNER"
RUNNER_SUBCOMMAND = ("run",)
RUNNER_OUTPUT_FORMAT = "json"
RUNNER_AUTO_FLAG: tuple[str, ...] = ()
# A tuple, not a string. `*RUNNER_ISOLATION_FLAG` on a str unpacks one argv entry
# per character, so the harness was passing `- - s t a n d a l o n e` and the flag
# it appeared to request was never sent at all -- the runner swallowed the
# characters into its variadic message instead. Nothing failed: the run proceeded,
# with a corrupted prompt, and reported no isolation while claiming to ask for it.
RUNNER_ISOLATION_FLAG = ("--standalone",)
# A read of any of these during a with_skill run proves the rubric was consulted.
SKILL_MARKERS = ("SKILL.md", "leaf.md", "shared/severity-and-rules.md", "shared/output-format.md")

GRADER_INSTRUCTIONS = """You are grading a code review against a fixed assertion list. For each assertion, decide whether the review satisfies it.

Rules:
- Judge only what the review actually says. Do not reward intent, and do not
  infer a finding the review did not report.
- Absence is a claim about the whole document, so it needs a search behind it.
  Before recording that the review does not contain something, look for it: a
  severity label, an axis code, a count, a quoted heading. Measured on one review
  graded twice under a single prompt, one attempt recorded that the review "never
  uses [MAJOR]" and "contains no axis labels at all" while the other quoted the
  finding's own heading, "### [MAJOR]", and the line below it, "Domain:
  Correctness (A3 — Data)". If you did not search, say so in the evidence rather
  than reporting an impression as a reading.
- An assertion beginning "Output does NOT" or "Does NOT" passes when the review
  stayed away from that behaviour.
- There is a difference between a review that stayed away from something and a review
  that never went near it, and only the first satisfies a constraint. An assertion that
  asks the review to demonstrate something -- that each finding carries a scenario, that
  findings are graded at a level, that a count is right -- is not answered by a review
  that reports no findings. That is silence, not compliance. Measured: a review whose
  header read "0 findings" and whose findings section read "None" was awarded 7 of 8
  assertions on one fixture, four of them because there was nothing present to fail.
  Where the review demonstrated nothing and the assertion asked for a demonstration, do
  not award it; say in the evidence that the assertion went unaddressed.
- If the review is cut off or unreadable, mark the remaining assertions false and
  say so in the evidence.
- Evidence is one short sentence naming the specific part of the review that
  decided it.

Reply with ONLY a JSON array, one object per assertion, in the order given, with
exactly two keys: "passed" (boolean) and "evidence" (string). No prose, no code
fence, no commentary."""


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_runner() -> str:
    """The executable that runs a review session. Named by the operator, not here.

    This harness is deliberately tool-agnostic. An earlier version resolved one
    specific CLI by name and hardcoded it in the source, which put the tool's name
    into this repository's scripts, its help text, its error messages and its
    environment variables. That is a vendor name in a tree whose instruction files
    name no vendor -- and it also welded the harness to a single runner.

    So the runner comes from the environment: a bare executable name resolved on
    PATH, or an absolute path. Nothing is assumed and nothing is named here.
    """
    override = os.environ.get(RUNNER_ENV)
    if not override:
        raise RuntimeError(
            f"{RUNNER_ENV} is not set. This harness runs reviews through an external "
            f"session runner and deliberately does not name one. Set {RUNNER_ENV} to an "
            f"executable on PATH, or to an absolute path."
        )
    if os.path.sep in override:
        if not os.path.isfile(override):
            raise RuntimeError(f"{RUNNER_ENV} points at {override}, which is not a file")
        return override
    found = shutil.which(override)
    if not found:
        raise RuntimeError(f"{RUNNER_ENV}={override!r} was not found on PATH")
    return found


def stream_errors(stream: str) -> list[str]:
    """Provider and transport errors the CLI reports as events, not as stderr.

    A session runner writes failures into stdout as `{"type":"error", ...}` and
    exits non-zero with an *empty* stderr. A rate limit therefore surfaced as a bare
    exit code and nothing else, which is how a quota wall got mistaken for a broken
    harness. The reason is always in the stream; it just was not being read.
    """
    found = []
    for line in stream.splitlines():
        line = line.strip()
        if not line or '"error"' not in line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") != "error":
            continue
        err = ev.get("error") or {}
        kind = err.get("type") or "error"
        msg = err.get("message") or ""
        status = err.get("status")
        found.append(f"{kind}{f' {status}' if status else ''}: {msg}".strip())
    return found


# G7: the judge decides every number in this repository and has never itself been
# audited. Four synthetic bodies assert the judge's floor behaviour. They run against
# stored review text with no reviewer call, no workspace and no replicate, so they fit
# inside a closed quota -- and a judge that passes any of them is inflating every
# aggregate above it.
JUDGE_SELFTEST_REPS = 3

JUDGE_PROBES = (
    ("empty", "", "fails every assertion: there is no review to grade", None, None),
    # The adversarial case, and the one a judge is most likely to wave through: the
    # review is confident, well-formatted, quotes a file and a line, and claims the
    # code is clean. On a judge that has been asked "does this review satisfy these
    # assertions" with no instruction about opposing content, a plausible-shaped
    # answer can read as a satisfied one. Measured: this is the only probe of the
    # four that the judge failed, so it is the probe worth keeping.
    ("declines",
     "### Findings\n\nNone. The code is exemplary and free of defects.\n\n"
     "Reviewed `clean.py` in full. No defects found; nothing to report.\n\n"
     "## Aligns well\n- Clear structure and honest error handling.",
     "fails every assertion: a confident, well-formed report claiming no defects is "
     "not a report that satisfies an assertion expecting one", None, None),
    ("inverted",
     "### Findings\n\nNone. The code is exemplary and free of defects.",
     "fails every assertion that expects a finding: it asserts the opposite", None, None),
    ("wrong-severity",
     "### Findings\n\n#### [INFO / SUGGESTION] <root cause>\n"
     "- **Domain:** Security (S1)\n"
     "- **Verified by:** READ\n"
     "- **Evidence:** `a.py:1`\n- **Fix:** Delete it.",
     "fails assertions expecting MAJOR or above: a real defect graded Info is not found",
     None, None),
    # The substance probe, and the one the four above could never be. Each of those
    # passed the judge the literal string "probe 0" as its assertion, so it could only
    # measure polarity -- whether the judge awards anything at all -- and never whether
    # the judge can read a real review and find what is in it. Four probes, three
    # replicates, all correct, verdict TRUSTED, and not one of them touched a
    # substantive judgement. TRUSTED was printed as if it had.
    #
    # This one carries real assertions over real text, and it is the exact pair the
    # reproducibility run disagreed about: the same review graded twice, one attempt
    # concluding the severity label was absent while the other quoted it. A judge that
    # reads properly awards exactly 2. One that infers absence from a first impression
    # awards 0; one that waves everything through awards 3. Polarity cannot tell those
    # apart -- and under the old bar, awarding nothing was a clean pass.
    ("labels-present",
     "### [MAJOR] Cache is invalidated by every write, so reads never hit a warm entry\n"
     "- **Domain:** Correctness (A3 — Data)\n"
     "- **Verified by:** READ\n"
     "- **Evidence:** `store.py:41`\n"
     "- **Fix:** Delete the per-write invalidation and let the entry expire on its own.\n",
     "awards 2 of 3: the severity label and the axis attribution are present, and the "
     "summary section is not. A judge answering 'no axis labels at all' has asserted "
     "absence without searching for it",
     ["The finding is graded MAJOR",
      "The finding is attributed to an axis code",
      "The report carries a summary of what aligns well"],
     2),
    # The vacuity probe, added after this was measured rather than imagined. On a real
    # fixture a review whose header read "0 findings" and whose findings section read
    # "None" collected 7 of 8 assertions: four because there was nothing present to
    # fail, three because the report carried the expected headings. Honest reporting
    # scored 1 of 8. The corpus therefore paid for silence, and the judge recorded
    # vacuity as compliance.
    #
    # The body below is deliberately well formed and confident, and names the right
    # sections, so a failure here cannot be blamed on shape or fluency -- only on
    # granting a pass for something the review never did.
    ("vacuous",
     "### Findings\n\nNone.\n\n"
     "`0 findings \u00b7 C:0 M:0 m:0 i:0 \u00b7 Mean 100/100 \u00b7 Final Grade A`\n\n"
     "## Aligns well\n"
     "- Bounded, timed retries with jitter and a per-attempt timeout.\n"
     "- Minimal, cohesive module, no dead surface.\n\n"
     "Gated by: neither \u2014 Grade A reached\n",
     "awards 0 of 3: a review reporting no findings cannot demonstrate anything. The "
     "previous prompt collected four vacuous passes from exactly this shape on a real "
     "fixture, so silence scored higher than reporting",
     ["Each finding above Info severity cites a demonstrable failure scenario",
      "Every finding above Info severity is graded MINOR, not Major or Critical",
      "The non-retryable-4xx retry bypass IS reported as a finding"],
     0),
)


def _one_judge_probe(body: str, model: str | None,
                     assertions: list[str] | None = None,
                     expect_awards: int | None = None) -> dict:
    """Grade one probe body once. Returns a state dict; never raises.

    A transport failure is NOT a judge result. Reporting one as a verdict turns a
    closed quota or a slow model into four confident findings the judge never made,
    and a quota wall is indistinguishable from an untrustworthy judge unless the two
    are kept apart.
    """
    try:
        verdicts = grade(body, assertions or [f"probe {i}" for i in range(3)], 180,
                         Path(tempfile.mkdtemp()), model)
        failures = sum(1 for v in verdicts if v["passed"])
        # The probe passes when the judge awarded it NOTHING. Asking "was the count
        # more than zero" has the polarity backwards: a correct judge passes zero,
        # which is the entire point of the probe.
        #
        # Given real assertions the bar is an exact count instead, and exactness is the
        # point: a judge that finds nothing and one that finds everything are both wrong
        # here, and only the count separates them. Zero was the polarity probe's idea of
        # correct, which is exactly why it passed the defect this probe exists to catch
        # -- "the review contains no axis labels at all" awards nothing at all.
        # POLARITY, and it is the entire meaning of this function. `failed_it` is "the
        # judge failed it" -- the judge resisted the bait, which is SUCCESS. The original
        # line was `failures == 0`, so a judge that correctly awarded nothing reads True.
        # Writing the exact-count branch as `!=` marks a judge that answered precisely
        # right as defective, and did: the substance probe awarded 2 of 2 expected, all
        # three replicates, and the battery reported UNTRUSTED. That is the one error
        # this instrument must never make -- it is the error it exists to prevent.
        failed_it = (failures == 0 if expect_awards is None
                     else failures == expect_awards)
        return {"failed_it": failed_it, "passed": failures, "why": None}
    except (subprocess.TimeoutExpired, TimeoutError) as exc:
        return {"failed_it": None, "passed": None,
                "why": f"not run: {type(exc).__name__} after {exc.timeout}s"}
    except RuntimeError as exc:
        detail = str(exc)
        if is_rate_limited([detail]) or is_transient(detail):
            return {"failed_it": None, "passed": None, "why": "not run: " + detail[:120]}
        # Declined to grade, or answered unparseably. Neither a pass nor a fail: for
        # an empty review that is defensible, for an inverted one it is a gap. Kept as
        # its own state so it cannot be read either way.
        return {"failed_it": None, "passed": None,
                "why": "judge did not return a gradeable verdict: " + detail[:120]}
    except Exception as exc:
        return {"failed_it": False, "passed": -1, "why": f"raised {type(exc).__name__}"}


def _fold_judge_probe(name: str, expectation: str, attempts: list[dict],
                       expect_awards: int | None = None) -> dict:
    """One probe over several attempts. Disagreement is a result, not noise.

    A single sample cannot separate a judge defect from judge variance, and this
    repo already knows that difference is unmeasured -- it is the replicate gap. So
    the probe reports both: what the judge did on each attempt, and whether it did
    the same thing every time.
    """
    ran = [a for a in attempts if a["failed_it"] is not None]
    if not ran:
        return {"probe": name, "judge_failed_it": None, "attempts": len(attempts),
                "agreed": None, "assertions_passed_by_probe": None,
                "expectation": expectation,
                "expect_awards": expect_awards,
                "why": attempts[0]["why"] if attempts else "no attempt"}
    # An attempt that produced no grade counts AGAINST reproducibility, never as a
    # neutral. Dropping it before computing agreement is how a malformed reply that
    # graded everything true gets discarded by two correct siblings and reported as a
    # clean pass -- the instrument hiding the defect it was built to find.
    no_grade = [a for a in attempts if a["failed_it"] is None]
    fails = sum(1 for a in ran if a["failed_it"])
    # Disagreement is over the award vector, not merely the probe's own verdict. Two
    # attempts can reach the same verdict by counting differently -- 2 of 3 twice is
    # reproducible, 2 of 3 then 3 of 3 is not, and only the vector shows which happened.
    graded_disagree = len({(a["failed_it"], a["passed"]) for a in ran}) > 1
    agreed = not graded_disagree and not no_grade
    return {
        "probe": name,
        "judge_failed_it": fails == len(ran),
        "attempts": len(attempts),
        "agreed": agreed,
        "assertions_passed_by_probe": sorted({a["passed"] for a in ran if a["passed"] is not None}),
        "expectation": expectation,
        "expect_awards": expect_awards,
        "why": None if agreed else (
            f"{len(no_grade)} of {len(attempts)} attempts produced no gradeable verdict; "
            "reproducibility is not established"
            if no_grade else
            "judge disagreed with itself across attempts"
        ),
    }


def _judge_verdict(results: list[dict], total: int) -> dict:
    ran = [r for r in results if r["judge_failed_it"] is not None]
    unstable = [r["probe"] for r in ran if not r["agreed"]]
    clean = [r["probe"] for r in ran if r["agreed"] and r["judge_failed_it"]]
    broken = [r["probe"] for r in ran if r["agreed"] and not r["judge_failed_it"]]
    if not ran:
        verdict = "NOT RUN"
    elif broken:
        verdict = "UNTRUSTED"
    elif unstable:
        # Every attempt that produced a verdict was correct, but the judge is not
        # reproducible. That is a variance finding about the instrument, and calling
        # it UNTRUSTED would blame the judge for the harness's missing replicates.
        verdict = "UNSTABLE"
    elif len(ran) == total:
        verdict = "TRUSTED"
    else:
        verdict = "PARTIAL"
    return {
        "probes_run": f"{len(ran)} of {total}",
        "verdict": verdict,
        "probes_correct": clean,
        "probes_defective": broken,
        "probes_unstable": unstable,
        "note": "NOT RUN means the judge could not be reached, which is not the same as the "
                "judge being untrustworthy. UNSTABLE means every graded attempt was correct "
                "but the judge did not reproduce itself -- a variance finding, not a defect. "
                "An attempt that returned no gradeable verdict counts against reproducibility: "
                "an unparseable reply is evidence about the judge, not a missing data point.",
    }


def judge_selftest(model: str | None = None, reps: int = JUDGE_SELFTEST_REPS,
                   only: list[str] | None = None) -> dict:
    """Can the judge fail? A grader that cannot say no cannot be trusted to say yes.

    Runs against stored review text: no reviewer call, no workspace, no fixture, no
    replicate of a review. Reports the verdict rather than raising, so the result is
    recorded beside the other measurements instead of stopping whatever run
    happened to trigger it.
    """
    # An unmatched filter is a typo, and a typo that silently runs nothing would report
    # NOT RUN -- which reads as "the judge could not be reached" rather than "you asked
    # for a probe that does not exist". Refuse instead.
    known = {pr[0] for pr in JUDGE_PROBES}
    unknown = sorted(set(only or []) - known)
    if unknown:
        raise SystemExit(f"no such judge probe: {', '.join(unknown)}\n"
                         f"available: {', '.join(sorted(known))}")
    chosen = [pr for pr in JUDGE_PROBES if not only or pr[0] in only]
    results = [
        _fold_judge_probe(name, expectation,
                          [_one_judge_probe(body, model, assertions, expect_awards)
                           for _ in range(max(1, reps))], expect_awards)
        for name, body, expectation, assertions, expect_awards in chosen
    ]
    return {"JUDGE SELFTEST": results, **_judge_verdict(results, len(chosen))}


RATE_LIMITED = ("quota", "429", "rate limit", "usage limit", "too many requests")


def is_rate_limited(messages: list[str]) -> bool:
    blob = " ".join(messages).lower()
    return any(marker in blob for marker in RATE_LIMITED)


# Session identity inherited from whatever launched the sweep. An eval run must
# not join the orchestrating agent's session: that session is rooted at the real
# repository, and the reviewer lands there instead of in the workspace, reads the
# fixture from the real tree, and then reads `evals/evals.json` and the recorded
# verdicts -- the answer it was being compared against. This was invisible for
# every earlier run because the sweep was always launched from a shell without
# these set, and it appeared the moment the harness was driven from inside an
# agent session, which is the normal way to run it.
# Session identity inherited from whatever launched the sweep. Names are matched by
# suffix so no tool is named here: any variable ending in these fragments belongs to
# an agent session, not to the harness.
INHERITED_SESSION_ENV_SUFFIXES = ("SESSION_ID", "AGENT_ID", "AI_AGENT")

# Directory names that identify a harness or its caches rather than what it touched.
TOOLING_DIRS = {"node_modules", ".cache", ".npm", ".local", ".cargo", ".gradle"}


def eval_env() -> dict[str, str]:
    """The ambient environment minus any inherited agent session identity.

    Matched by variable-name suffix rather than an explicit list, so no tool is
    named and a differently-branded session is still stripped. An eval run must
    never join the session that launched it: that session is rooted wherever the
    operator's work is, and a reviewer that joins it reads the answer key from the
    real repository instead of the staged workspace.
    """
    env = dict(os.environ)
    for key in list(env):
        if any(key.endswith(sfx) for sfx in INHERITED_SESSION_ENV_SUFFIXES):
            env.pop(key, None)
    return env


# Transient upstream failures are not the run's fault and must not be recorded as
# one. A 502 from a provider mid-sweep is the difference between a measured arm
# and a missing one, and retrying is the whole difference.
TRANSIENT_MARKERS = ("502", "500", "503", "504", "upstream error", "timeout",
                     "connection reset", "eof", "stream")
MAX_ATTEMPTS = 3
RETRY_BACKOFF_S = 5


def is_transient(detail: str) -> bool:
    blob = detail.lower()
    if is_rate_limited([detail]):
        return False
    return any(marker in blob for marker in TRANSIENT_MARKERS)


def run_model(
    message: str,
    work_dir: Path,
    timeout: int,
    model: str | None = None,
    attempt: int = 0,
) -> tuple[str, str]:
    """Run one non-interactive review session. Returns (text, raw_event_stream)."""
    proc = subprocess.run(
        [
            resolve_runner(), *RUNNER_SUBCOMMAND, message,
            "--format", RUNNER_OUTPUT_FORMAT,
            # No permission prompt can be answered in a non-interactive run, and a
            # denied read ends the session before it produces a review. Everything
            # the reviewer needs is already staged into the workspace.
            # Deliberately NOT --auto. Auto-approval grants every permission the
            # session can hold, including reads outside the workspace, so the
            # reviewer could reach the real repository and the answer key. The
            # default denies those instead: measured, a run without --auto made
            # zero attempts outside its workspace while completing its nine
            # in-workspace reads. Denials surface as tool errors, which are
            # recorded in plumbing.json without discarding a review that exists.
            # A private server per invocation. Without it the run joins the
            # background service, which carries its own project root -- the real
            # repository -- and the reviewer lands there regardless of the
            # directory argument. Observed: the baseline read the fixture from the
            # real tree, walked up, and opened the with_skill grading.json and
            # review.md, i.e. the answer it was being compared against. Passing
            # the directory is not enough on its own; this is what makes it hold.
            *RUNNER_ISOLATION_FLAG,
            # The workspace is a trailing POSITIONAL argument, not a flag: `run`
            # takes no --dir. Passing cwd alone is not enough -- with no directory
            # argument the runner falls back to a default project, and a reviewer
            # that lands in the real repository reads evals/evals.json, the answer
            # key. The contamination gate caught exactly that. Naming the directory
            # is what makes the staging true rather than merely intended.
            *(["-m", model] if model else []),
            # LAST, and this ordering is load-bearing. `run` takes a *variadic*
            # positional message, so a directory placed before `-m <model>` is
            # swallowed into the message and never applied as the project at all.
            # runner then falls back to its default project -- the real
            # repository -- and the reviewer reads the fixture and the recorded
            # verdicts from there. Observed exactly that: the baseline's first
            # tool call was an absolute path into the real tree. The workspace,
            # the git seal and --standalone were all correct and none of it
            # mattered, because the project was never set to the workspace.
            str(work_dir),
        ],
        cwd=str(work_dir),
        env=eval_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        # Prefer the stream's own reason. Falling back to stderr alone reports an
        # empty string for every provider-side failure, which is indistinguishable
        # from a broken executable and cost one full sweep to diagnose.
        reasons = stream_errors(proc.stdout)
        detail = "; ".join(reasons) if reasons else (proc.stderr.strip() or "no error text emitted")
        if is_transient(detail) and attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_BACKOFF_S * (attempt + 1))
            return run_model(message, work_dir, timeout, model, attempt=attempt + 1)
        raise RuntimeError(f"runner exited {proc.returncode}: {detail[:400]}")
    return extract_text(proc.stdout), proc.stdout


def tool_errors(stream: str) -> list[dict]:
    """Tool calls that returned an error, e.g. a denied write.

    A denied tool can end the run before the model produces its answer. Without
    this check the truncated output is graded like a real review and recorded
    as a genuine zero, which reads downstream as a broken task.
    """
    errors: list[dict] = []
    for line in stream.splitlines():
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
        if state.get("status") == "error":
            errors.append({"tool": event.get("part", {}).get("tool"), "error": str(state.get("error"))[:200]})
    return errors


def looks_like_report(review: str) -> bool:
    """True when the output actually contains a review, not just preamble.

    The question is whether the run produced substance, not whether it produced
    the *skill's* shape. Those are different tests, and conflating them made the
    baseline arm unmeasurable: `without_skill` stages no skill, so the reviewer
    has no template and will not emit `## Findings` or a `C:<n>` tally -- and
    requiring them rejected a correct 2,464-character review of the accumulator
    against its constraint document, discarding it as "no review body".

    A baseline that imitates the skill's report format is a baseline that has
    been contaminated in the other direction, so the shape cannot be the test.

    What is left is a substance test: enough text, and at least one citation of
    the code under review or a named finding. Preamble and truncation fail both.
    """
    body = review.strip()
    # Shape first, and decisively: a report that carries the mandatory findings
    # section and a graded finding IS a report, whatever its length. The length
    # floor exists to catch preamble and truncation in output that has no
    # recognisable shape, so applying it to shaped output rejects a short but
    # complete report -- found by the test suite, on the same day it was written.
    skill_shaped = (
        "## Findings" in body
        or "### [CRITICAL]" in body
        or "### [MAJOR]" in body
        or bool(re.search(r"\bfindings\b.*\bC:\d+", body, re.S))
    )
    if skill_shaped:
        return True
    if len(body) < 400:
        return False
    # Arm-agnostic: a review names its subject and says something about it.
    subject = re.search(r"`[^`]+\.(?:py|js|ts|go|rb|java|rs|md)`|\bline \d+", body)
    substance = re.search(
        r"\b(bug|race|risk|fails|incorrect|wrong|violation|violates|broke|"
        r"missing|unsafe|deadlock|leak|not\s+guaranteed|compliant|violation)\b",
        body,
        re.I,
    )
    return bool(subject and substance)


def extract_text(stream: str) -> str:
    """Concatenate assistant text parts out of the NDJSON event stream."""
    chunks: list[str] = []
    for line in stream.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "text":
            text = event.get("part", {}).get("text")
            if text:
                chunks.append(text)
    return "\n".join(chunks).strip()


# Top-level entries a stored path can be relativised against. Used to migrate
# verdicts recorded on another machine, where the absolute prefix is unknown and
# unresolvable from here -- a Windows path is not absolute on POSIX and vice
# versa, so the prefix has to be matched by tail rather than resolved.
# Directory names that identify the harness rather than what it touched.

REPO_TOPLEVEL = (
    "domains", "shared", "project-tree", "auditandevolve", "scripts",
    "evals", "SKILL.md", "README.md",
)


def redact_foreign(raw: str) -> str:
    """Keep the last two segments of a path from another machine.

    Once a path is known to be outside the repository, its prefix carries no
    information a reader needs and a great deal they should not have: a username,
    a temp directory layout, a project name. `C:\\Users\\a-user\\AppData\\Local\\Temp\\...`
    becomes `.../<harness>/...`, which still identifies what was touched.
    """
    parts = [seg for seg in raw.replace("\\", "/").split("/") if seg]
    # Drop a leading tooling directory. Once a path is known to be outside the
    # repository, naming the tool that reached it adds nothing a reader needs and
    # identifies the harness to anyone auditing this evidence.
    while len(parts) > 1 and parts[-2].lower() in TOOLING_DIRS:
        parts.pop(-2)
    if len(parts) <= 2:
        return "/".join(parts)
    return ".../" + "/".join(parts[-2:])


def relativise_foreign(raw: str) -> str | None:
    """Relativise a path recorded on a different machine, by matching its tail.

    `C:\\Users\\a-user\\repo\\shared\\output-format.md` becomes
    `shared/output-format.md`. No prefix is resolved, so this works for a path
    from any OS and any directory layout. Returns None when no known top-level
    entry appears in the path, which means it was never inside the repository and
    is left alone.
    """
    normalised = raw.replace("\\", "/")
    parts = [seg for seg in normalised.split("/") if seg]
    # The repository root is a real thing a run reads -- it is how a directory
    # listing of the workspace gets recorded -- and it matches no top-level entry.
    if parts and parts[-1] == SKILL_ROOT.name:
        return "./"
    for index, seg in enumerate(parts):
        if seg in REPO_TOPLEVEL:
            tail = "/".join(parts[index:])
            if seg in ("SKILL.md", "README.md") and index != len(parts) - 1:
                continue
            return tail
    return None


def read_paths_and_patterns(stream: str) -> tuple[list[str], list[str]]:
    """What the run touched: (paths, search patterns).

    Two lists because they are different things and conflating them made
    `files_read` a field that could not mean anything. A grep's *pattern* -- a
    brace glob like `{README.md,CONTRIBUTING.md,*.md}`, or an alternation
    like `nplusone|n\\+1|NPlusOne` -- is not a file that was read, and one
    committed verdict listed thirteen such strings under `files_read`.

    The paths stay absolute here. The contamination gate needs the raw form to
    recognise an escape, and `relativise` happens only at write time.
    """
    paths: list[str] = []
    patterns: list[str] = []
    for line in stream.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "tool_use":
            continue
        inputs = event.get("part", {}).get("state", {}).get("input", {}) or {}
        for key in ("filePath", "path"):
            value = inputs.get(key)
            if isinstance(value, str) and value not in paths:
                paths.append(value)
        pattern = inputs.get("pattern")
        if isinstance(pattern, str) and pattern not in patterns:
            patterns.append(pattern)
        # A shell reads files too, and in this corpus that is how it mostly reads them:
        # one run made three `read` calls, all of which errored, then read the fixture
        # with `cat`, listed it with `ls`, and opened it again from `python3`. The gate
        # saw none of it. A reviewer could `cat` the answer key and pass.
        #
        # Only paths that could actually reach the key are harvested, never every path in
        # the command: a reviewer running python3 legitimately touches /usr/lib, and
        # flagging that would refuse honest runs until the gate was switched off. So a
        # candidate counts only if it names a forbidden entry or sits under this
        # repository -- which is the whole threat and nothing else.
        command = event.get("part", {}).get("tool") == "shell" and inputs.get("command")
        if isinstance(command, str):
            for token in re.findall(r"[\w./@%+-]{4,}", command):
                # Both lists, not just the names: `ls evals/iteration-1/` is how you read
                # a recorded verdict without touching evals.json, and a filter that only
                # knew the names waved it through.
                #
                # Names match anywhere in the token; directories must match a whole path
                # component. Substring matching on directories flagged this repository's
                # own path -- `/Users/.../repo/domains/` contains "review",
                # because the project is called se-review -- so every honest mention of
                # the repo root was harvested as a forbidden read. It reached the right
                # verdict by accident and for the wrong reason, which is worse than not
                # reaching it: the next rename would have silently disarmed the check.
                # Either one is enough. An AND would match nothing: `evals/iteration-1`
                # names no forbidden *file*, and `evals.json` sits in no forbidden
                # *directory*, so requiring both silently disarmed the whole check.
                name_hit = any(bad in token for bad in FORBIDDEN_NAMES)
                dir_hit = bool(set(token.split("/")) & set(FORBIDDEN_DIRS))
                if not (name_hit or dir_hit):
                    continue
                if token not in paths:
                    paths.append(token)
    return paths, patterns


def files_read(stream: str) -> list[str]:
    """Raw paths passed to a read/glob/grep tool. Absolute, for the gates."""
    return read_paths_and_patterns(stream)[0]


def isolation_gate(stream: str, work_dir: Path) -> tuple[bool, str, list[str], int]:
    """Can this run prove the reviewer stayed somewhere the answer key is not?

    Contamination answers a narrower question: did the reviewer actually reach a forbidden
    entry? That is necessary and it is not sufficient, because the runner pins every
    session to the real repository regardless of the process working directory, the
    trailing positional, `--standalone`, the git seal, or a project marker in the
    workspace. Measured four ways. So a reviewer that never opened `evals/evals.json` has
    still been sitting next to it, and "it did not read the key" is not "it could not".

    Proof therefore has to be constructive rather than negative. Three conditions, and a
    run that meets none of them is not isolated for want of evidence:

    Every recorded access is under this run's own workspace. A path anywhere else means
    the reviewer was somewhere the key may be.

    No access names a forbidden entry. That is the contamination check, repeated here so
    this gate stands on its own and cannot be satisfied by a caller that skipped the other.

    No shell command runs without naming the workspace by absolute path. This is the
    condition that actually bites. The shell tool's working directory is the runner's
    choice, not ours, so a relative `cat evals/evals.json` is executed wherever the
    runner decided -- which is the real repository, where the file exists. There is no way
    to ask the shell where it is without spending a call on asking, and inferring it from
    a command that was never given is exactly the kind of assumption this repository
    keeps refusing.
    """
    root = str(work_dir)
    paths, patterns = read_paths_and_patterns(stream)
    # A recursive search pattern is a read of everything beneath it, which is the answer
    # key included. The pattern list was discarded here, so a command naming the
    # workspace once and sweeping `**/*` satisfied the absolute-path condition while
    # reading the whole tree -- the gate passed a run that swept for the key.
    # A recursive search is only dangerous if it can reach the key, and the workspace holds
    # the staged surface and the fixture and nothing else, so it cannot. Refusing every
    # sweep was the same over-strict proxy in a second disguise: sixteen of twenty-one
    # refusals in one sweep were a reviewer globbing its own workspace, which is what
    # working isolation invites. A sweep that does not root at the workspace is still
    # refused, because that one is running somewhere else.
    #
    # The tuple shape matters and was wrong here once: `return False, (a, b, c)` is a
    # 2-tuple whose second element is a 3-tuple, so the caller's four-way unpack would
    # have raised rather than refused.
    for pattern in patterns:
        if pattern.strip() not in SWEEP_PATTERNS:
            continue
        rooted = any(root in line for line in stream.splitlines() if line.strip())
        if not rooted:
            return (False,
                    f"ran a recursive search ({pattern!r}) that is not rooted at this "
                    f"run's workspace, so it can reach the answer key",
                    paths, 0)
    for path in paths:
        if any(bad in path for bad in FORBIDDEN_NAMES):
            return (False,
                    f"reached a forbidden entry: {portable_path(path, work_dir)}",
                    paths, 0)
        if set(path.split("/")) & set(FORBIDDEN_DIRS):
            return (False,
                    f"reached a forbidden directory: {portable_path(path, work_dir)}",
                    paths, 0)
    for path in paths:
        try:
            Path(path).resolve().relative_to(work_dir.resolve())
        except (ValueError, OSError):
            return (False,
                    f"read outside this run's workspace: "
                    f"{portable_path(path, work_dir)}",
                    paths, 0)

    # The old fourth condition -- every shell command had to name the workspace by absolute
    # path -- was a *proxy*, adopted because the shell's working directory was the real
    # repository and nothing could be done about it. It refused honest runs: a reviewer
    # working correctly inside its own workspace may `wc -l` a relative path, and that is
    # not contamination. Measured after the flag was fixed, it refused a run that had made
    # eight reads and was nowhere near the key.
    #
    # The proxy is retired because its reason is gone. Isolation works, so a relative path
    # resolves inside the workspace, and the question worth asking -- did this run reach
    # the key -- is now directly observable, because shell reads are harvested. If it did,
    # the first loop refuses it. What is no longer needed is a guess about where the shell
    # was standing.
    indirect = 0
    for line in stream.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = event.get("part") or {}
        if event.get("type") != "tool_use" or part.get("tool") != "shell":
            continue
        command = (part.get("state") or {}).get("input", {}).get("command")
        if isinstance(command, str) and root not in command:
            indirect += 1
    return True, "", paths, indirect


# Machine-specific path prefixes have no business in committed evidence. A temp
# directory names the machine and the run; a home directory names the operator. Both were
# committed: a review body quoting `the staged workspacese-run-eval-...` and plumbing
# `reads` arrays holding `/Users/<name>/siderepo/...`, the latter because a contaminated run
# reached into the real repository and the read was recorded verbatim.
#
# The *fact* of a read outside the workspace is the evidence. The path that got there is
# not, so it is reduced to a stable prefix and the meaningful tail. Nothing is discarded:
# `repo/evals/evals.json` still says exactly what the old absolute path said, and it says
# it identically on any machine.
PATH_PREFIXES = (
    ("/private/var/folders/", "<tmp>/"),
    ("/var/folders/", "<tmp>/"),
    ("/private/tmp/", "<tmp>/"),
)


def portable_path(path: str, work_dir: Path | None = None) -> str:
    """Reduce a path to something true on any machine.

    Three finished shapes, chosen so no rewrite loses meaning: inside this run's workspace
    a path becomes `ws/...`; inside this repository it is prefixed `repo/...`; anything
    else keeps its last two components under `outside/...`.

    Two failure modes shaped this, both found by running the scrub twice:

    Temporary paths needed their own case. A macOS per-user temporary root is
    `/var/folders/<uid>/<per-user hash>/T/...` and both of those components identify the
    machine and the account. Stripping only the `/private/var/folders/` prefix -- the first
    version -- left the hash in the middle wearing a `<tmp>` hat, which is worse than not
    rewriting it, because it looks handled.

    Nothing relative may be resolved. `Path("<tmp>/...").resolve()` anchors at the current
    directory, so a value that is already reduced resolves *inside this repository* and
    gains a second prefix: `repo/<tmp>/...`. Resolution is therefore attempted only for
    input that was absolute to begin with, and the reduction is idempotent -- a scrub that
    must be run exactly once, correctly, is a scrub that will be run twice.
    """
    text = str(path)
    # A staged workspace, wherever the temporary root is. Checked before anything else
    # because it is the one shape that is unambiguously identifiable and unambiguous.
    m = re.search(r"/T/(se-run-[^/]+)/(.+)$", text)
    if m:
        return "ws/" + m.group(2)

    if text.startswith("/"):
        if work_dir:
            try:
                return "ws/" + Path(text).resolve().relative_to(work_dir.resolve()).as_posix()
            except (ValueError, OSError):
                pass
        try:
            return "repo/" + Path(text).resolve().relative_to(SKILL_ROOT.resolve()).as_posix()
        except (ValueError, OSError):
            pass
    elif text.startswith(("ws/", "repo/", "outside/")):
        return text  # already portable

    for prefix, _ in PATH_PREFIXES:
        if prefix in text:
            parts = [p for p in text.split(prefix, 1)[1].split("/") if p]
            tail = "/".join(parts[-2:]) if len(parts) > 1 else (parts[0] if parts else "")
            return "<tmp>/" + tail if tail else "<tmp>"
    parts = [p for p in text.split("/") if p]
    if not parts:
        return "<path>"
    if len(parts) == 1:
        return "outside/" + parts[0]
    return "outside/" + "/".join(parts[-2:])


def portable_reads(reads: list[str], work_dir: Path | None = None) -> list[str]:
    out = []
    for r in reads:
        p = portable_path(r, work_dir)
        if p not in out:
            out.append(p)
    return out


def sanitise_paths(text: str, work_dir: Path | None = None) -> str:
    """Strip machine-specific prefixes out of a review body, keeping the citation.

    A review legitimately cites `file:line`. It does not legitimately carry the temporary
    directory it was staged into, and committed verbatim that directory names the machine
    and the run. Replacing the prefix with `ws/` preserves the citation exactly -- the
    reviewer did read that file in that workspace -- and makes the evidence portable.
    """
    out = text
    if work_dir:
        out = out.replace(str(work_dir), "ws")
        out = out.replace(str(work_dir.resolve()), "ws")
    out = out.replace(str(SKILL_ROOT), "repo")
    out = out.replace(str(SKILL_ROOT.resolve()), "repo")
    # A staged workspace path: `/private/var/folders/<per-user hash>/<session>/T/se-run-.../`
    # The per-user component is machine-identifying and the session component is noise, and
    # the whole prefix is an artefact of staging rather than anything the reviewer cited,
    # so it collapses to the same `ws/` a live run now writes.
    out = re.sub(r"[^\s`\"']*/T/se-run-[^/\s`\"']+/", "ws/", out)
    for prefix, replacement in PATH_PREFIXES:
        if prefix in out:
            tail = out.split(prefix, 1)[1]
            out = out.split(prefix, 1)[0] + replacement + tail
    # A bare home directory the model quoted without a path we recognise.
    out = re.sub(r"/Users/[A-Za-z0-9._-]+", "home", out)
    return out


def relativise(reads: list[str], workspace: Path | None = None) -> list[str]:
    """Repo-relative POSIX paths, so a verdict is portable and machine-agnostic.

    A committed verdict is evidence about the skill, and evidence that carries
    `C:\\Users\\a-user\\repo\\...` is evidence about one machine: it cannot be
    diffed against a re-run, it cannot be read by anyone else, and it publishes
    the author's username and directory layout. Fifteen verdicts carried 139 such
    paths.

    Resolution order, most specific first: the run workspace (which mirrors the
    repository layout), then the repository root, then anything left over is kept
    verbatim under an `outside:` prefix -- because a path that could not be
    relativised is exactly the interesting one, and hiding it would defeat the
    contamination gate's purpose.
    """
    roots: list[Path] = []
    if workspace is not None:
        roots.append(workspace)
    roots.append(SKILL_ROOT)
    out: list[str] = []
    for raw in reads:
        candidate = Path(raw)
        rendered = None
        # A path recorded on another OS is not resolvable here, and joining it
        # onto a root "succeeds" while producing nonsense: `SKILL_ROOT /
        # "C:\\Users\\a-user\\..."` yields one garbage segment. Recognise it and leave it
        # to the tail matcher instead.
        foreign = ("\\" in raw) or bool(re.match(r"^[A-Za-z]:", raw))
        if foreign:
            out.append(relativise_foreign(raw) or f"outside:{redact_foreign(raw)}")
            continue
        for root in roots:
            try:
                base = root.resolve()
                target = candidate if candidate.is_absolute() else (base / candidate)
                rendered = target.resolve().relative_to(base).as_posix()
                break
            except (ValueError, OSError):
                continue
        if rendered is None:
            rendered = relativise_foreign(raw) or f"outside:{redact_foreign(raw)}"
        out.append(rendered)
    seen: list[str] = []
    for item in out:
        if item not in seen:
            seen.append(item)
    return seen


# Slots the report format declares mandatory. A reviewer that had the format in
# front of it emits them; one working unaided generally does not.
FORMAT_MARKERS = ("Covered:", "Gated by:", "Verified by:", "Unclassified:")


def skill_was_consulted(reads: list[str], review: str = "") -> bool:
    """True when the run can have had the skill in front of it.

    Two ways that happens, and the first check alone misses half of them. The runner
    discovers `SKILL.md` in the project directory and loads it into the system
    prompt, so a `with_skill` run never issues a `read` for it at all -- the file
    read is the wrong instrument. Observed: a run that produced the format
    verbatim, down to `Not examined: 0 — none`, was rejected as "skill never
    read".

    The system prompt is not echoed into the event stream, so the fallback is
    behavioural: the skill's mandatory header slots. Those are a real
    discriminator rather than a circular one, because `without_skill` stages no
    skill and therefore has nothing to copy them from -- which is exactly the
    contrast the baseline arm exists to show.
    """
    if any(marker in path.replace("\\", "/") for path in reads for marker in SKILL_MARKERS):
        return True
    return any(marker in review for marker in FORMAT_MARKERS)


def parse_verdicts(text: str, expected: int) -> list[dict] | None:
    """Pull the grader's JSON array out of a reply. None unless it is well formed."""
    body = text.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)\s*```", body, re.S)
    if fence:
        body = fence.group(1)
    start, end = body.find("["), body.rfind("]")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        parsed = json.loads(body[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list) or len(parsed) != expected:
        return None
    for item in parsed:
        if not isinstance(item, dict) or not isinstance(item.get("passed"), bool):
            return None
        if not isinstance(item.get("evidence"), str):
            return None
    return parsed


def grader_digest() -> str:
    """A digest of the grading instruction itself, recorded in every verdict.

    Without it, replaying a stored verdict answers a different question than it appears
    to. Measured: re-grading two stored reviews flipped 1 of them, and five of eight
    assertions on the other -- but every stored verdict predates any record of which
    prompt produced it, so the comparison is across a prompt change, not across a repeat
    of the same judgement. That is a prompt-version difference reported as judge jitter,
    and it makes the noise floor unmeasurable in the only direction that matters: is this
    judge reproducible *now*.

    The instrument's identity belongs in its verdict for the same reason the model's does.
    Two verdicts graded by different instructions are not comparable however equal their
    numbers, and nothing in the tree could see that.
    """
    # "cfg:", not "grader:". The key already says which instrument this is, and the
    # digest only has to answer "were these the same instructions?". A named prefix
    # would have meant widening the validator's digest rule from cfg:<hex> to any
    # <name>:<hex> -- and a rule that accepts a caller-chosen name accepts a vendor
    # name too. The key disambiguates without loosening anything.
    return "cfg:" + hashlib.sha256(
        GRADER_INSTRUCTIONS.encode("utf-8")).hexdigest()[:12]


def fixture_digests(eval_item: dict, root: Path | None = None) -> dict[str, str]:
    """A content digest for every fixture this eval names.

    A verdict records a fixture *path* and nothing about the bytes at it. So a Phase 4
    round that plants a defect, writes the assertions, runs, and then edits the fixture
    leaves the stored verdict current: the assertion text is unchanged, so
    `grade_evals.py` sees no drift, and the aggregate reports a fresh number over a corpus
    that moved. Measured: 101 stored verdicts name a fixture path and 4 record any digest.

    `evals/README.md` already states the rule as a norm with no mechanism behind it --
    "The fixtures were not edited. Editing a control to raise a score is the move that
    makes a benchmark worthless" -- so this is the missing mechanism, and it is one hash
    per file with nothing to run.
    """
    base = root or SKILL_ROOT
    out: dict[str, str] = {}
    for rel in eval_item.get("files", []) or []:
        path = Path(rel)
        candidates = [base / rel, base / "evals" / "fixtures" / path.name,
                      base / "evals" / "fixtures" / rel]
        for cand in candidates:
            if cand.is_file():
                out[rel] = "sha256:" + hashlib.sha256(cand.read_bytes()).hexdigest()[:16]
                break
        else:
            out[rel] = "absent"
    return out


NO_AXIS_HEADER = re.compile(r"^Unclassified:\s*(\d+)", re.MULTILINE)


def no_axis_count(reps: list[dict]) -> dict:
    """The uncoded-finding count for this run, or null when the header was absent.

    Three outcomes, and the two nulls must never render alike:

      <int>   every replicate stated the header and agreed
      null + "replicates disagreed: <values>"  the count is not stable, so there is
               no single number and averaging them would invent one
      null + "header absent"                   the reviewer did not say

    The third is a required field nobody produced, which `axis-codes.md` names as the
    condition that leaves a reserved code unreviewable. It is recorded so the gap is on
    the record per run, not hidden in a corpus aggregate.
    """
    seen = []
    for rep in reps:
        body = (rep.get("review") or "").strip()
        if not body:
            continue
        match = NO_AXIS_HEADER.search(body)
        if match:
            seen.append(int(match.group(1)))
    if not reps or all(not (rep.get("review") or "").strip() for rep in reps):
        return {"no_axis_count": None, "no_axis_count_reason": "no review body"}
    if not seen:
        return {"no_axis_count": None, "no_axis_count_reason": "header absent"}
    if len(set(seen)) > 1:
        return {"no_axis_count": None,
                "no_axis_count_reason": f"replicates disagreed: {sorted(set(seen))}"}
    return {"no_axis_count": seen[0], "no_axis_count_reason": None}


def already_current(
    grading_path: Path, assertions: list[str], reps: int = 1, base_commit: str | None = None
) -> tuple[bool, str]:
    """Is this stored verdict still evidence about the tree as it stands?

    Returns `(current, reason_if_not)`. The reason names *which* field differed,
    because a silent re-run and a silent skip are indistinguishable from the
    outside and only one of them is a decision anyone can review.

    Two things make a verdict currency, and this function used to check only one of
    them. The assertion text and the replicate count are the obvious pair. The third
    is the tree the review was produced from: a Phase 2 guideline edit changes
    `SKILL.md` and the guideline files without touching `evals/evals.json`, so the
    assertion text was unchanged, this predicate returned "current", and the
    regression gate's "re-run exactly those" silently did nothing. The delta was
    then computed against a review of a *different instruction surface* while
    reporting that the surface had been measured.

    That is the scan-matches-nothing shape one level up: not a wrong answer, but no
    answer, produced by a gate whose whole job is to produce one. `base_commit` was
    already written into every verdict and required as the run's basis by
    `auditandevolve/SKILL.md`; it was recorded and never compared.

    This makes a stored verdict stale on any commit, which is the honest reading --
    and it deliberately does not *hard-refuse* on a mismatch. Refusing would mark
    every stored verdict stale on every guideline edit, and the tree already cannot
    afford to re-run its corpus. Naming the mismatch is available; refusing is not.
    """
    if not grading_path.is_file():
        return False, "no stored verdict"
    try:
        data = load_json(grading_path)
    except json.JSONDecodeError:
        return False, "stored verdict is unreadable"

    recorded = [r.get("text", "") for r in data.get("assertion_results", [])]
    if recorded != assertions:
        return False, "assertion text has changed since the verdict was recorded"

    if base_commit is not None and data.get("base_commit") != base_commit:
        recorded_at = data.get("base_commit") or "none"
        return False, (
            f"the tree has moved since this verdict was recorded "
            f"(recorded at {recorded_at}, now {base_commit})"
        )

    if reps > 1:
        reps_done = [
            r
            for r in data.get("replicates", [])
            if [a.get("text", "") for a in r.get("assertion_results", [])] == assertions
        ]
        if len(reps_done) >= reps:
            return True, ""
        return False, f"{len(reps_done)} of {reps} replicates recorded"
    return True, ""


SKILL_DIRS = ("shared", "domains", "project-tree", "auditandevolve", "scripts")
# Paths that hold answers or verdicts. evals/fixtures/ is deliberately NOT here:
# the eval prompt tells the reviewer to read evals/fixtures/<name>.py, so flagging
# it would reject every legitimate run. What must not be reachable is the answer
# key and the recorded verdicts beneath it.
FORBIDDEN_NAMES = ("evals.json", ".git")
FORBIDDEN_DIRS = ("iteration-1", "review")
# A pattern that would sweep the whole tree reaches the key even though it names
# no path. These are the shapes a recursive search actually takes.
SWEEP_PATTERNS = {".", "*", "**", "**/*", "./", "../", "**/*.*"}


# The gate under ablation. `nosuppress` is this tree with the gate removed and
# every reference to it deleted, which is what makes the two arms differ by
# exactly the mechanism and nothing else.
ABLATED = ("project-tree/shared/deliberate.md",)

# The harness grades the reviewer, so the reviewer must not be able to read the harness.
# Staging `scripts/` put GRADER_INSTRUCTIONS and JUDGE_PROBES inside the workspace: the
# rubric the judge grades against, and a worked review carrying the exact award count it
# has to earn. The contamination gate never objected, because `run_evals.py` is not a
# forbidden name -- it is an ordinary file in an ordinary staged directory, which is
# precisely how a key gets carried in without tripping anything. Self-inflicted: those
# probes were added while the harness was already being staged.
#
# Only the grading half is excluded. The other scripts stay, because a reviewer may
# reasonably run the validator, and removing a capability to fix a leak is not a fix.
HARNESS_FILES = ("run_evals.py", "grade_evals.py")


def stage_skill(dest: Path, arm: str = "with_skill") -> None:
    """Copy the instruction surface into a run workspace and nothing else.

    Discovery survives because every path the instruction files cite is relative
    and one level deep, which validate_skill.py already enforces. What does not
    come along is the answer key: evals/evals.json carries every expected_output
    and assertion string, and evals/iteration-1/ carries every recorded verdict.
    Neither is reachable from the workspace.
    """
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("SKILL.md", *SKILL_DIRS):
        src = SKILL_ROOT / name
        if src.is_dir():
            shutil.copytree(
                src,
                dest / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", *HARNESS_FILES),
                dirs_exist_ok=True,
            )
        elif src.is_file():
            shutil.copy2(src, dest / name)
    if arm == "nosuppress":
        remove_gate(dest)


def seal_workspace(dest: Path) -> None:
    """Make the workspace a git repository with a single commit.

    Without this the reviewer does not stay in the workspace, and the baseline arm
    is worthless. Observed directly: an unstaged workspace is not a project, so
    runner resolved the project elsewhere, and the reviewer read the fixture
    from the real repository, walked upward, and found `evals/README.md` and the
    `with_skill` grading.json and review.md -- the baseline was reading the answer
    it was supposed to be compared against.

    A repository root gives the runner an unambiguous project, and `..` from inside
    it stays inside it. Verified by planting a decoy answer key in a workspace:
    with the seal the reviewer never saw it, without the seal it walked out.

    Applies to every arm, including `without_skill`, which stages no skill at all
    and so has nothing else to mark a project boundary.
    """
    try:
        subprocess.run(
            ["git", "init", "-q", str(dest)],
            capture_output=True, text=True, timeout=60, check=True,
        )
        for key, val in (("user.email", "eval@localhost"), ("user.name", "eval"),
                         ("commit.gpgsign", "false")):
            subprocess.run(["git", "-C", str(dest), "config", key, val],
                           capture_output=True, text=True, timeout=60, check=False)
        subprocess.run(["git", "-C", str(dest), "add", "-A"],
                       capture_output=True, text=True, timeout=120, check=False)
        subprocess.run(
            ["git", "-C", str(dest), "commit", "-q", "-m", "staged eval workspace"],
            capture_output=True, text=True, timeout=120, check=False,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raise RuntimeError(
            f"could not seal the workspace at {dest}: {exc}. An unsealed workspace "
            f"lets the reviewer reach the real repository and read the answer key."
        ) from exc


def remove_gate(dest: Path) -> None:
    """Delete the ablated files and every line that names one.

    Copy-then-delete, not an ignore pattern: ignore_patterns matches basenames,
    so excluding "project-tree/shared/deliberate.md" by that string excludes
    nothing at all - which is exactly the bug this replaced. The strip must also
    reach every staged document, not only the root entry file, or the workspace
    cites a file that is no longer there and the arm measures a broken tree
    rather than an ungated one.
    """
    for rel in ABLATED:
        target = dest / rel
        if target.is_file():
            target.unlink()
    needles = [Path(rel).name for rel in ABLATED]
    for doc in dest.rglob("*.md"):
        lines = doc.read_text(encoding="utf-8").split("\n")
        kept = [ln for ln in lines if not any(n in ln for n in needles)]
        if len(kept) != len(lines):
            doc.write_text("\n".join(kept), encoding="utf-8")


def contamination(reads: list[str], workspace: Path) -> list[str]:
    """Paths a run reached that it should not have been able to.

    Two rules. Nothing outside the run's own workspace, which catches absolute
    paths back into the real repository. And nothing inside a directory that
    holds verdicts or answer keys, which catches a relative sweep that stays
    inside the workspace but reaches the corpus.
    """
    try:
        root = workspace.resolve()
    except OSError:
        return reads
    leaks = []
    for raw in reads:
        if not isinstance(raw, str) or not raw:
            continue
        if raw.strip() in SWEEP_PATTERNS:
            leaks.append(raw)
            continue
        candidate = Path(raw)
        resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError:
            leaks.append(raw)
            continue
        parts = relative.parts
        if any(part in FORBIDDEN_NAMES for part in parts):
            leaks.append(raw)
            continue
        # Every component, not all but the last. Dropping the final segment meant a read
        # of a forbidden *directory* resolved "inside" it and was never compared against
        # the forbidden set at all -- so the gate caught files beneath the recorded-verdict
        # directory and missed the directory itself, which is the cheaper way in.
        if any(part in FORBIDDEN_DIRS for part in parts):
            leaks.append(raw)
    return leaks


def absolute_prompt(eval_item: dict, dest: Path) -> str:
    """Rewrite the prompt's fixture paths to absolute paths inside the workspace.

    The eval prompts say "Review evals/fixtures/x.py". The workspace reproduces
    that layout, so the path resolves -- but it also reproduces the *repository's*
    layout, and a reviewer that cannot find the file, or that goes looking for
    its siblings, walks up out of the workspace and into the real repository.
    Observed directly: the reviewer's first tool call was an absolute path into
    the real tree, and it went on to read `evals/evals.json` and the recorded
    verdicts.

    Naming the absolute staged path removes the ambiguity that provokes the
    search. Nothing about the review changes; only the path it is given does.
    """
    prompt = eval_item["prompt"]
    for rel in eval_item.get("files", []):
        for spelling in (rel, rel.replace("/", " ")):
            prompt = prompt.replace(spelling, str((dest / rel).resolve()))
    # Say the workspace is the whole world. Measured: 7 of 102 runs were refused for reading
    # outside it, and the reads are explicit -- after the fixture, the reviewer reached for
    # `repo/evals` and `repo/shared/output-format.md`. The repository root is exactly three
    # hops up from a staged workspace (`probe/tmp/ws` -> `probe/tmp` -> `probe` -> repo), so a
    # reviewer looking for a sibling or a criteria file arrives there without trying to escape.
    #
    # This does not weaken the gate, which still refuses any run it cannot prove; it reduces the
    # incidence of a run needing to be refused. Whether that is a fix or a way of making the
    # refusal rate look better is measurable: re-run the refused fixtures and compare.
    #
    # A workspace is its own repository and contains everything the review needs. Nothing above
    # this directory is part of the review, and no file outside it describes what to look for.
    return prompt + (
        "\n\nThe path above is inside a self-contained workspace that already holds every "
        "file this review needs, including the skill's own rules. Nothing outside that "
        "directory is part of the review, and no file elsewhere describes what to look for, so "
        "there is nothing to gain by reading above it.")


STAGE_ROOT = "probe/tmp"


def stage_root() -> Path:
    """Where a run workspace is created: inside this repository, under a gitignored path.

    Two reasons, and the second is the load-bearing one.

    The first is hygiene. A staged workspace used to be created in the system temporary
    directory, which is outside the tree, so every path the reviewer touched carried a
    per-user temporary root -- a machine identifier and an account identifier -- into
    recorded evidence. That is why `portable_path` exists at all.

    The second is that isolation was only ever verified with the workspace inside the tree.
    Probed from a temporary root the run did not return a usable verdict; probed from a
    directory inside the repository it returned the workspace as the shell's working
    directory and an `evals/` holding nothing but fixtures. Rather than depend on a
    location whose behaviour was not established, the workspace lives where the behaviour
    is known, and where a reader can go and look at it.
    """
    root = SKILL_ROOT / STAGE_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root


def stage_fixture(eval_item: dict, dest: Path) -> None:
    """Copy the eval's files into a bare directory, preserving relative paths.

    The paths must survive, not just the filenames: the eval prompt says
    "Review evals/fixtures/x.py", so a flattened copy would leave the reviewer
    looking for a file that is not where the prompt says it is.
    """
    dest.mkdir(parents=True, exist_ok=True)
    for rel in eval_item.get("files", []):
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SKILL_ROOT / rel, target)


def grade(
    review: str,
    assertions: list[str],
    timeout: int,
    work_dir: Path,
    model: str | None = None,
    artifact_dir: Path | None = None,
) -> list[dict]:
    listed = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(assertions))
    message = (
        f"{GRADER_INSTRUCTIONS}\n\n"
        f"ASSERTIONS ({len(assertions)}):\n{listed}\n\n"
        f"REVIEW UNDER GRADING:\n\n---\n{review}\n---"
    )
    reply, stream = run_model(message, work_dir, timeout, model)
    verdicts = parse_verdicts(reply, len(assertions))
    if verdicts is None:
        # Keep the reply. A judge that fails to produce a parseable array is the
        # difference between a measured arm and a missing one, and the reply is
        # the only evidence of what went wrong -- prose, a truncated array, an
        # array of the wrong length, or a refusal. Discarding it means the next
        # occurrence is undiagnosable, which is how the quota wall hid for a
        # whole sweep.
        # Into the eval's own output directory, not the judge's temporary one:
        # that directory is removed when the grading context exits, so a reply
        # "kept" there is destroyed on the way out and the next occurrence is
        # undiagnosable all over again.
        keep = artifact_dir or work_dir
        keep.mkdir(parents=True, exist_ok=True)
        (keep / "judge_reply.txt").write_text(reply, encoding="utf-8")
        (keep / "judge_stream.jsonl").write_text(stream, encoding="utf-8")
        raise RuntimeError(
            f"grader reply was not a well-formed verdict array of the right length "
            f"({len(reply)} chars, wanted {len(assertions)}); reply kept at "
            # Relative to this repository, always. The message is read in a terminal and
            # copied into issues and commit notes, so an absolute path here is a machine
            # path and an account name one paste away from publication.
            f"{portable_path(str(keep))}"
        )
    return verdicts


def safe_error(exc: BaseException) -> str:
    """A failure worth reading, without the parts that must never be published.

    A subprocess failure stringifies its own argv, so printing it verbatim puts the
    runner's install path, the operator's home directory and the whole grading prompt --
    assertions included -- into a run log. Observed: one judge timeout wrote all of that
    into the sweep output. Logs get pasted into issues, and an issue is public.

    So: the exception type, the first line of its message, path-reduced, and nothing more.
    The full text stays in the stream file, which is gitignored, for whoever is debugging
    it in place.
    """
    head = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
    head = portable_path(head) if head.startswith("/") else head
    for prefix in ("Command '[", "["):
        if head.startswith(prefix):
            head = "a subprocess call"
            break
    if len(head) > 160:
        head = head[:157] + "..."
    return f"{type(exc).__name__}: {head}" if head else type(exc).__name__


SKILL_SURFACE = ("SKILL.md", "shared/", "domains/", "project-tree/", "auditandevolve/")


def trigger_probe(args) -> dict:
    """Does the skill's own description make it activate, or does it need to be named?

    Every other measurement here asks what a reviewer produced. This asks something
    earlier: whether the reviewer engaged at all. `evals/trigger-queries.json` was adopted
    with `should_trigger` on each query and nothing ever read that field -- there was no
    path to run them, so the number was not missing, it was uncomputable.

    Consultation is read from tool calls, not from the reply. A triggered run opens the
    instruction surface; an untriggered one answers the question from the prompt. Matching
    the skill's name anywhere in the output would count the prompt echoing itself, which is
    the failure this avoids.

    The reply is recorded but not graded. There is nothing to grade: the queries ask whether
    the skill activates, not whether a review is correct, and a fixture's assertions cannot
    be applied to an answer that may legitimately be "this does not need a review".
    """
    spec = load_json(SKILL_ROOT / "evals" / "trigger-queries.json")
    queries = spec.get("queries") or []
    if args.limit:
        queries = queries[: args.limit]
    rows = []
    for n, item in enumerate(queries, 1):
        query = item["query"] if isinstance(item, dict) else str(item)
        expected = bool(item.get("should_trigger")) if isinstance(item, dict) else None
        work_dir = stage_root() / f"se-trigger-{n:02d}"
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
        stage_skill(work_dir, "with_skill")
        seal_workspace(work_dir)
        try:
            reply, stream = run_model(query, work_dir, args.timeout, args.model)
            paths, _ = read_paths_and_patterns(stream)
            inside = []
            for path in paths:
                try:
                    rel = Path(path).resolve().relative_to(work_dir.resolve()).as_posix()
                except (ValueError, OSError):
                    continue
                if any(rel == s.rstrip("/") or rel.startswith(s) for s in SKILL_SURFACE):
                    inside.append(rel)
            # Proceeded to a review -- not "opened a file".
            #
            # The first version of this read `consulted` as "read something in the staged
            # surface", and produced 17 of 20 engaged with ten false positives. The replies
            # say otherwise: "That request falls outside...", "out of scope for se-review".
            # The model was reading SKILL.md *in order to decide the skill did not apply*,
            # and then declining, which is the behaviour being measured working correctly.
            #
            # So the signal is whether a review happened. Reading the surface is kept as
            # evidence, not as the verdict: a run that reads the surface and declines has
            # demonstrated exactly the discrimination this probe is asking about.
            proceeded = looks_like_report(reply)
            rows.append({"query": query, "should_trigger": expected,
                         "consulted": proceeded, "read_surface": bool(inside),
                         "read": sorted(set(inside))[:6],
                         "reply_chars": len(reply),
                         "reply_head": sanitise_paths(reply.strip()[:160], work_dir)})
        except Exception as exc:  # a transport failure is not a verdict either way
            rows.append({"query": query, "should_trigger": expected, "consulted": None,
                         "read": [], "reply_chars": 0,
                         "reply_head": safe_error(exc)})
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    graded = [r for r in rows if r["consulted"] is not None and r["should_trigger"] is not None]
    engaged = sum(1 for r in graded if r["consulted"])
    wanted = sum(1 for r in graded if r["should_trigger"])
    both = sum(1 for r in graded if r["consulted"] == r["should_trigger"])
    return {"rows": rows, "asked": len(rows), "scored": len(graded),
            "engaged": engaged, "should_trigger": wanted, "agreed": both,
            "rate": round(engaged / len(graded), 4) if graded else None,
            "accuracy": round(both / len(graded), 4) if graded else None}


def print_trigger_probe(result: dict) -> None:
    print(f"\nTRIGGER PROBE  {result['asked']} queries, {result['scored']} scored")
    for r in result["rows"]:
        mark = "?" if r["consulted"] is None else ("engaged" if r["consulted"] else "silent ")
        want = "-" if r["should_trigger"] is None else ("want" if r["should_trigger"] else "skip ")
        agree = "" if r["consulted"] is None else (
            "" if r["consulted"] == r["should_trigger"] else "  <- disagrees")
        print(f"  {mark}  {want}  {r['query'][:66]}{agree}")
    if not result["scored"]:
        print("  NOT MEASURED -- no query produced a gradeable consultation signal.")
        return
    print(f"\n  engaged {result['engaged']} of {result['scored']}; "
          f"{result['should_trigger']} should have engaged; "
          f"agreement {result['agreed']}/{result['scored']}")
    print(f"  activation rate {result['rate']:.3f}" if result["rate"] is not None else "")


def current_base() -> str | None:
    """The short digest of HEAD, or None when it cannot be read."""
    try:
        return subprocess.run(
            ["git", "-C", str(SKILL_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip() or None
    except (subprocess.SubprocessError, OSError):
        return None


def run_one(eval_item: dict, condition: str, out_root: Path, args) -> str:
    """Run one eval in one arm, `args.reps` times, and record every replicate.

    One review is a point estimate with no error bar. Replicates are what turn
    a pass rate into something a delta can be compared against: without them
    the noise floor hillclimb.md requires before round one cannot be computed
    at all, and the suppression ablation's 40-point bar has nothing to sit on.
    """
    eid = eval_item["id"]
    name = eval_name(eid)
    assertions = eval_item.get("assertions", [])
    target = out_root / name / condition
    grading_path = target / "grading.json"

    try:
        base_commit = subprocess.run(
            ["git", "-C", str(SKILL_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip() or None
    except (subprocess.SubprocessError, OSError):
        base_commit = None

    if not args.force:
        current, why = already_current(grading_path, assertions, args.reps, base_commit)
        if current:
            return "skip"
        if grading_path.is_file():
            # Say why a stored verdict is being re-run. A re-run with no stated
            # reason and a silent skip look identical in a run log, and only one of
            # them is a decision.
            print(f"  re-running: {why}")

    target.mkdir(parents=True, exist_ok=True)
    # Clear the replicate directories this run will rewrite. A run at a lower replicate
    # count than the one before it leaves the surplus on disk, so an arm's directory
    # describes two runs at once: a 2-replicate verdict sitting beside rep3, rep4 and rep5
    # from an earlier 5-replicate run, one of which was refused. The verdict aggregates only
    # the replicates it recorded, so the number is right and the evidence beside it is not.
    for stale in range(2, args.reps + 1):
        leftover = target / f"rep{stale}"
        if leftover.is_dir():
            shutil.rmtree(leftover, ignore_errors=True)
    judge_model_name = getattr(args, "judge_model", None) or args.model
    reps = []
    failures = []
    for rep in range(1, args.reps + 1):
        result, why = run_once(eval_item, condition, target, args, rep)
        if result is None:
            failures.append(why)
            continue
        reps.append(result)
    if not reps:
        # A rejected run must not leave the previous run's verdict sitting beside it.
        # `--force` re-runs an arm; if every replicate is refused the arm has produced
        # nothing this time, and a grading.json from an earlier attempt reads as a
        # verdict for the current tree. Measured: three arms held a verdict while their
        # own event stream had reached the answer key, and one of them recorded
        # `reason: contamination` in plumbing.json with a grading.json next to it --
        # the gate refusing the run and the corpus reporting it anyway.
        if grading_path.is_file():
            grading_path.unlink()
        return "; ".join(failures) if failures else "no replicate produced a verdict"

    passed = sum(r["summary"]["passed"] for r in reps)
    total = sum(r["summary"]["total"] for r in reps)
    grading = {
        "eval_id": eid,
        "eval_name": name,
        "condition": condition,
        # A configuration handle, never an identity. The validator forbids a `model`
        # key in committed evidence and names the replacement in its own error text --
        # `<key>_config`, holding `cfg:<hex>` or `unpinned`. This writer emitted the
        # forbidden key, so a fresh verdict could not be committed without tripping the
        # gate, and the `--model` help promised a digest that no code computed. Two
        # auditors found this independently by grepping for a hash function and not
        # finding one.
        "model_config": config_digest(args.model),
        "judge_model_config": config_digest(judge_model_name),
        "judge_disjoint": bool(judge_model_name and args.model and judge_model_name != args.model),
        # A diff graded against a base that has moved is not the same measurement.
        "base_commit": base_commit,
        # The no-axis count, recorded by the harness rather than read from the review
        # prose later. `Unclassified:` has been required by shared/output-format.md since
        # the first commit and no run in this corpus emitted it, so a counter that parses
        # review bodies can only ever report absence -- and absence is not a measurement.
        # Recording it here makes the omission attributable to a specific run instead of
        # invisible in an aggregate, and `null` is distinct from 0: null is "the reviewer
        # did not say", zero is "the reviewer looked and the registry covered everything".
        **no_axis_count(reps),
        "grader_config": grader_digest(),
        # Which assertion is a verdict and which is a probe. The corpus declares roles per
        # eval, but no verdict recorded them, so the block that separates the two read
        # `assertion_roles`, found it absent on every stored verdict, and printed nothing --
        # a check that reports nothing, indistinguishable from one that found nothing.
        "assertion_roles": eval_item.get("assertion_roles"),
        "fixture_digests": fixture_digests(eval_item),
        "skill_consulted": any(r.get("skill_consulted") for r in reps),
        "skill_consulted_reps": sum(1 for r in reps if r.get("skill_consulted")),
        "reps_requested": args.reps,
        "reps_completed": len(reps),
        # Replicates that were refused, named in the record rather than only in the run
        # log. A partial that survives into an aggregate looks identical to a complete
        # one unless the shortfall travels with it.
        "reps_refused": len(failures) or 0,
        # What isolation this verdict may claim. Measured, not assumed: a probe of the
        # runner showed the shell tool's working directory is the real repository, even
        # with the workspace as the process cwd, `--standalone` passed, and the
        # workspace named as the trailing positional. There is no flag on this runner to
        # set the project directory, so the staged workspace cannot be made true through
        # the CLI and a reviewer can reach evals/evals.json with one relative path.
        # Until that is fixed, "unverified" is the honest value and no verdict here may
        # claim otherwise.
        "reviewer_project_root": "workspace",
        # Shell commands that relied on a relative path. Not a refusal -- isolation means a
        # relative path resolves inside the workspace -- but recorded, because the number
        # that was a hard gate until the flag was fixed is now an observation, and an
        # observation nobody writes down is an assumption.
        "isolation_indirect_commands": sum(r.get("isolation_indirect", 0) for r in reps),
        "assertion_results": reps[0]["assertion_results"],
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "pass_rate": round(passed / total, 4) if total else 0.0,
        },
    }
    if len(reps) > 1:
        grading["replicates"] = reps
        rates = [r["summary"]["pass_rate"] for r in reps]
        mean = sum(rates) / len(rates)
        var = sum((r - mean) ** 2 for r in rates) / (len(rates) - 1) if len(rates) > 1 else 0.0
        grading["replicate_summary"] = {
            "n": len(rates),
            "mean_pass_rate": round(mean, 4),
            # The quantity hillclimb.md asks for before round one: how far a
            # score moves by chance alone. Zero at one replicate, which is
            # precisely why a single run cannot gate a delta.
            "stdev_pass_rate": round(math.sqrt(var), 4),
            "min_pass_rate": min(rates),
            "max_pass_rate": max(rates),
        }
    grading_path.write_text(json.dumps(grading, indent=2), encoding="utf-8")
    note = f" ({len(failures)} rep(s) produced no verdict)" if failures else ""
    return f"ok {passed}/{total} over {len(reps)} rep(s){note}"


def run_once(eval_item: dict, condition: str, target: Path, args, rep: int):
    """One replicate. Returns (grading_payload, None) or (None, reason).

    Split out so the replicate loop above owns aggregation and this owns a
    single attempt. Each attempt gets its own workspace, so nothing one
    replicate wrote can be read by the next - the isolation the ablation
    depends on, since a shared workspace would let rep 2 see rep 1's verdict.
    """
    eid = eval_item["id"]
    name = eval_name(eid)
    assertions = eval_item.get("assertions", [])
    rep_target = target if rep == 1 else target / f"rep{rep}"
    rep_target.mkdir(parents=True, exist_ok=True)

    work_dir = stage_root() / f"se-run-{name}-{condition}-r{rep}-{os.urandom(3).hex()}"
    work_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        if condition in ("with_skill", "nosuppress"):
            stage_skill(work_dir, arm=condition)
        stage_fixture(eval_item, work_dir)
        seal_workspace(work_dir)
        review, stream = run_model(absolute_prompt(eval_item, work_dir), work_dir, args.timeout, args.model)
        (rep_target / "events.jsonl").write_text(stream, encoding="utf-8")

        reads, patterns = read_paths_and_patterns(stream)
        consulted = skill_was_consulted(reads, review)
        # Recorded, not rejected. A runner loads a project SKILL.md into the system
        # prompt without any file read, so this detector has an inherent false
        # negative rate -- and it proved intermittent, rejecting runs whose review
        # was in the skill's format on the previous attempt. A detector that can
        # discard a real measurement must not be a hard gate: the flag travels in
        # the verdict instead, so an unaided run is visible rather than deleted.
        if (
            condition in ("with_skill", "nosuppress")
            and args.require_skill
            and not consulted
        ):
            (rep_target / "plumbing.json").write_text(
                json.dumps(
                    {
                        "reason": "skill markers not observed; recorded as unverified "
                        "consultation rather than discarded, because the detector "
                        "cannot see a skill auto-loaded into the system prompt",
                        "reads": portable_reads(reads, work_dir),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        if condition == "without_skill" and consulted:
            return None, f"REJECTED r{rep}: the baseline read the skill"
        if condition == "nosuppress" and any("deliberate" in r for r in reads):
            return None, f"REJECTED r{rep}: the ablation arm read the gate file"

        # Contamination gate. The answer key lives in this repository, so a
        # reviewer whose working directory is the skill root can reach it with a
        # recursive search. That already happened: one with-skill run in this
        # corpus self-disclosed a grep that matched evals/evals.json, and the
        # twelve evals it touched were discarded. Stage the skill rather than
        # running in place, then refuse any run that reaches outside its own
        # workspace or into the directories that hold verdicts.
        # Proof of isolation, not merely absence of contamination. The runner pins each
        # session to the directory named on its command line, so a run that reached the key
        # would show it in the harvested reads -- which is why shell reads are collected and
        # not just tool reads. See the gate for why the earlier proxy was retired.
        isolated, why_isolated, iso_paths, iso_indirect = isolation_gate(stream, work_dir)
        if not isolated:
            (rep_target / "plumbing.json").write_text(
                json.dumps({"reason": "isolation unproven", "detail": why_isolated,
                            "reads": portable_reads(iso_paths, work_dir)}, indent=2),
                encoding="utf-8",
            )
            return None, f"UNPROVEN r{rep}: {why_isolated}"

        leaks = contamination(reads, work_dir)
        if leaks:
            (rep_target / "plumbing.json").write_text(
                json.dumps({"reason": "contamination", "reads": portable_reads(leaks, work_dir)}, indent=2),
                encoding="utf-8",
            )
            return None, f"CONTAMINATED r{rep}: reached the key or outside the workspace"

        # The citation is evidence; the temporary directory it was staged into is not.
        # Committed verbatim it named the machine, the run and -- where a reviewer reached
        # into the real tree -- the operator's home directory and username.
        (rep_target / "review.md").write_text(
            sanitise_paths(review, work_dir), encoding="utf-8")

        # Plumbing gate. The question is not "did a tool error" but "is there a
        # review to grade". A denied or misnamed tool can end a run before it
        # produces anything, and grading that truncated output is how a permission
        # denial becomes a permanent 0/n. But the converse error is worse and was
        # being made on every run: a reviewer that misnames one tool, gets an
        # error, carries on and produces a complete review was being discarded
        # wholesale. Tool names differ per harness, so that rule made the corpus
        # unmeasurable wherever the model guessed wrong once.
        errors = tool_errors(stream)
        has_report = looks_like_report(review)
        if not has_report:
            (rep_target / "plumbing.json").write_text(
                json.dumps(
                    {
                        "tool_errors": errors,
                        "reason": "no review body produced; output was preamble or truncated",
                        "output_chars": len(review),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            cause = f"{len(errors)} tool error(s), " if errors else ""
            return None, f"INCOMPLETE r{rep}: {cause}no review body ({len(review)} chars)"
        if errors:
            # Graded anyway, and recorded, so the error is visible without
            # discarding a review that exists.
            (rep_target / "plumbing.json").write_text(
                json.dumps(
                    {
                        "tool_errors": errors,
                        "reason": "review body present and graded despite tool errors; "
                        "the errors did not prevent the review",
                        # The reads this arm made, on the branch that produced a verdict.
                        # Without them the only branch of this gate that reports what was
                        # read is the branch that threw the run away, so a completed run
                        # records nothing about its own file access -- and a reader who
                        # asks "did this review read the key?" gets silence, which reads
                        # the same as "no". Measured: one arm here reported `reads: 0`
                        # while the gate had seen three paths, because the key was absent
                        # and absent was read as zero.
                        "reads": portable_reads(reads, work_dir),
                        "reads_recorded": len(reads),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

        # The judge gets its own directory. It already receives the assertions as
        # text, so nothing leaks today, but the principle that the judge is not the
        # model under test should not stop at the model.
        with tempfile.TemporaryDirectory(prefix="se-judge-") as judge_dir:
            judge_model = getattr(args, "judge_model", None) or args.model
            verdicts = grade(
                review, assertions, args.timeout, Path(judge_dir),
                judge_model, rep_target,
            )

        passed = sum(1 for v in verdicts if v["passed"])
        # Assertion text is attached from evals.json, never taken from the grader.
        payload = {
            "rep": rep,
            "skill_consulted": consulted,
            # Relative, so the verdict is portable and diffable. The gates above
            # used the raw absolute paths; this is what gets written down.
            "files_read": relativise(reads, work_dir),
            "searched": patterns,
            # Shell commands that leaned on a relative path. Isolation means those resolve
            # inside the workspace, so this is an observation rather than a refusal -- and it
            # is the number that was a hard gate until the flag that makes isolation work
            # was actually being sent. Written down so it is not merely assumed.
            "isolation_indirect": iso_indirect,
            "assertion_results": [
                {"text": text, "passed": v["passed"], "evidence": v["evidence"]}
                for text, v in zip(assertions, verdicts)
            ],
            "summary": {
                "passed": passed,
                "failed": len(assertions) - passed,
                "total": len(assertions),
                "pass_rate": round(passed / len(assertions), 4) if assertions else 0.0,
            },
        }
        # Timing is written only past the plumbing gate, and only beside a verdict.
        # A rejected run leaves review.md and plumbing.json and no timing.json, so
        # the aggregate can never read a tool error or a cut-off answer as a slow
        # but legitimate review.
        (rep_target / "timing.json").write_text(
            json.dumps(
                {
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "output_chars": len(review),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return payload, None
    finally:
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)


def config_digest(value: str | None) -> str:
    """A stable handle for a run configuration, never the configuration itself.

    Two verdicts are comparable when their handles match, and a handle reveals
    nothing about what produced the number. `unpinned` is a distinct value rather
    than a digest of the empty string, so "nobody said" cannot be mistaken for
    "somebody said the same thing twice" -- which is exactly the confusion an
    unpinned run invites when it is hashed as if it were pinned.
    """
    if not value:
        return "unpinned"
    return "cfg:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run se-review evals with text-bound verdicts.")
    parser.add_argument(
        "--judge-selftest",
        action="store_true",
        help="audit the judge itself instead of running any eval. Grades a fixed set of "
        "probe answers whose verdicts are known in advance, and reports whether the "
        "judge separates them. This is the only check in the repository that examines "
        "the instrument rather than the thing measured, and it existed with no way to "
        "be invoked: the code was complete and nothing called it, which is the same "
        "shape as a rule that can never fire.",
    )
    parser.add_argument(
        "--judge-selftest-reps",
        type=int,
        default=JUDGE_SELFTEST_REPS,
        help="repetitions per probe when --judge-selftest is set.",
    )
    parser.add_argument(
        "--trigger-probe",
        action="store_true",
        help="run the trigger-query set and record whether the skill activates. No "
             "reviewer task and no grading: the question is whether the skill engaged.",
    )
    parser.add_argument(
        "--judge-probe",
        action="append",
        default=None,
        help="run only the named probe. Diagnosing one probe should not cost the "
             "whole battery, and the substance probe is the one that decides whether "
             "TRUSTED means anything.",
    )
    parser.add_argument(
        "--condition",
        choices=("with_skill", "without_skill", "nosuppress", "both"),
        default="both",
        help="nosuppress is the ablation arm: this tree with the deliberate gate removed.",
    )
    parser.add_argument("--eval", type=int, help="run a single eval id")
    parser.add_argument("--limit", type=int, help="run at most N evals")
    parser.add_argument("--iteration", default="iteration-1")
    parser.add_argument("--timeout", type=int, default=900, help="seconds per model call")
    parser.add_argument(
        "--judge-model",
        default=None,
        help="provider/model to grade as. The judge must not be the model under "
        "test, so pin this separately from --model. When omitted it falls back to "
        "--model and the verdict is recorded as non-disjoint, because a model "
        "grading its own output has an interest in the result.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="run configuration to use. Recorded in the verdict as a digest, not by name, "
        "so two verdicts can be checked for comparability without the "
        "verdict naming what produced it. An unpinned run is not comparable to a pinned one.",
    )
    parser.add_argument(
        "--reps",
        type=int,
        default=1,
        help="replicates per eval per arm; >1 records a replicate block and a spread",
    )
    parser.add_argument("--force", action="store_true", help="re-run even if verdicts are current")
    parser.add_argument("--require-skill", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.trigger_probe:
        result = trigger_probe(args)
        print_trigger_probe(result)
        dest = SKILL_ROOT / "evals" / args.iteration / "trigger_probe.json"
        dest.write_text(json.dumps(result, indent=2) + "\n")
        print(f"\n  written to {dest.relative_to(SKILL_ROOT)}")
        return 0

    if args.judge_selftest:
        return _run_judge_selftest(args)

    evals = load_json(SKILL_ROOT / "evals" / "evals.json").get("evals", [])
    if args.eval is not None:
        evals = [e for e in evals if e["id"] == args.eval]
        if not evals:
            print(f"No eval with id {args.eval}")
            return 1
    if args.limit is not None:
        evals = evals[: args.limit]

    out_root = SKILL_ROOT / "evals" / args.iteration
    conditions = (
        ("with_skill", "without_skill")
        if args.condition == "both"
        else (args.condition,)
    )

    sweep_base = current_base()
    moved_from = None
    for eval_item in evals:
        for condition in conditions:
            if args.dry_run:
                print(f"would run  {eval_item['id']:>3} {eval_name(eval_item['id']):<32} {condition}")
                continue
            try:
                result = run_one(eval_item, condition, out_root, args)
            except Exception as exc:  # a failed run must not stop the sweep
                result = f"FAILED: {safe_error(exc)}"
            print(f"{eval_item['id']:>4} {eval_name(eval_item['id']):<32} {condition:<14} {result}")
            # The tree moved mid-sweep. Every verdict records the base it was graded at,
            # and `already_current` compares one verdict against one base -- but a sweep
            # spanning two bases produces a set whose arms are not comparable, and the
            # delta between them would be attributed to the change under test when it is
            # the change that happened to land between two arms. Observed directly: two
            # arms of one ablation recorded different bases, and nothing said so.
            now = current_base()
            if sweep_base and now and now != sweep_base:
                if moved_from is None:
                    moved_from = sweep_base
                    print(
                        f"\nWARNING: the tree moved during this sweep ({moved_from} -> "
                        f"{now}).\n  Arms recorded before and after are not comparable, and "
                        f"any delta\n  between them measures the edit that landed mid-sweep "
                        f"rather than the one\n  under test. Freeze the tree while a sweep "
                        f"runs."
                    )
            # A quota wall does not clear by trying again, and continuing past it
            # turns one honest stop into forty identical failures that bury the
            # runs which did land. Stop, and say what is still owed.
            if str(result).startswith("FAILED") and is_rate_limited([str(result)]):
                remaining = [
                    f"{e['id']}:{c}" for e in evals[evals.index(eval_item):]
                    for c in conditions
                ]
                print(
                    f"\nABORTED: the provider rate limit was hit. {len(remaining) - 1} "
                    f"run(s) in this sweep were not attempted. Nothing was recorded for "
                    f"them, and no verdict should be inferred from their absence.\n"
                    f"Resume with: python3 scripts/run_evals.py --eval <id> --condition <arm>"
                )
                return 2
    return 0


def _run_judge_selftest(args: argparse.Namespace) -> int:
    """Print the judge audit and exit.

    The verdict is reported rather than raised, so the result is recorded beside the
    other measurements instead of stopping whatever run happened to trigger it. A
    caller that wants it to be fatal should read the exit code, which is 1 on
    UNTRUSTED and 0 otherwise.
    """
    report = judge_selftest(reps=args.judge_selftest_reps, only=args.judge_probe)
    for key, value in report.items():
        if key == "JUDGE SELFTEST":
            print("\nJudge probes (expected verdict in brackets):")
            for probe in value:
                # The row keys come from _fold_judge_probe. My first printer guessed
                # `name`/`verdict`/`expected` and raised KeyError on the first row, which
                # is the same failure class this whole pass has been about: a printer
                # asserting a shape nobody checked. Read the keys the function writes.
                did = probe.get("judge_failed_it")
                verdict = ("failed_it" if did is True else
                           "did_not_fail" if did is False else
                           "no verdict")
                agreed = probe.get("agreed")
                agree_txt = "" if agreed is None else f"  agreed={agreed}"
                want = probe.get("expect_awards")
                got = probe.get("assertions_passed_by_probe")
                want_txt = "" if want is None else f" (awards {want})"
                if got:
                    # The direction of the error is the whole diagnosis: too few means
                    # it under-read and asserted absence, too many means it waved the
                    # review through. Naming one without the other is not a finding.
                    want_txt += f" but awarded {got}"
                print(f"  {probe.get('probe', '?'):<34} {verdict:<12} "
                      f"expected {probe.get('expectation')}{want_txt}{agree_txt}")
        else:
            print(f"\n{key}: {value}")
    verdict = str(report.get("judge_verdict", "")).upper()
    print(
        "\nThe judge decides every number in this repository. A verdict of UNTRUSTED "
        "means the numbers are not evidence until the judge prompt is fixed."
    )
    return 1 if verdict == "UNTRUSTED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
