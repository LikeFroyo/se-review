"""How much of a fixture can a review of the wrong file collect?

Every graded number in this repository is a score against an assertion list, and an
assertion list that a review of an unrelated file also satisfies cannot tell a good
review from a bad one. This measures that directly, per fixture, without spending a
reviewer call: it takes one stored review as a probe and grades it against each fixture's
assertions. Whatever the probe collects is the floor of that fixture's scale, and
`100 - floor` is the span a real effect has to fit inside.

That span is the whole question for the suppression experiment, whose kill criterion is a
40-point difference in false-positive rate. Measured 2026-10-05 over ids 80-91: the
`suppress_*` family collects 55.6-66.7 percent from an unrelated review and so cannot move
40 points at all, while `suppression_blind_*` collects 10.0-20.0 percent and can. Six of
twelve fixtures were unrunnable and would have returned a guaranteed null that read as
"suppression is harmless".

Three rules this script holds itself to, each of a defect it was built after:

A count names its denominator. A run that dies on the first malformed reply reports the
fixtures that worked, which is a better-looking number and a wrong one. Failures are
counted and printed, never dropped.

The floor is one grading call per fixture, so its resolution is one assertion -- 11.1 points
on a nine-assertion fixture, 20 on a five-assertion one. Read a difference smaller than that as
unmeasured rather than as a change. Measured over the corpus, that is exactly where the noise
sat: re-running after the no-axis rewrite moved three fixtures by precisely one assertion each
(ids 39, 43, 101, reading 0/9 -> 1/9, 0/10 -> 1/10, 1/5 -> 2/5) while the fixtures that had
been rewritten moved by three and four assertions (ids 80-85, -33 to -44 points). The rewrite
is the signal; the three are the resolution of the instrument.

Identity is never recorded. The judge enters as a digest, the same convention every other
writer uses, so two runs can be compared without naming what ran.

The kill criterion is a parameter, not an assumption, and the verdict is per fixture. A
single number over twelve fixtures would hide that the answer differs by family.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import run_evals as R  # noqa: E402

DEFAULT_PROBE = "evals/iteration-1/eval-clean/with_skill/review.md"


# Two shapes of assertion are collectable by a review that found nothing, and a first
# attempt at spotting them by regex caught 7 of 860 -- which would have said the corpus was
# clean. It missed the mechanism on the fixtures with the worst floors:
#
#   absence claims      "Does NOT report the unbounded queue as unbounded growth" -- a review
#                       that reports nothing satisfies this completely.
#   format contracts    "Output includes 'Aligns well'", "'Gated by' line is present" -- any
#                       review honouring the output format satisfies these whatever it
#                       found, so they measure compliance, not review quality.
#
# Fixtures 80-85 collect 55.6-66.7 percent from an unrelated review and that is where four
# absence claims and two format contracts sit per fixture. Fixtures 86-91 pin the count
# ("Exactly 1 finding above Info severity") and collect 10-20 percent.
#
# So this predicts the floor without spending a grading call, and the measurement above
# remains the ground truth it is checked against. A prediction that disagrees with the
# measurement is a finding about one of them, and that disagreement is printed.
ABSENCE_CLAIM = re.compile(
    r"^\s*(zero|no|not|none)\b|does not\b|is not (reported|graded|present|raised)|"
    r"are not (reported|graded|present|raised)|remains? (absent|unreported)", re.I)
COUNT_PINNED = re.compile(
    r"\bexactly\b|\bat (most|least)\b|\b\d+\s+(findings?|of the\b|assertions?)", re.I)
# Quote-agnostic because the corpus spells these both ways -- `Output includes 'Aligns well'`
# and a backticked variant -- and a pattern matching only one of them reported 7 of 860
# assertions as collectable when the true count is 59.
# The clause an absence-claim rewrite uses to bind itself to a positive observation. Its
# presence is the corpus asserting that this assertion cannot be collected by silence, and the
# measurement in `measure()` is what checks whether that claim holds.
ENGAGEMENT_CLAUSE = re.compile(
    r"as a conclusion|having named|reaches it|by naming that|rather than by omitting|"
    r"rather than merely omitting|has read|having engaged", re.I)

# A count of zero discriminates nothing. A review that reports nothing reports zero.
ZERO_COUNT = re.compile(r"\bexactly\s+0\b|\b0\s+findings\b|\bzero findings\b", re.I)
FORMAT_CONTRACT = re.compile(
    r"output includes|aligns well|gated by|header matches pattern|"
    r"\b(mean|final) (score|grade)\b follows|\blines? (present|is present)\b", re.I)


def collectable(text: str) -> str | None:
    """Why a review reporting nothing could satisfy this assertion, or None if it could not.

    An absence claim and a format contract are both satisfied by silence; they are reported
    separately because authoring fixes them differently -- an absence claim needs a count
    bound attached to it, a format contract does not belong in a quality panel at all.
    """
    # Format contracts are checked first. Testing the count pin first meant
    # "Header matches pattern: 0 findings - C:0 M:0 m:0 i:0" was scored as discriminating,
    # because "0 findings" matched the count pattern -- and a pinned count of *zero* is the
    # one count a review that read nothing also reports. Six fixtures carried that assertion
    # on the verdict side as a result.
    if FORMAT_CONTRACT.search(text):
        return "format contract"
    # An assertion that requires naming something specific is not satisfied by silence, whatever
    # else it says. Checked before the count rules, because binding an absence to the positive
    # observation that licenses it makes it discriminating even when the count is zero -- and a
    # regex reading only the count scored those as collectable, undoing the fix that produced
    # them. The clause is a convention the corpus authoring applies deliberately, and it is
    # visible in the assertion text rather than inferred.
    if ENGAGEMENT_CLAUSE.search(text):
        return None
    if ZERO_COUNT.search(text):
        # Its own category. A pinned count is discriminating because silence cannot hit it,
        # except when the count is zero -- silence hits zero every time. Filed as an absence
        # claim it would lose the count, and filed as pinned it would look safe.
        return "zero count"
    if COUNT_PINNED.search(text):
        return None
    if ABSENCE_CLAIM.search(text):
        return "absence claim"
    return None


def predicted_floor(corpus: dict, ids: list[int], role: str | None = "verdict") -> dict:
    """Static floor estimate per fixture, in percent, with no grading call spent.

    `role` restricts to one side of the verdict/probe split, and the default is `verdict`
    because that is the panel the quality rate is computed from. Scoring the whole panel
    while the rate is taken over part of it answers a question nobody asked: it reported
    fixtures 80-85 at 44-56 percent when, before the probe-role assertions that actually
    discriminate were moved onto the verdict side, the number that mattered was different
    again.
    """
    out = {}
    for eid in ids:
        entry = corpus.get(eid) or {}
        assertions = entry.get("assertions", [])
        roles = entry.get("assertion_roles") or []
        if role and len(roles) == len(assertions):
            assertions = [a for a, r in zip(assertions, roles) if r == role]
        if not assertions:
            continue
        kinds = [collectable(a) for a in assertions]
        free = sum(1 for k in kinds if k)
        out[eid] = {
            "free": free,
            "total": len(assertions),
            "free_pct": round(100.0 * free / len(assertions), 1),
            "format_contracts": kinds.count("format contract"),
            "absence_claims": kinds.count("absence claim"),
            "zero_counts": kinds.count("zero count"),
        }
    return out


# G19: the corpus scores detection and severity in one number, so the headline cannot say which
# of the two the skill contributes. The blind re-measurement says it is overwhelmingly the
# second -- a fresh reviewer detects 23 of 24 defects unaided (+4.2 pts), while severity
# discipline is worth +33.3. These two classes read off the assertion text rather than off a
# hand-maintained list, because a list would drift from the corpus it claims to describe and the
# split would go on reporting a stale ratio.
#
# The classes are deliberately coarse and mutually exclusive, detection first: a count of
# findings above Info is the assertion that fails when nothing is found, so it is a detection
# claim even though it mentions severity. Only "graded", "rung", and "axis" reach the severity
# class, which keeps "Exactly 1 finding above Info severity" on the detection side where it
# belongs.
DETECTION = re.compile(
    r"exactly\s+\d+\s+findings?|findings? above info|^no findings|zero findings|"
    r"\bis reported\b|\bidentif(?:ies|ying)\b|\bfailure scenario\b|"
    r"\bnames?\b|\bcites?\b|\bdoes not\b|\bnotes?\b|\bfix\b|\baxis\b|\bgrades?\b",
    re.I)
SEVERITY = re.compile(r"\bgraded\b|\bgrading\b|\brung\b|\bseverity\b|\baxis\b", re.I)

# Anchored to the leading word, because the corpus writes a remediation assertion as a sentence
# beginning "Fix ...". Matching the word anywhere put "Identifies the guard that RETURNS early"
# into remediation, on the strength of a verb inside a clause about a defect. That is the sort of
# thing a regex does when it is asked to read meaning.
REMEDIATION = re.compile(r"^\s*fix\b|\bthe fix\b|\bfix (replaces|returns|adds|routes|"
                         r"registers|makes|propagates|wraps|removes|deletes)\b", re.I)

# A count of findings above Info mentions severity but tests detection: it fails exactly when
# the review found nothing. Checked first so the word does not pull it across. Covers "Exactly N
# findings", "N findings above Info", and the zero forms -- "Zero findings above Info severity"
# reads as a severity claim to anything matching on the word, and is the assertion that matters
# most on a fixture where the correct answer is nothing.
COUNT_OF_FINDINGS = re.compile(
    r"^\s*(exactly\s+\d+\s+findings?|\d+\s+findings?|findings? above info|"
    r"zero findings|no findings|zero\s+(?:above-info\s+)?findings)", re.I)


def concern(text: str) -> str:
    """Which claim an assertion tests, on the three axes the blind measurement used.

    `detection`     did the review find it at all -- the count of findings above Info, and
                    naming the mechanism, the failure scenario, the constraint.
    `severity`      given that you found it, how badly does it matter -- the rung.
    `remediation`   given that you found it, is the proposed fix right.

    Three buckets rather than two because the blind re-measurement scored three, and a two-way
    split would file "Fix replaces the price-keyed guard" under detection -- which credits the
    skill with correctly repairing a defect that detection is supposed to be about.

    Detection wins ties. "Exactly 1 finding above Info severity" reads like a severity claim
    because the word appears, but it fails precisely when the review found nothing. Getting that
    backwards would credit the skill with the axis it does not have.
    """
    if SEVERITY.search(text) and not COUNT_OF_FINDINGS.match(text):
        return "severity"
    if REMEDIATION.search(text) and not COUNT_OF_FINDINGS.match(text):
        return "remediation"
    return "detection"


def concern_split(corpus: dict, ids: list[int] | None = None,
                  role: str | None = "verdict") -> dict:
    """Assertion counts by concern, per fixture and corpus-wide, with no grading call spent."""
    per, totals = {}, {"detection": 0, "severity": 0, "remediation": 0}
    for eid in (ids if ids is not None else sorted(corpus)):
        entry = corpus.get(eid) or {}
        asserts = entry.get("assertions", [])
        roles = entry.get("assertion_roles") or []
        if role and len(roles) == len(asserts):
            asserts = [a for a, r in zip(asserts, roles) if r == role]
        if not asserts:
            continue
        k = {"detection": 0, "severity": 0, "remediation": 0}
        for a in asserts:
            k[concern(a)] += 1
        per[eid] = {**k, "total": len(asserts)}
        for key in totals:
            totals[key] += k[key]
    totals["total"] = sum(totals.values())
    return {"per_fixture": per, "totals": totals}


def parse_range(text: str) -> tuple[int, int]:
    lo, _, hi = text.partition("-")
    return int(lo), int(hi or lo)


def probe_one(body: str, assertions: list[str], judge: str | None) -> tuple[int, int, str]:
    """Grade the probe against one fixture. Returns (collected, total, failure).

    A failure is returned, not raised. A reply that is not a well-formed verdict array is
    evidence about the judge and not a missing data point, and dropping it would report a
    floor computed over fewer fixtures than the run set out to measure.
    """
    try:
        verdicts = R.grade(body, assertions, 240, Path(tempfile.mkdtemp()), judge)
    except Exception as exc:  # noqa: BLE001 -- the reason is reported, not swallowed
        return 0, len(assertions), f"{type(exc).__name__}: {str(exc)[:90]}"
    got = [bool(v.get("passed")) for v in verdicts]
    if len(got) != len(assertions):
        return 0, len(assertions), f"judge returned {len(got)} verdicts for {len(assertions)} assertions"
    return sum(got), len(assertions), ""


def measure(ids: list[int], body: str, judge: str | None, kill: float) -> dict:
    corpus = {e["id"]: e for e in R.load_json(REPO / "evals" / "evals.json")["evals"]}
    rows, failed = [], []
    for eid in ids:
        if eid not in corpus:
            raise SystemExit(f"no eval with id {eid}")
        got, total, why = probe_one(body, corpus[eid]["assertions"], judge)
        if why:
            failed.append({"eval_id": eid, "name": corpus[eid].get("name")
                           or corpus[eid]["files"][0], "reason": why})
            continue
        floor = got / total if total else 0.0
        span = (1.0 - floor) * 100
        rows.append({"eval_id": eid, "name": corpus[eid].get("name") or corpus[eid]["files"][0],
                     "collected": got, "total": total, "floor_pct": round(floor * 100, 1),
                     "span_points": round(span, 1),
                     "resolves_kill_criterion": span >= kill})
    return {"probe_review": None, "rows": rows, "ungradeable": failed,
            "asked": len(ids), "graded": len(rows), "kill_criterion_points": kill}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--range", default="80-91", help="eval id range, inclusive")
    ap.add_argument("--probe-review", default=DEFAULT_PROBE,
                    help="stored review to grade against every fixture. It should be a "
                         "review of a file unrelated to the range, or the floor is a "
                         "score, not a floor.")
    ap.add_argument("--judge-model", default=None)
    ap.add_argument("--kill", type=float, default=40.0,
                    help="points a true effect must be able to move")
    ap.add_argument("--iteration", default="iteration-1")
    ap.add_argument("--write", action="store_true", help="record the result as evidence")
    args = ap.parse_args()

    probe = REPO / args.probe_review
    if not probe.is_file():
        raise SystemExit(f"no probe review at {args.probe_review}\n"
                         "The floor is measured by grading something unrelated, so the probe "
                         "has to exist. Pick a stored review of a different fixture.")
    lo, hi = parse_range(args.range)
    out = measure(list(range(lo, hi + 1)), probe.read_text(), args.judge_model, args.kill)
    out["probe_review"] = args.probe_review
    # A digest, never an identity: comparability without naming what ran.
    out["judge_model_config"] = R.config_digest(args.judge_model) if args.judge_model else "unpinned"
    out["grader_config"] = R.grader_digest()

    print(f"\nMISMATCH PROBE  fixtures {lo}-{hi}  kill criterion {args.kill:g} points")
    print(f"  probe: {args.probe_review}")
    print(f"  judge {out['judge_model_config']}  grader {out['grader_config']}")
    print(f"  an unrelated review graded against each fixture's assertions\n")
    for r in out["rows"]:
        mark = "resolves" if r["resolves_kill_criterion"] else "CANNOT RESOLVE"
        print(f"  {r['eval_id']:>4}  {r['name'].split('/')[-1][:40]:<42}"
              f"{r['collected']:>3}/{r['total']:<3} floor {r['floor_pct']:5.1f}%"
              f"  span {r['span_points']:5.1f}  {mark}")
    for f in out["ungradeable"]:
        print(f"  {f['eval_id']:>4}  {f['name'].split('/')[-1][:40]:<42}UNGRADEABLE  {f['reason']}")

    # The denominator is the number asked for, not the number that worked.
    if out["graded"] != out["asked"]:
        print(f"\n  {out['graded']} of {out['asked']} fixtures graded; "
              f"{len(out['ungradeable'])} ungradeable. The floors above cover the graded "
              f"fixtures only.")
    if not out["rows"]:
        print("\nVERDICT: NOT MEASURED -- every reply was ungradeable, so no floor is reported.")
        return 1

    blocked = [r for r in out["rows"] if not r["resolves_kill_criterion"]]
    print(f"\n  floors span {min(r['floor_pct'] for r in out['rows']):.1f}%"
          f" to {max(r['floor_pct'] for r in out['rows']):.1f}%")
    if blocked:
        print(f"VERDICT: {len(blocked)} of {len(out['rows'])} fixtures cannot resolve a "
              f"{args.kill:g}-point criterion.")
        print("  An assertion an unrelated review satisfies cannot distinguish a good review")
        print("  from a bad one, so a difference smaller than the span is not attributable to")
        print("  the thing being measured. Running these returns a null by construction.")
        for r in blocked:
            print(f"    blocked: {r['eval_id']} {r['name'].split('/')[-1]} (span {r['span_points']})")
    else:
        print(f"VERDICT: every graded fixture has at least {args.kill:g} points of span.")

    if args.write:
        dest = REPO / "evals" / args.iteration / "mismatch_probe.json"
        dest.write_text(json.dumps(out, indent=2) + "\n")
        print(f"\n  written to {dest.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())