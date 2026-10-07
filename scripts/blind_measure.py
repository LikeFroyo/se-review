"""Measure what the guidelines contribute, blind, scored by concern.

G19 is the open question this instrument exists for: the corpus scores detection and severity in
one number, so the headline cannot say which of them the skill moves. The independent blind
re-measurement in `evals/README.md` answers it -- detection +4.2 points, severity +33.3 -- and a
competent fresh reviewer finds 23 of 24 planted defects unaided. That measurement is recorded as
prose and its runner was never committed, so it cannot be re-run, re-scored on the three concerns,
or checked. This is that runner.

Three properties make it a measurement rather than another in-session comparison, and each is a
methodological choice that costs something:

**Fresh session per arm.** One model call per (fixture, arm). Nothing carries over, so the second
arm cannot see what the first concluded.

**Docstrings and comments stripped from the fixture.** The repo's convention puts the planted
defect in the docstring -- `CRITICAL DEFECT: ...` -- which is a confound: a reviewer that reads the
docstring is not detecting anything, it is transcribing. Re-serialising through `ast` removes that
without changing behaviour, so the code still fails the way the fixture intends.

**The bare arm has no domain knowledge at all.** Not an earlier guideline set -- no `domains/`
directory, so none of the 87 guidelines and none of the 17 sub-domains. This is *stronger* than the
comparison `evals/README.md` records, which used a reverted skill retaining 36 guidelines, and it is
the direction that matters: if a reviewer with no guidelines still finds the defect, then detection
does not need the guidelines, and the severity gap is the skill's whole claim.

What it cannot do: it costs two reviewer calls per fixture, so it will never cover 102 fixtures.
It is a small instrument pointed at the question, not a replacement for the corpus, and the rates it
prints carry that sample size in every line.

Identity is never recorded. The judge enters as a digest, the convention every other writer here
uses, so two runs can be compared without naming what ran.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import mismatch_probe as MP  # noqa: E402
import run_evals as R  # noqa: E402

ARMS = ("full", "bare")


def strip_annotations(source: str) -> str | None:
    """Re-serialise Python with docstrings and comments removed.

    Returns `None` when the source does not parse, and the caller keeps the original rather than
    substituting a stripped-but-different file: a fixture that will not parse is a finding about
    the corpus, and quietly passing it through unstripped would put the docstring confound back
    into the measurement while the report claimed it was gone.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
    try:
        return ast.unparse(ast.fix_missing_locations(tree))
    except Exception:  # noqa: BLE001 -- the caller keeps the original and says so
        return None


def stage_bare(dest: Path) -> None:
    """Stage the skill with no domain knowledge, rather than an earlier set of it.

    `SKILL.md` and `shared/` stay: the output contract is not what is under test, and removing it
    would measure the difference between a review and a non-review. `domains/` goes, and with it all
    87 guidelines and 17 sub-domains.
    """
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("SKILL.md", "shared"):
        src = REPO / name
        if src.is_dir():
            import shutil
            shutil.copytree(src, dest / name, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        elif src.is_file():
            import shutil
            shutil.copy2(src, dest / name)


def stage_stripped_fixture(eval_item: dict, dest: Path) -> tuple[bool, str]:
    """Stage the fixture with docstrings removed, reporting whether that actually happened."""
    import shutil
    dest.mkdir(parents=True, exist_ok=True)
    stripped_all = True
    for rel in eval_item.get("files", []):
        src = REPO / rel
        if not src.is_file():
            stripped_all = False
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix == ".py":
            text = strip_annotations(src.read_text(encoding="utf-8"))
            if text is None:
                out.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                stripped_all = False
                continue
            out.write_text(text, encoding="utf-8")
        else:
            shutil.copy2(src, out)
    return stripped_all, ""


def pick(ids: list[int] | None, corpus: dict, count: int) -> list[int]:
    """Fixtures to measure: the ones carrying the most severity and remediation assertions.

    Severity and remediation are the claims the blind re-measurement found the skill moving, so a
    fixture with no severity assertion cannot answer the question -- it can only report detection,
    which the re-measurement says the skill barely affects.
    """
    if ids:
        return sorted(ids)
    split = MP.concern_split(corpus)["per_fixture"]
    ranked = sorted((i for i, r in split.items() if r["severity"] >= 2 and r["remediation"] >= 1),
                    key=lambda i: -(split[i]["severity"] + split[i]["remediation"]))
    return ranked[:count]


def measure_one(eval_item: dict, arm: str, model: str | None, judge: str | None,
                timeout: int) -> dict:
    """One fixture, one arm: fresh workspace, one review, graded on the three concerns."""
    eid = eval_item["id"]
    name = R.eval_name(eid)
    work = R.stage_root() / f"blind-{name}-{arm}-{R.os.urandom(3).hex()}"
    work.mkdir(parents=True, exist_ok=True)
    if arm == "bare":
        stage_bare(work)
    else:
        R.stage_skill(work, arm="with_skill")
    stripped, why = stage_stripped_fixture(eval_item, work)
    try:
        review, _stream = R.run_model(R.absolute_prompt(eval_item, work), work, timeout, model)
    except Exception as exc:  # noqa: BLE001 -- the reason is the datum
        return {"eval_id": eid, "arm": arm, "ok": False, "reason": f"{type(exc).__name__}: {exc}",
                "stripped": stripped}
    body = review or ""
    if not body.strip():
        return {"eval_id": eid, "arm": arm, "ok": False, "reason": "no review body", "stripped": stripped}
    try:
        verdicts = R.grade(body, eval_item["assertions"], timeout, Path(tempfile.mkdtemp()), judge)
    except Exception as exc:  # noqa: BLE001
        return {"eval_id": eid, "arm": arm, "ok": False,
                "reason": f"grade: {type(exc).__name__}: {str(exc)[:70]}", "stripped": stripped}
    bucket = {"detection": [0, 0], "severity": [0, 0], "remediation": [0, 0]}
    for text, v in zip(eval_item["assertions"], verdicts):
        c = bucket[MP.concern(text)]
        c[0] += bool(v.get("passed"))
        c[1] += 1
    return {"eval_id": eid, "arm": arm, "ok": True, "stripped": stripped,
            "concerns": bucket, "body_len": len(body)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ids", default="", help="comma-separated eval ids; default: the fixtures "
                                              "carrying the most severity and remediation")
    ap.add_argument("--count", type=int, default=6, help="how many fixtures when --ids is absent")
    ap.add_argument("--model", default=None, help="reviewer model; pin it")
    ap.add_argument("--judge-model", default=None, help="judge model; pin it, or grading falls "
                                                         "back to the runner's own default")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--write", action="store_true", help="record the result as evidence")
    ap.add_argument("--iteration", default="iteration-1")
    args = ap.parse_args()

    corpus = {e["id"]: e for e in R.load_json(REPO / "evals" / "evals.json")["evals"]}
    ids = pick([int(x) for x in args.ids.split(",") if x.strip()], corpus, args.count)
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    if not ids:
        print("  no fixture carries both a severity and a remediation assertion; nothing to measure")
        return 1

    print(f"\nBLIND MEASURE  {len(ids)} fixture(s) x {len(arms)} arm(s), fresh session each")
    print(f"  reviewer {args.model or 'UNPINNED'}  judge {args.judge_model or 'UNPINNED'}")
    print("  judge digest " + R.grader_digest())
    print("  fixtures: docstrings and comments stripped; bare arm has no domains/ directory\n")

    rows = []
    for eid in ids:
        item = corpus[eid]
        for arm in arms:
            got = measure_one(item, arm, args.model, args.judge_model, args.timeout)
            got["name"] = R.eval_name(eid)
            rows.append(got)
            if not got["ok"]:
                print(f"  {got['name'][:34]:<36} {arm:<6} NOT MEASURED -- {got['reason'][:48]}")
                continue
            c = got["concerns"]
            parts = "  ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(c.items()))
            print(f"  {got['name'][:34]:<36} {arm:<6} {parts}")

    print("\n  By concern, over the fixtures both arms produced a review for:")
    print(f"    {'concern':<14} {'full':>16} {'bare':>16} {'delta':>9}")
    summary = {}
    for concern in ("detection", "severity", "remediation"):
        acc = {a: [0, 0] for a in arms}
        paired = 0
        for eid in ids:
            got = {r["arm"]: r for r in rows if r["eval_id"] == eid and r["ok"]}
            if len(got) < 2:
                continue
            paired += 1
            for a in arms:
                c = got[a]["concerns"][concern]
                acc[a][0] += c[0]
                acc[a][1] += c[1]
        if not paired or not acc["full"][1] or not acc["bare"][1]:
            print(f"    {concern:<14} {'NOT MEASURED -- no fixture has both arms':>44}")
            continue
        f, b = acc["full"][1] and acc["full"][0] / acc["full"][1], acc["bare"][0] / acc["bare"][1]
        summary[concern] = {"full": acc["full"], "bare": acc["bare"], "delta": (f - b) * 100,
                            "fixtures": paired}
        print(f"    {concern:<14} {acc['full'][0]:>4}/{acc['full'][1]:<3} {f:>7.1%}"
              f" {acc['bare'][0]:>5}/{acc['bare'][1]:<3} {b:>7.1%} {(f-b)*100:>+8.1f}")

    dest = REPO / "evals" / args.iteration / "blind_measure.json"
    if args.write:
        dest.write_text(json.dumps({
            "fixtures": ids, "arms": arms, "rows": rows, "summary": summary,
            "grader_config": R.grader_digest(),
            "note": "Reviewer identity is deliberately absent; compare on the grader digest.",
        }, indent=2) + "\n", encoding="utf-8")
        print(f"\n  written to {dest.relative_to(REPO)}")
    print("\n  Read the delta column, not the absolute rates. This is a small sample measured")
    print("  blind, so it bounds the claim rather than establishing it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())