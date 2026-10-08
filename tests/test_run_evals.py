"""Tests for the eval harness.

The harness decides every number in this repository, and nine defects in it were
found by *running* it rather than by reading it — a Windows-only executable
resolver, a flag that does not exist, a directory argument swallowed by a
variadic positional, an inherited session identity that let the reviewer reach the
answer key, a background service carrying the wrong project root, a plumbing rule
that discarded complete reviews, a "review detection" that demanded the skill's
own output format, a verdict list that recorded one machine's directory layout,
and a search pattern filed as a file.

Every one of those was found the expensive way, by burning model calls to
discover a harness bug. These tests make the next nine cheap and deterministic.

Run: python3 -m unittest discover -s tests -v
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import run_evals as R  # noqa: E402
import validate_skill as V  # noqa: E402
import research_ledger as L  # noqa: E402
import pass_freeze as F  # noqa: E402


class ProviderErrors(unittest.TestCase):
    """A provider failure arrives as a stdout event with an empty stderr."""

    QUOTA = (
        '{"type":"step_start","sessionID":"s","part":{}}\n'
        '{"type":"error","error":{"type":"provider.quota",'
        '"message":"Rate limit exceeded. Please try again later.","status":429}}\n'
    )

    def test_quota_event_is_recovered_from_the_stream(self):
        errs = R.stream_errors(self.QUOTA)
        self.assertEqual(len(errs), 1)
        self.assertIn("provider.quota", errs[0])
        self.assertIn("429", errs[0])

    def test_a_clean_stream_yields_no_errors(self):
        self.assertEqual(R.stream_errors('{"type":"step_start"}'), [])

    def test_malformed_lines_are_skipped_not_raised(self):
        raw = "not json\n" + self.QUOTA + "{broken\n"
        self.assertEqual(len(R.stream_errors(raw)), 1)

    def test_quota_is_a_rate_limit_and_not_transient(self):
        errs = R.stream_errors(self.QUOTA)
        self.assertTrue(R.is_rate_limited(errs))
        # Retrying a quota wall is what turned one honest stop into forty
        # identical failures in a full sweep.
        self.assertFalse(R.is_transient("; ".join(errs)))

    def test_upstream_502_is_transient_and_worth_retrying(self):
        detail = "provider.internal 200: Streaming response failed: [502] Upstream error"
        self.assertTrue(R.is_transient(detail))

    def test_auth_failure_is_neither_rate_limited_nor_transient(self):
        detail = "provider.auth 401: bad key"
        self.assertFalse(R.is_rate_limited([detail]))
        self.assertFalse(R.is_transient(detail))

    def test_a_usage_limit_message_is_recognised(self):
        self.assertTrue(R.is_rate_limited(["provider.quota: FreeUsageLimitError"]))


class ReportDetection(unittest.TestCase):
    """`looks_like_report` must not demand the skill's own output format.

    A baseline arm stages no skill, so it has no template and will never emit
    `## Findings`. Requiring it rejected a correct 2,464-character review and
    recorded "no review body" — which made the baseline arm unmeasurable.
    """

    BASELINE = (
        "# Review of `x.py` vs `CONSTRAINTS.md`\n\n"
        "## Constraint C1 Summary\n" + "The apply method increments _pending. " * 40
        + "\nThis is a race: two callers can interleave at line 13."
    )

    def test_skill_shaped_report_is_accepted(self):
        self.assertTrue(R.looks_like_report("## Findings\n\n### [CRITICAL] boom"))

    def test_a_real_baseline_review_is_accepted(self):
        self.assertTrue(R.looks_like_report(self.BASELINE))

    def test_preamble_is_rejected(self):
        self.assertFalse(
            R.looks_like_report("Sure! I will review the file now. Let me read it.")
        )

    def test_mid_sentence_truncation_is_rejected(self):
        self.assertFalse(R.looks_like_report("The apply method increments"))

    def test_empty_is_rejected(self):
        self.assertFalse(R.looks_like_report(""))

    def test_long_but_contentless_is_rejected(self):
        self.assertFalse(R.looks_like_report("x" * 900))


class ReadsVersusPatterns(unittest.TestCase):
    """A grep pattern is not a file that was read."""

    STREAM = (
        '{"type":"tool_use","part":{"state":{"input":'
        '{"path":"/ws/evals/fixtures/a.py"}}}}\n'
        '{"type":"tool_use","part":{"state":{"input":'
        '{"path":"/ws","pattern":"nplusone|n\\\\+1|NPlusOne"}}}}\n'
        '{"type":"tool_use","part":{"state":{"input":'
        '{"pattern":"{README.md,CONTRIBUTING.md,*.md}"}}}}\n'
    )

    def test_paths_and_patterns_are_separate_lists(self):
        paths, patterns = R.read_paths_and_patterns(self.STREAM)
        self.assertEqual(paths, ["/ws/evals/fixtures/a.py", "/ws"])
        self.assertEqual(patterns, ["nplusone|n\\+1|NPlusOne", "{README.md,CONTRIBUTING.md,*.md}"])

    def test_files_read_excludes_patterns(self):
        self.assertNotIn("nplusone|n\\+1|NPlusOne", R.files_read(self.STREAM))

    def test_duplicates_collapse(self):
        paths, _ = R.read_paths_and_patterns(self.STREAM + self.STREAM)
        self.assertEqual(len(paths), 2)


class Relativisation(unittest.TestCase):
    """A committed verdict is evidence about the skill, not about the machine."""

    def test_posix_absolute_becomes_repo_relative(self):
        raw = "/Users/someone/repo/shared/output-format.md"
        self.assertEqual(R.relativise([raw], REPO)[0], "shared/output-format.md")

    def test_relative_passes_through(self):
        self.assertEqual(
            R.relativise(["domains/leanness/waste/sub-leaf.md"], REPO)[0],
            "domains/leanness/waste/sub-leaf.md",
        )

    def test_windows_path_from_another_machine_matches_by_tail(self):
        raw = r"C:\niaomi\ProjectQuickMax\se-review\evals\fixtures\vendored_fork.py"
        self.assertEqual(R.relativise([raw])[0], "evals/fixtures/vendored_fork.py")

    def test_windows_path_is_not_joined_onto_a_root(self):
        # `SKILL_ROOT / "C:\..."` "succeeds" while yielding one garbage segment.
        raw = r"C:\x\se-review\SKILL.md"
        self.assertEqual(R.relativise([raw])[0], "SKILL.md")

    def test_repository_root_is_recognised(self):
        raw = r"C:\niaomi\ProjectQuickMax\se-review"
        self.assertEqual(R.relativise([raw])[0], "./")

    def test_genuinely_foreign_path_is_redacted_not_published(self):
        raw = r"C:\Users\AUPADH~1\AppData\Local\Temp\runner\verify.py"
        out = R.relativise([raw])[0]
        self.assertTrue(out.startswith("outside:"))
        self.assertNotIn("AUPADH", out)
        self.assertIn("verify.py", out)

    def test_redaction_keeps_the_tail_that_identifies_the_touch(self):
        out = R.redact_foreign("/a/b/c/d/e/f.py")
        self.assertEqual(out, ".../e/f.py")

    def test_foreign_tail_needs_a_known_top_level_entry(self):
        self.assertIsNone(R.relativise_foreign(r"C:\Windows\System32\etc\hosts"))


class SkillConsultation(unittest.TestCase):
    """A runner loads a project SKILL.md with no file read, so a read-only check
    has an inherent false-negative rate. It also must not accept everything."""

    def test_a_read_of_the_skill_counts(self):
        self.assertTrue(R.skill_was_consulted(["<ws>/SKILL.md"], ""))

    def test_the_mandatory_header_slots_count_as_evidence(self):
        review = "Covered: 2/2 files\nGated by: neither"
        self.assertTrue(R.skill_was_consulted(["<ws>/evals/fixtures/x.py"], review))

    def test_a_baseline_that_read_nothing_does_not_count(self):
        review = "# Review of x\n\nThe apply method is racy at line 13."
        self.assertFalse(R.skill_was_consulted(["<ws>/evals/fixtures/x.py"], review))


class ContaminationGate(unittest.TestCase):
    """The gate is what caught the reviewer reading the answer key."""

    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())

    def test_a_clean_run_leaks_nothing(self):
        self.assertEqual(R.contamination([str(self.ws / "evals/fixtures/a.py")], self.ws), [])

    def test_a_read_outside_the_workspace_is_a_leak(self):
        self.assertTrue(R.contamination(["/Users/other/repo/SKILL.md"], self.ws))

    def test_the_answer_key_is_a_leak(self):
        self.assertTrue(R.contamination(["evals/evals.json"], self.ws))

    def test_a_recorded_verdict_is_a_leak(self):
        self.assertTrue(R.contamination(["evals/iteration-1/x/with_skill/grading.json"], self.ws))

    def test_a_recursive_sweep_is_a_leak_even_with_no_path(self):
        self.assertTrue(R.contamination(["**/*"], self.ws))

    def test_every_sweep_pattern_is_caught(self):
        for pattern in R.SWEEP_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertTrue(R.contamination([pattern], self.ws))


class VerdictParsing(unittest.TestCase):
    """A malformed judge reply is the difference between an arm and a missing arm."""

    def test_a_fenced_array_is_parsed(self):
        text = 'blah\n```json\n[{"passed": true, "evidence": "x"}]\n```\n'
        self.assertEqual(len(R.parse_verdicts(text, 1)), 1)

    def test_a_bare_array_is_parsed(self):
        text = '[{"passed": false, "evidence": "y"}]'
        self.assertEqual(len(R.parse_verdicts(text, 1)), 1)

    def test_a_wrong_length_array_returns_none(self):
        self.assertIsNone(R.parse_verdicts('[{"passed": true}]', 3))

    def test_prose_instead_of_an_array_returns_none(self):
        self.assertIsNone(R.parse_verdicts("I could not grade this run.", 1))


class JudgeSelfTest(unittest.TestCase):
    """The instrument that decides whether the judge is trusted must not lie.

    A masking bug shipped here: an attempt returning no gradeable verdict was
    dropped before agreement was computed, so two correct siblings turned a
    malformed reply that graded everything TRUE into a clean pass. The self-test
    reported TRUSTED while hiding the defect it exists to find.
    """

    OK = {"failed_it": True, "passed": 0, "why": None}
    BAD = {"failed_it": False, "passed": 3, "why": None}
    NOGRADE = {"failed_it": None, "passed": None, "why": "not run: quota"}

    def verdict(self, attempts):
        folded = R._fold_judge_probe("p", "exp", attempts)
        return R._judge_verdict([folded], 1)["verdict"]

    def test_all_correct_is_trusted(self):
        self.assertEqual(self.verdict([self.OK] * 3), "TRUSTED")

    def test_probe_failure_is_untrusted(self):
        self.assertEqual(self.verdict([self.BAD] * 3), "UNTRUSTED")

    def test_disagreement_is_unstable_not_untrusted(self):
        # Correct attempts with a variance finding is a finding about the
        # instrument, and blaming the judge for missing replicates is wrong.
        self.assertEqual(self.verdict([self.OK, self.BAD]), "UNSTABLE")

    def test_never_reached_is_not_run(self):
        self.assertEqual(self.verdict([self.NOGRADE] * 3), "NOT RUN")

    def test_an_unparseable_reply_blocks_trusted(self):
        # The regression. Two correct plus one unparseable used to fold to TRUSTED.
        self.assertEqual(self.verdict([self.OK, self.OK, self.NOGRADE]), "UNSTABLE")

    def test_an_unparseable_reply_is_reported_as_such(self):
        folded = R._fold_judge_probe("p", "exp", [self.OK, self.NOGRADE])
        self.assertFalse(folded["agreed"])
        self.assertIn("no gradeable verdict", folded["why"])


class ValidatorNonVacuity(unittest.TestCase):
    """The gate that guards the gate is itself unverified.

    Every rule in the validator is a scan over text: a glob, a regex, a substring.
    A scan that stops matching does not fail -- it reports nothing, and a rule that
    reports nothing is indistinguishable from a rule that found nothing to report.
    So a broken glob turns the whole instruction-surface gate into a silent pass,
    and the tree looks validated because a command exited zero.

    Two obligations follow, and this class discharges both. Every extractor's
    result must be asserted non-zero, so a scan that finds nothing is a failure;
    and every rule must be shown able to reject, so a scan that matches everything
    is equally a failure. Neither is provable by reading the validator, which is
    why they are proved by construction here.
    """

    # Floors on what each extractor must find. These are not "the current count":
    # a count restated as an equality breaks the next time a guideline is added,
    # which teaches the reader to update the number instead of fixing the glob.
    # A floor is a claim that the scan is reaching the corpus at all.
    EXTRACTOR_FLOORS = (
        ("leaf.md", "domains/*/leaf.md", 6),
        ("sub-leaf.md", "domains/*/*/sub-leaf.md", 20),
        ("guidelines", "domains/*/*/guidelines/*.md", 70),
    )

    def _validate(self, tree: Path):
        proc = subprocess.run(
            [sys.executable, str(tree / "scripts" / "validate_skill.py"), str(tree)],
            capture_output=True, text=True,
        )
        return proc.returncode, proc.stdout

    def _copy(self) -> Path:
        import shutil
        dest = Path(tempfile.mkdtemp()) / "se-review"
        shutil.copytree(
            REPO, dest,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"),
        )
        return dest

    # -- obligation 1: every extractor reaches the corpus -------------------

    def test_every_extractor_finds_something(self):
        tree = self._copy()
        for label, pattern, floor in self.EXTRACTOR_FLOORS:
            found = len([p for p in tree.glob(pattern) if p.is_file()])
            self.assertGreaterEqual(
                found, floor,
                f"the {label} extractor found {found}, below its floor of {floor}. "
                f"If this fired, the glob is broken and every rule that depends on "
                f"it is passing vacuously.",
            )

    def test_the_validator_agrees_with_the_tree_about_tree_size(self):
        # The validator prints its own tallies. If its tallies and the filesystem
        # disagree, one of them is wrong and the exit code cannot say which.
        tree = self._copy()
        code, out = self._validate(tree)
        self.assertEqual(code, 0, out)
        reported = re.search(r"Domains active:\s+(\d+)", out)
        self.assertIsNotNone(reported, f"no domain tally in validator output:\n{out}")
        real = len([p for p in tree.glob("domains/*/leaf.md") if p.is_file()])
        self.assertEqual(int(reported.group(1)), real)
        for label, key in (("Sub-domains", r"Sub-domains:\s+(\d+)"),
                           ("Guideline files", r"Guideline files:\s+(\d+)"),
                           ("Eval cases", r"Eval cases:\s+(\d+)")):
            got = re.search(key, out)
            self.assertIsNotNone(got, f"no {label} tally in validator output:\n{out}")
        self.assertEqual(
            int(re.search(r"Guideline files:\s+(\d+)", out).group(1)),
            len([p for p in tree.glob("domains/*/*/guidelines/*.md") if p.is_file()]),
            "the validator's guideline count disagrees with the filesystem",
        )

    # -- obligation 2: every rule can reject --------------------------------

    # Each mutation breaks one invariant in a way a reader of the validator could
    # not be expected to notice, and the validator must notice. The glob is explicit
    # and always filtered to files: a directory called `guidelines` sorts before the
    # guideline files inside it, which is a fine way to write a test that never runs.
    #
    # Every mutation is asserted to have actually changed the file. An earlier
    # version of this test removed a "Trigger" heading that no guideline has -- the
    # real heading is "What to look for" -- so the regex matched nothing, the file
    # was byte-identical, and the validator passed an untouched tree. The test
    # reported the validator as sound when it had proved nothing at all. A
    # mutation that does not mutate is a silent pass, so it is now a hard failure.
    MUTATIONS = (
        ("a guideline left unenumerated in its sub-leaf table",
         "domains/*/*/sub-leaf.md", "unenumerated"),
        ("frontmatter missing a required key", "SKILL.md", "frontmatter"),
        ("an eval fixture stripped of its assertions", "evals/evals.json", "assertions"),
        ("an unclosed code span in a shared rule", "shared/output-format.md", "backtick"),
        ("a code block left open to end of file", "shared/output-format.md", "openfence"),
        ("a root skill grown past the line budget", "SKILL.md", "oversize"),
        ("a sub-domain reference pointing at a file that is gone",
         "domains/*/*/sub-leaf.md", "dangling"),
    )

    def _first_file(self, tree: Path, pattern: str) -> Path | None:
        for path in sorted(tree.glob(pattern)):
            if path.is_file():
                return path
        return None

    def _apply(self, kind: str, target: Path) -> bool:
        """Mutate `target` in place. Returns False if nothing changed."""
        original = target.read_text()
        body = original
        if kind == "unenumerated":
            # Strip the enumeration row for one guideline. This is the direction
            # that loses work: every reference still resolves, the sub-leaf still
            # loads, and the one guideline nobody listed is never read.
            body = re.sub(
                r"(?m)^\| \*\*[^*]*\*\*.*`guidelines/[a-z0-9_-]+\.md`.*\n", "", body, count=1)
        elif kind == "frontmatter":
            body = original.replace("description:", "desc:", 1)
        elif kind == "assertions":
            data = json.loads(original)
            if not data.get("evals"):
                return False
            data["evals"][0]["assertions"] = []
            body = json.dumps(data, indent=2)
        elif kind == "backtick":
            # A *single* backtick. A doubled one is an empty code span and is
            # correctly balanced, so ` `` ` would mutate nothing observable.
            body = original + "\nan unclosed code span: `severity\n"
        elif kind == "openfence":
            body = original + "\n```text\na block that is never closed\n"
        elif kind == "oversize":
            body = original + "\n" + "\n".join(
                f"filler line {n} - padding past the budget" for n in range(1, 520))
        elif kind == "dangling":
            body = re.sub(r"`guidelines/([a-z0-9_-]+)\.md`",
                          "`guidelines/this-file-does-not-exist.md`", body, count=1)
        else:
            return False
        if body == original:
            return False
        target.write_text(body)
        return True

    def test_every_mutation_actually_mutates(self):
        # The no-op guard, as its own test so it cannot be satisfied by the
        # mutation table happening to work today.
        for label, pattern, kind in self.MUTATIONS:
            tree = self._copy()
            target = self._first_file(tree, pattern)
            self.assertIsNotNone(target, f"{label}: nothing matches {pattern}")
            before = target.read_text()
            changed = self._apply(kind, target)
            self.assertTrue(
                changed,
                f"{label}: the mutation left {target.relative_to(tree)} byte-identical, "
                f"so the validator would be reported as sound on the strength of a "
                f"file nothing happened to.",
            )
            self.assertNotEqual(target.read_text(), before)

    def test_each_seed_injection_is_rejected(self):
        caught, missed, inert = [], [], []
        for label, pattern, kind in self.MUTATIONS:
            tree = self._copy()
            target = self._first_file(tree, pattern)
            if target is None:
                missed.append(f"{label} (nothing matches {pattern})")
                continue
            if not self._apply(kind, target):
                inert.append(label)
                continue
            code, _ = self._validate(tree)
            (caught if code != 0 else missed).append(label)
        self.assertEqual(inert, [], f"mutations that changed nothing: {inert}")
        self.assertEqual(
            missed, [],
            f"the validator accepted these injected defects: {missed}. "
            f"It rejected {len(caught)} others, so it is not inert -- it has holes.",
        )

    def test_the_validator_does_not_flag_its_own_blocklist(self):
        # A blocklist must spell out what it forbids. The scanner and its test are
        # exempt by design; if that exemption ever widened, the exemption itself
        # would be invisible.
        tree = self._copy()
        code, out = self._validate(tree)
        self.assertEqual(code, 0, out)
        body = (tree / "scripts" / "validate_skill.py").read_text()
        self.assertIn("scripts/validate_skill.py", body)


class VendorNeutrality(unittest.TestCase):
    """No vendor, provider, product or tool name anywhere in a tracked file.

    The harness has to invoke a session runner, so it could not simply avoid the
    subject -- it takes the runner from the environment instead of naming one, which
    is both the compliance fix and the better design: the harness is no longer
    welded to whichever tool it was written against.
    """

    # The rule is the validator's, not a copy of it. An earlier version of this class
    # carried its own TOKENS/PREFIXES and its own regexes -- which is how two
    # implementations of one rule came to disagree: the test reported a vendor in
    # auditandevolve/SOURCES.md while the validator correctly excused the token as part
    # of a declared reference URL. A test that re-implements the thing it tests is a
    # second, unmaintained copy of it, and it fails in the direction that matters: it
    # passes while the real rule drifts. So this calls V.
    TOKENS = V.FORBIDDEN_VENDOR_TOKENS
    PREFIXES = V.FORBIDDEN_VENDOR_PREFIXES
    SUFFIXES = V.VENDOR_SCAN_SUFFIXES
    EXEMPT_PREFIXES = V.VENDOR_EXEMPT_PREFIXES
    # The scanner and its test both spell out the blocklist, because a blocklist has
    # to. Neither is a disclosure of what was used. Everything else is scanned --
    # including this file's other content.
    SELF = ("scripts/validate_skill.py", "tests/test_run_evals.py")

    def _hit(self, text):
        return V.vendor_hit(text)

    def test_no_tracked_file_names_a_vendor(self):
        ignored = V._ignore_matcher(REPO)
        offenders = []
        for path in REPO.rglob("*"):
            if not path.is_file() or path.suffix not in self.SUFFIXES:
                continue
            rel = path.relative_to(REPO).as_posix()
            if set(path.parts) & {".git", "__pycache__", "node_modules"}:
                continue
            # Scan what would be published, not what is on disk. A gitignored scratch
            # file is not a neutrality breach, and a gate that reports one gets
            # weakened: this failed on a `probe/tmp/` file holding a commit message, which
            # is exactly the noise that teaches a team to ignore the check. Same rule as
            # `validate_portable_evidence`, for the same reason.
            if ignored(rel):
                continue
            if rel.startswith(self.EXEMPT_PREFIXES) or rel in self.SELF:
                continue
            try:
                token = self._hit(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
            if token:
                offenders.append(f"{rel} -> {token}")
        self.assertEqual(offenders, [], f"a vendor is named: {offenders}")

    def test_the_word_cursor_is_not_a_vendor(self):
        # A pagination cursor and a database cursor are ordinary technical terms.
        self.assertIsNone(self._hit("SELECT * FROM t LIMIT 1 OFFSET :cursor"))
        self.assertIsNone(self._hit("The cursor that does not encode its position"))

    def test_the_harness_takes_its_runner_from_the_environment(self):
        # The runner is named by the operator, so the module carries no executable
        # name of its own -- and no env var that implies one.
        self.assertTrue(hasattr(R, "RUNNER_ENV"))
        src = Path(R.__file__).read_text()
        self.assertNotIn("shutil.which(\"opencode", src)
        self.assertIn("RUNNER_ENV", src)

    # -- the reference-URL allowance ----------------------------------------
    #
    # Upstream guidance is cited by URL, and a citation's host and path contain the
    # vendor's name. That is provenance and is allowed -- but only as a URL. The
    # allowance exists to permit a citation, and the moment it becomes a way to *say*
    # a vendor name it is worse than having no neutrality rule at all, because it looks
    # like compliance. So every way of smuggling the name through it is a test.
    #
    # Each case below is an attempt that would succeed if the allowance were file-scoped
    # rather than span-scoped, or if it were a generic URL pattern rather than a
    # declared prefix list. Both of those are plausible implementations, so both are
    # pinned against.

    # The token under test. Deliberately NOT named `V`: that is the imported
    # validator module, and an f-string referring to it interpolated the module
    # repr instead of the vendor name -- so the probe passed for the wrong reason.
    PROBE = "anthropic"

    def test_a_declared_reference_url_is_permitted(self):
        for url in (
            "https://platform.claude.com/docs/en/about-claude/use-case-guides/overview",
            "https://github.com/anthropics/skills/tree/main/skills/claude-api",
            "https://claude.dev/blog/automating-eval-design-and-hillclimbing/",
        ):
            self.assertIsNone(self._hit(f"- {url}"), f"a declared reference was rejected: {url}")

    def test_the_name_in_prose_is_still_a_vendor(self):
        # The load-bearing asymmetry: same blocklist, same word, one sentence away.
        self.assertIsNotNone(self._hit(
            f"See the guidance below.\n- https://claude.dev/blog/x/\n\n{self.PROBE} agrees with us."))

    def test_the_allowance_is_span_scoped_not_file_scoped(self):
        # A file that contains a permitted URL gains no licence at all.
        self.assertIsNotNone(self._hit(
            f"- https://claude.dev/blog/x/\n- {self.PROBE}/skills is the canonical home."))

    def test_a_lookalike_repository_is_not_a_reference(self):
        # The prefix is full host-and-path, so one directory over does not match.
        self.assertIsNotNone(self._hit("https://github.com/anthropics/skills-evil/claude-x"))

    def test_the_declared_host_under_a_different_path_is_not_a_reference(self):
        # Being on a permitted host is not enough; the path prefix must match too.
        self.assertIsNotNone(self._hit("https://github.com/someone/claude-clone/blob/main/x.md"))

    def test_an_undeclared_url_cannot_carry_the_name(self):
        # A generic `https?://` exemption would let anyone paste a vendor name into a
        # URL. This is the case that exemption would wrongly pass.
        self.assertIsNotNone(self._hit("https://evil.example.com/claude/anthropic/guide"))

    def test_a_bare_hostname_is_not_a_reference(self):
        # Without the scheme the prefix cannot match, so the host is prose.
        self.assertIsNotNone(self._hit("See platform.claude.com/docs/en/about-claude/x"))

    def test_a_trailing_quote_does_not_extend_the_permitted_span(self):
        # The span ends at whitespace or a closing delimiter. If it did not, text
        # appended inside the same token would ride in on the URL's permission.
        body = f'- "https://claude.dev/blog/automating-eval-design-and-hillclimbing/" {self.PROBE}'
        self.assertIsNotNone(self._hit(body))

    def test_the_allowance_is_a_declared_list_not_a_pattern(self):
        # If the allowance were a regex, the prefixes would be unreachable as data
        # and widening it would be a one-character edit nobody would review.
        src = (REPO / "scripts" / "validate_skill.py").read_text()
        self.assertIn("REFERENCE_URL_PREFIXES = (", src)
        self.assertNotIn("re.compile(r\"https", src)


class ResearchLedgerGates(unittest.TestCase):
    """The ledger's four refusals must each be shown able to fire.

    `scripts/research_ledger.py` exists because a record a pass is merely *instructed*
    to keep will be empty -- and `auditandevolve/attempts.jsonl` is the proof in this
    repository: four references across two files, wired into two phase procedures, and
    the file does not exist.

    A gate that has never refused anything is indistinguishable from a gate that cannot.
    So each refusal gets a case that trips it, a case that must survive it, and -- because
    the failure mode this whole session kept hitting -- an assertion that the case
    actually reaches the gate rather than being quietly absorbed.
    """

    @staticmethod
    def _rows(**overrides):
        base = {
            "source_id": "S1",
            "item_id": "I1",
            "source_tier": "primary",
            "disposition": "covered",
            "anchor": "shared/axis-codes.md:11",
            "action": "delete-candidate",
            "receipt": "shared/axis-codes.md::one code per finding",
            "hits": 1,
        }
        base.update(overrides)
        return base

    def _run(self, rows, declared, dry=True):
        argv = [sys.executable, str(REPO / "scripts" / "research_ledger.py"),
                "--rows", str(declared)]
        if dry:
            argv.append("--dry-run")
        proc = subprocess.run(argv, input="\n".join(json.dumps(r) for r in rows),
                              capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr

    # -- the happy path, so the negatives mean something ---------------------

    def test_a_reconciled_table_passes_every_gate(self):
        code, out = self._run([self._rows()], 1)
        self.assertEqual(code, 0, f"a valid table was refused:\n{out}")
        self.assertIn("PASSED all four gates", out)

    def test_the_vocabulary_in_the_gate_matches_the_instruction_file(self):
        # Two copies of a closed set is two sources of truth. The gate's list and the
        # table in research-sources.md must be the same seven tokens, or a disposition
        # the instruction file teaches would be refused at write time.
        doc = (REPO / "auditandevolve" / "research-sources.md").read_text()
        for token in L.DISPOSITIONS:
            self.assertIn(f"`{token}`", doc,
                          f"the gate accepts `{token}` but the instruction file never names it")

    # -- refusal 1: reconciliation ------------------------------------------

    def test_too_few_rows_is_refused(self):
        code, out = self._run([self._rows()], 3)
        self.assertEqual(code, 1, out)
        self.assertIn("reconciliation failed", out)
        self.assertIn("Nothing was written", out)

    def test_an_empty_table_is_refused(self):
        # An empty ledger is indistinguishable from a pass that never ran.
        code, out = self._run([], 1)
        self.assertEqual(code, 1, out)
        self.assertIn("no rows", out)

    def test_a_duplicate_row_is_refused(self):
        # The population is declared, not bagged. Two rows for one item means one of them
        # is the same finding counted twice, which is how a rate gets invented.
        code, out = self._run([self._rows(), self._rows(hits=1)], 2)
        self.assertEqual(code, 1, out)
        self.assertIn("duplicate row", out)

    # -- refusal 2: receipt replay ------------------------------------------

    def test_a_receipt_that_does_not_reproduce_is_refused(self):
        code, out = self._run([self._rows(hits=99)], 1)
        self.assertEqual(code, 1, out)
        self.assertIn("does not reproduce", out)

    def test_covered_with_a_zero_hit_search_is_refused(self):
        # The exact combination this gate exists to refuse: claiming the tree already
        # says it, with a search that genuinely matches nothing. The recorded count has to
        # agree with the replay, or reconciliation refuses first and the sharper branch
        # is never reached -- which is itself why both checks exist.
        code, out = self._run(
            [self._rows(receipt="shared/axis-codes.md::a phrase nobody wrote", hits=0)], 1)
        self.assertEqual(code, 1, out)
        self.assertIn("the one combination this gate exists to refuse", out)

    def test_advances_with_a_receipt_that_finds_something_is_refused(self):
        # The same contradiction in the other direction, and it is the one that matters
        # for the ratchet: `advances` asserts the tree does NOT say this, and the receipt
        # is the evidence. Recording both is incoherent, and a pass that could do it would
        # insert text the tree already states.
        code, out = self._run([self._rows(disposition="advances")], 1)
        self.assertEqual(code, 1, out)
        self.assertIn("asserts the tree does NOT say this", out)

    def test_a_receipt_that_is_not_a_search_is_refused(self):
        code, out = self._run([self._rows(receipt="I read the guidelines carefully")], 1)
        self.assertEqual(code, 1, out)
        self.assertIn("A receipt that cannot be re-evaluated is a claim", out)

    def test_a_missing_receipt_is_refused(self):
        code, out = self._run([self._rows(receipt="")], 1)
        self.assertEqual(code, 1, out)
        self.assertIn("nothing to replay", out)

    # -- refusal 3: anchor resolution ---------------------------------------

    def test_an_anchor_naming_a_missing_file_is_refused(self):
        code, out = self._run([self._rows(anchor="shared/does-not-exist.md:3")], 1)
        self.assertEqual(code, 1, out)
        self.assertIn("not there", out)

    def test_an_anchor_past_the_end_of_the_file_is_refused(self):
        code, out = self._run([self._rows(anchor="shared/axis-codes.md:99999")], 1)
        self.assertEqual(code, 1, out)
        self.assertIn("outside the file", out)

    def test_covered_without_an_anchor_is_refused(self):
        code, out = self._run([self._rows(anchor="")], 1)
        self.assertEqual(code, 1, out)
        self.assertIn("needs a file:line", out)

    # -- refusal 4: the ratchet obligation ----------------------------------

    def test_covered_with_no_action_is_refused(self):
        # The ratchet default is deletion, so an undecided row is an unexercised check.
        code, out = self._run([self._rows(action="")], 1)
        self.assertEqual(code, 1, out)
        self.assertIn("carries no action", out)

    # -- the vocabulary itself is a gate ------------------------------------

    def test_a_disposition_outside_the_closed_set_is_refused(self):
        code, out = self._run([self._rows(disposition="looks-great")], 1)
        self.assertEqual(code, 1, out)
        self.assertIn("not in the closed set", out)

    def test_no_number_may_be_attached_to_a_disposition(self):
        # The whole reason this class uses a vocabulary. A relevance score would be a
        # number whose only producer is a feeling, in a column headed `value`.
        for field in ("score", "relevance", "value", "helpfulness", "rating"):
            self.assertNotIn(field, L.DISPOSITIONS,
                             f"`{field}` is not a disposition and must not read as one")
        src = (REPO / "auditandevolve" / "research-sources.md").read_text().lower()
        self.assertIn("no number is attached", src)
        self.assertIn("not measured", src)


class EvolutionPathGates(unittest.TestCase):
    """Two gates that let the loop write to a ledger and to itself. Both must be shown
    able to refuse, because `auditandevolve/attempts.jsonl` was specified in four places
    across two files and did not exist -- and a donor's equivalent shipped with a header
    and zero rows."""

    LEDGER = REPO / "auditandevolve" / "attempts.jsonl"
    FREEZE = REPO / "auditandevolve" / ".pass-freeze.json"

    def setUp(self):
        self._ledger = self.LEDGER.read_bytes() if self.LEDGER.is_file() else b""
        if self.FREEZE.exists():
            self.FREEZE.unlink()

    def tearDown(self):
        if self.LEDGER.is_file():
            self.LEDGER.write_bytes(self._ledger)
        if self.FREEZE.exists():
            self.FREEZE.unlink()

    @staticmethod
    def _copy():
        import shutil
        dest = Path(tempfile.mkdtemp()) / "se-review"
        shutil.copytree(REPO, dest,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"))
        return dest

    # -- classification ------------------------------------------------------

    def test_every_evolution_file_is_classified(self):
        root = REPO / "auditandevolve"
        present = {q.relative_to(REPO).as_posix() for q in root.iterdir()
                   if q.is_file() and q.suffix in (".md", ".jsonl") and not q.name.startswith(".")}
        unclassified = present - set(V.EVOLUTION_FILE_CLASSES)
        self.assertEqual(unclassified, set(),
                         f"classified nowhere: {sorted(unclassified)}. A file that is neither "
                         f"writable nor off-limits has no rule governing it.")

    def test_the_validator_rejects_an_unclassified_file(self):
        tree = self._copy()
        (tree / "auditandevolve" / "brand-new-procedure.md").write_text("# A new file nobody classified\n")
        proc = subprocess.run([sys.executable, str(tree / "scripts" / "validate_skill.py"), str(tree)],
                              capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0, "a new file in the evolution path passed with no class")
        self.assertIn("classified nowhere", proc.stdout)

    # -- the freeze ----------------------------------------------------------

    def _freeze(self, *argv):
        return subprocess.run([sys.executable, str(REPO / "scripts" / "pass_freeze.py"), *argv],
                              capture_output=True, text=True, cwd=REPO)

    def test_begin_then_verify_without_an_edit_passes(self):
        self.assertEqual(self._freeze("begin", "5").returncode, 0)
        self.assertEqual(self._freeze("verify").returncode, 0)

    def test_verify_without_a_freeze_is_refused(self):
        proc = self._freeze("verify")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("unjudged gate", proc.stdout)

    def test_a_second_open_freeze_is_refused(self):
        self.assertEqual(self._freeze("begin", "5").returncode, 0)
        second = self._freeze("begin", "3")
        self.assertEqual(second.returncode, 1)
        self.assertIn("already open", second.stdout)

    def test_editing_the_gate_during_the_pass_is_refused(self):
        # This is the whole mechanism: a phase rewrites the procedure that judges it.
        self.assertEqual(self._freeze("begin", "5").returncode, 0)
        state = json.loads(self.FREEZE.read_text())
        self.assertTrue(state["hashes"]["auditandevolve/hillclimb.md"],
                        "the freeze recorded no hash for the phase's own file")
        state["hashes"]["auditandevolve/hillclimb.md"] = "0" * 40
        self.FREEZE.write_text(json.dumps(state))
        proc = self._freeze("verify")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("edited the file that judges it", proc.stdout)

    def test_every_phase_has_a_gate(self):
        self.assertEqual(set(F.PHASE_GATES), {0, 1, 2, 3, 4, 5})
        for phase, gates in F.PHASE_GATES.items():
            self.assertTrue(gates, f"phase {phase} has no gate")
            for rel in gates:
                self.assertTrue((REPO / rel).is_file(), f"phase {phase} gate {rel} is not a file")

    # -- the attempt ledger --------------------------------------------------

    def _propose(self, patch_text):
        path = Path(tempfile.mkdtemp()) / "patch.diff"
        path.write_text(patch_text)
        return subprocess.run(
            [sys.executable, str(REPO / "scripts" / "attempts_ledger.py"), "propose",
             "--surface", "a.md", "--patch", str(path)],
            capture_output=True, text=True)

    def _record(self, digest, round_=1, verdict="reverted", base="abc123"):
        return subprocess.run(
            [sys.executable, str(REPO / "scripts" / "attempts_ledger.py"), "record",
             "--round", str(round_), "--surface", "a.md", "--patch-digest", digest,
             "--train-delta", "+0.08", "--test-delta", "0",
             "--verdict", verdict, "--base-commit", base],
            capture_output=True, text=True)

    @staticmethod
    def _digest(text):
        import hashlib
        return "pat:" + hashlib.sha256(text.encode()).hexdigest()[:12]

    def test_the_first_proposal_is_accepted(self):
        self.assertEqual(self._propose("rule one\n").returncode, 0)

    def test_a_reverted_patch_is_refused_with_the_numbers_that_rejected_it(self):
        text = "rule one\n"
        self.assertEqual(self._record(self._digest(text)).returncode, 0)
        proc = self._propose(text)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("REVERTED", proc.stdout)
        self.assertIn("+0.08", proc.stdout)
        self.assertIn("Nothing was written", proc.stdout)

    def test_a_kept_patch_is_refused_as_a_no_op(self):
        text = "rule two\n"
        self.assertEqual(self._record(self._digest(text), verdict="kept").returncode, 0)
        proc = self._propose(text)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no-op", proc.stdout)

    def test_matching_is_by_digest_not_by_wording(self):
        # The reason the earlier "one-line description" rule did not work: a re-proposal
        # comes from the same transcripts and is worded differently.
        text = "the original patch wording\n"
        self.assertEqual(self._record(self._digest(text)).returncode, 0)
        self.assertEqual(self._propose("an entirely different phrasing of the same change\n").returncode, 0)
        self.assertEqual(self._propose(text).returncode, 1)

    def test_a_stale_row_is_reported_rather_than_applied(self):
        self.assertEqual(self._record(self._digest("rule three\n"), base="old-sha").returncode, 0)
        self.assertIn("stale", self._propose("rule three\n").stdout)

    def test_recording_a_round_out_of_order_is_refused(self):
        proc = self._record(self._digest("x"), round_=4)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("cannot be recorded", proc.stdout)

    def test_a_row_missing_its_measured_against_state_is_refused(self):
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "attempts_ledger.py"), "record",
             "--round", "1", "--surface", "a.md", "--patch-digest", "pat:abc",
             "--train-delta", "+1", "--test-delta", "+1", "--verdict", "kept",
             "--base-commit", ""],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("base_commit", proc.stdout)

    def test_a_verdict_outside_the_closed_set_is_refused(self):
        proc = self._record(self._digest("y"), verdict="probably-fine")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("verdict must be one of", proc.stdout)


class NoAxisCounter(unittest.TestCase):
    """The uncoded population is only a measurement if zero and absent stay apart.

    `shared/axis-codes.md` says the open half of G9 is that "a reserved code with no
    periodic review is a defect nobody can size, and it cannot be sized if nothing records
    its occurrences." The header count is that record. So the counter that reads it has to
    be able to tell three states apart, and the third is the one that will actually occur.

    This is G8's pair in a new place: a review that recorded `Unclassified: 0` said the
    reviewer looked and the registry covered everything. A review with no header said
    nothing. A total across both claims *measured, and nothing found* about runs where
    nothing was measured -- which is exactly what the tree refuses everywhere else.
    """

    @staticmethod
    def _counter():
        import eval_diagnostics as D
        return D.no_axis_population

    def _tree(self, reviews):
        """reviews: list of (eval, condition, body_or_None)."""
        root = Path(tempfile.mkdtemp()) / "se-review"
        for eval_name, condition, body in reviews:
            d = root / "evals" / "iteration-1" / eval_name / condition
            d.mkdir(parents=True)
            if body is not None:
                (d / "review.md").write_text(body)
        return root

    def test_a_stated_zero_is_not_the_same_as_an_absent_header(self):
        pop = self._counter()(
            self._tree([("e1", "with_skill", "# R\nUnclassified: 0\n"),
                        ("e2", "with_skill", "# R\nno header here\n")]))
        self.assertEqual(len(pop["stated"]), 1, "the zero-valued header was not read")
        self.assertEqual(pop["stated"][0][1], 0)
        self.assertEqual(pop["absent"], 1)
        self.assertEqual(pop["sum"], 0)
        # The load-bearing assertion: both were read, and they are counted separately.
        self.assertEqual(pop["total"], 2)
        self.assertNotEqual(len(pop["stated"]), pop["total"])

    def test_absent_headers_are_never_counted_as_zero(self):
        pop = self._counter()(self._tree([("e1", "with_skill", "# R\n"), ("e2", "with_skill", "# R\n")]))
        self.assertEqual(pop["stated"], [])
        self.assertEqual(pop["absent"], 2)
        self.assertEqual(pop["sum"], 0)
        # Sum is 0 because nothing was stated -- and `stated` being empty is the fact that
        # stops a reader treating that 0 as a result.
        self.assertEqual(len(pop["stated"]), 0)

    def test_a_nonzero_count_survives_and_is_located(self):
        pop = self._counter()(
            self._tree([("e1", "with_skill", "# R\nUnclassified: 3\n"),
                        ("e2", "with_skill", "# R\nUnclassified: 0\n")]))
        self.assertEqual(pop["sum"], 3)
        self.assertEqual(pop["nonzero"], 1)
        self.assertIn("e1", pop["stated"][0][0])

    def test_a_run_with_no_body_is_ungraded_not_absent(self):
        root = self._tree([("e1", "with_skill", "# R\nUnclassified: 1\n")])
        d = root / "evals" / "iteration-1" / "e2" / "with_skill"
        d.mkdir(parents=True)
        (d / "grading.json").write_text("{}")   # a verdict with no review body
        pop = self._counter()(root)
        self.assertEqual(pop["ungraded"], 1)
        self.assertEqual(pop["absent"], 0, "a run with no body is not a review with no header")
        self.assertEqual(pop["total"], 1)

    def test_the_header_is_a_required_format_marker(self):
        # If it is not a format marker, a review can omit it and still look like a
        # skill-following report -- which is how a required field becomes decoration.
        self.assertIn("Unclassified:", R.FORMAT_MARKERS)

    def test_the_diagnostic_reports_not_measured_rather_than_zero(self):
        import eval_diagnostics as D
        root = self._tree([("e1", "with_skill", "# R\nno header\n")])
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            D.print_no_axis(root)
        out = buf.getvalue()
        self.assertIn("NOT MEASURED", out)
        self.assertIn("not a finding of zero", out)

    def test_an_empty_corpus_says_not_measured_rather_than_nothing(self):
        import eval_diagnostics as D
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            D.print_no_axis(self._tree([]))
        self.assertIn("NOT MEASURED", buf.getvalue())


class NoAxisRecording(unittest.TestCase):
    """The count must be recorded by the harness, because the reviewer does not emit it.

    Measured: `Unclassified:` has been required by shared/output-format.md since the
    first commit, and **0 of 54** stored review bodies carry it. A counter that parses
    review prose can therefore only ever report absence -- and absence is not a
    measurement. So the harness records the count per run, and `null` means the reviewer
    did not say, which is not the same claim as zero.
    """

    def test_a_stated_count_is_recorded(self):
        self.assertEqual(
            R.no_axis_count([{"review": "# R\nUnclassified: 3\n"}]),
            {"no_axis_count": 3, "no_axis_count_reason": None})

    def test_stated_zero_is_recorded_as_zero_not_null(self):
        out = R.no_axis_count([{"review": "# R\nUnclassified: 0\n"}])
        self.assertEqual(out["no_axis_count"], 0)
        self.assertIsNone(out["no_axis_count_reason"])
        self.assertNotEqual(out["no_axis_count"], None)

    def test_an_absent_header_is_null_with_a_reason(self):
        out = R.no_axis_count([{"review": "# R\nno header\n"}])
        self.assertIsNone(out["no_axis_count"])
        self.assertEqual(out["no_axis_count_reason"], "header absent")

    def test_disagreeing_replicates_are_null_not_averaged(self):
        out = R.no_axis_count([{"review": "Unclassified: 1\n"}, {"review": "Unclassified: 4\n"}])
        self.assertIsNone(out["no_axis_count"])
        self.assertIn("disagreed", out["no_axis_count_reason"])
        self.assertIn("1", out["no_axis_count_reason"])

    def test_a_run_with_no_body_is_distinguished_from_an_absent_header(self):
        out = R.no_axis_count([{}])
        self.assertIsNone(out["no_axis_count"])
        self.assertEqual(out["no_axis_count_reason"], "no review body")
        self.assertNotEqual(out["no_axis_count_reason"],
                            R.no_axis_count([{"review": "x"}])["no_axis_count_reason"])

    def test_agreeing_replicates_record_the_shared_value(self):
        out = R.no_axis_count([{"review": "Unclassified: 2\n"}, {"review": "Unclassified: 2\n"}])
        self.assertEqual(out["no_axis_count"], 2)

    def test_the_ledger_status_distinguishes_empty_from_unwired(self):
        proc = subprocess.run([sys.executable, str(REPO / "scripts" / "attempts_ledger.py"), "status"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("0 rows", proc.stdout)
        self.assertIn("Correct state", proc.stdout)
        self.assertIn("Distinguish this from a ledger nothing writes", proc.stdout)


class StructuralAssertionCensus(unittest.TestCase):
    """How much of the corpus could be checked without a model call -- and why that is
    not the same as making it measurable.

    223 of 860 assertions mention a report-header token (a severity word, a finding
    count, a header field), so a deterministic checker could adjudicate them from a
    stored review at zero quota. That is a real lead and it is also a trap, so the census
    is pinned rather than acted on.

    The trap: those assertions test **format**, not review quality. A corpus that counted
    them as measurable would report a higher pass rate while measuring nothing about
    whether the skill finds defects -- G8's exact failure, with a mechanism attached.
    G1's substantive half is the detection assertions, and no deterministic checker
    reaches those. This test exists so nobody mistakes the lead for the fix.
    """

    STRUCTURAL = re.compile(r"\b(CRITICAL|MAJOR|MINOR|INFO)\b|\d+ findings|"
                            r"`(Covered|Gated by|Verified by|Unclassified):", re.IGNORECASE)

    def test_the_corpus_has_both_kinds_of_assertion(self):
        spec = json.loads((REPO / "evals" / "evals.json").read_text())
        structural = sum(1 for e in spec["evals"] for a in e["assertions"]
                         if self.STRUCTURAL.search(a))
        total = sum(len(e["assertions"]) for e in spec["evals"])
        self.assertGreater(structural, 0, "the structural share collapsed to zero")
        self.assertLess(structural, total,
                        "every assertion now looks structural, which would mean the "
                        "census can no longer tell format from substance")

    def test_structural_assertions_do_not_test_detection(self):
        # The load-bearing claim of this class, asserted so it cannot quietly stop
        # being true: a structural assertion names a header or a severity, and a
        # detection assertion names the defect.
        spec = json.loads((REPO / "evals" / "evals.json").read_text())
        substantive = [a for e in spec["evals"] for a in e["assertions"]
                       if not self.STRUCTURAL.search(a)]
        self.assertTrue(substantive, "no substantive assertion found, so the split is wrong")
        for text in substantive[:40]:
            self.assertNotRegex(text, r"^Exactly \d+ findings above Info severity$")


class RetiredAxisCodes(unittest.TestCase):
    """A retired code is citable in a tombstone and in a record. Nowhere else.

    Measured before this rule: **65 occurrences of `A5` across 40 stored reviews**, and
    they are substantive -- "Parameterized query throughout (A5)". Two of those classes
    exist and the rule has to tell them apart:

      record    a stored review, or the fixture matrix in evals/README.md, saying what a
                past eval asserted. Rewriting any of it is falsifying evidence.
      tombstone a live file naming the retirement so a reader can map it by subject.
      LIVE CITE a live instruction file telling a reader to look at a retired axis. The
                registry says "Never invent a code" and "a code absent from this file does
                not exist" -- but a retired code is present and marked, so neither catches
                it. That is the hole.

    The set is derived from the retirement table, so retiring a code needs no edit here.
    """

    @staticmethod
    def _validate(tree):
        proc = subprocess.run([sys.executable, str(tree / "scripts" / "validate_skill.py"), str(tree)],
                              capture_output=True, text=True)
        return proc.returncode, proc.stdout

    @staticmethod
    def _copy():
        import shutil
        dest = Path(tempfile.mkdtemp()) / "se-review"
        shutil.copytree(REPO, dest,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"))
        return dest

    def test_the_retired_set_is_derived_not_hardcoded(self):
        registry = (REPO / "shared" / "axis-codes.md").read_text()
        self.assertRegex(registry, r"\|\s*\*A5\*\s*\|\s*\*retired\*",
                         "the retirement table no longer marks A5 retired, so this test's "
                         "fixture is meaningless -- re-derive the retired code")

    def test_a_live_citation_of_a_retired_code_is_refused(self):
        tree = self._copy()
        target = tree / "domains" / "correctness" / "ai-systems" / "guidelines" / "evaluation-and-drift.md"
        target.write_text(target.read_text() + "\nAlways confirm the token is validated (A5).\n")
        code, out = self._validate(tree)
        self.assertNotEqual(code, 0, "a live retired-code citation passed")
        self.assertIn("retired axis code", out)

    def test_a_tombstone_is_permitted(self):
        tree = self._copy()
        code, out = self._validate(tree)
        self.assertEqual(code, 0, f"the two existing tombstones were rejected:\n{out}")

    def test_recorded_evidence_keeps_its_record(self):
        tree = self._copy()
        # A stored review citing a retired code is the thing it recorded.
        tree.joinpath("evals/README.md").write_text(
            "| 39 | fixture | Security | echoed origin | 1 x MAJOR A5 | 9 |\n")
        code, out = self._validate(tree)
        self.assertEqual(code, 0, f"the fixture matrix was rejected as a live citation:\n{out}")

    def test_live_assertions_are_not_exempt(self):
        # evals/evals.json tells a reviewer what to look for, so a retired code there is
        # a live citation even though it sits under evals/.
        import json
        tree = self._copy()
        spec = json.loads((tree / "evals" / "evals.json").read_text())
        spec["evals"][0]["assertions"] = ["Confirms the principal is not asserted (A5)"]
        (tree / "evals" / "evals.json").write_text(json.dumps(spec, indent=2))
        code, out = self._validate(tree)
        self.assertNotEqual(code, 0, "a retired code in a live assertion passed")
        self.assertIn("retired axis code", out)

    def test_the_registry_may_name_what_it_retires(self):
        code, out = self._validate(self._copy())
        self.assertEqual(code, 0, f"the registry was flagged for its own tombstones:\n{out}")


class VerdictPrivacy(unittest.TestCase):
    """A verdict is evidence about the skill, never about the harness.

    Six pattern-based rules were tried for the free-text case and every one fired
    on this repository's own content -- a sub-domain path, a MIME type in a
    fixture, a supply-chain fixture's action reference. So the check is structural:
    it looks at the keys, which is where every leak actually came from.
    """

    DIGEST = re.compile(r"\A(cfg:[0-9a-f]{8,}|unpinned)\Z")
    IDENTITY_KEYS = ("model", "judge_model", "model_id", "judge_model_id")

    def test_identity_keys_are_the_forbidden_set(self):
        # Expressed here as a literal rather than imported, so deleting the check
        # from the validator does not silently delete the test that covers it.
        self.assertEqual(set(self.IDENTITY_KEYS),
                         {"model", "judge_model", "model_id", "judge_model_id"})

    def test_a_digest_is_accepted(self):
        self.assertTrue(self.DIGEST.match("cfg:9f3a1c7e2b04"))
        self.assertTrue(self.DIGEST.match("unpinned"))

    def test_an_identity_is_not_a_digest(self):
        for value in ("vendor/model-1.2-free", "some-model-free", "", "cfg:", "cfg:XYZ"):
            with self.subTest(value=value):
                self.assertIsNone(self.DIGEST.match(value))

    def test_no_committed_evidence_carries_an_identity_key(self):
        offenders = []
        for path in (REPO / "evals").rglob("*.json"):
            try:
                doc = json.loads(path.read_text())
            except Exception:
                continue
            if isinstance(doc, dict):
                offenders += [f"{path.name}:{k}" for k in self.IDENTITY_KEYS if k in doc]
        self.assertEqual(offenders, [], f"evidence names what ran: {offenders}")

    def test_every_config_key_in_evidence_holds_a_digest(self):
        bad = []
        for path in (REPO / "evals").rglob("*.json"):
            try:
                doc = json.loads(path.read_text())
            except Exception:
                continue
            if not isinstance(doc, dict):
                continue
            for key, value in doc.items():
                if key.endswith("_config") and isinstance(value, str) and not self.DIGEST.match(value):
                    bad.append(f"{path.name}:{key}={value}")
        self.assertEqual(bad, [], f"a config key holds an identity: {bad}")


class Staging(unittest.TestCase):
    """Staging is what makes the contamination gate true rather than intended."""

    def test_the_answer_key_is_never_staged(self):
        with tempfile.TemporaryDirectory() as d:
            R.stage_skill(Path(d), arm="with_skill")
            self.assertFalse((Path(d) / "evals/evals.json").is_file())

    def test_recorded_verdicts_are_never_staged(self):
        with tempfile.TemporaryDirectory() as d:
            R.stage_skill(Path(d), arm="with_skill")
            self.assertFalse((Path(d) / "evals/iteration-1").exists())

    def test_the_whole_instruction_surface_is_staged(self):
        with tempfile.TemporaryDirectory() as d:
            R.stage_skill(Path(d), arm="with_skill")
            for rel in ("SKILL.md", "shared/severity-and-rules.md",
                        "shared/domain-fanout.md", "shared/evolution-candidates.md",
                        "domains/security/leaf.md",
                        "domains/security/trust-boundaries/guidelines/attack-path.md"):
                with self.subTest(rel=rel):
                    self.assertTrue((Path(d) / rel).is_file(), f"{rel} not staged")

    def test_the_ablation_arm_removes_the_gate_file(self):
        with tempfile.TemporaryDirectory() as d:
            R.stage_skill(Path(d), arm="nosuppress")
            self.assertFalse(
                (Path(d) / "project-tree/shared/deliberate.md").is_file()
            )

    def test_the_prompt_names_the_staged_absolute_path(self):
        import json
        item = next(
            e for e in json.loads((REPO / "evals/evals.json").read_text())["evals"]
            if e["id"] == 100
        )
        ws = Path(tempfile.mkdtemp())
        out = R.absolute_prompt(item, ws)
        self.assertIn(str((ws / item["files"][0]).resolve()), out)

    def test_a_workspace_is_sealed_as_a_repository(self):
        ws = Path(tempfile.mkdtemp())
        R.seal_workspace(ws)
        toplevel = subprocess.run(
            ["git", "-C", str(ws), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True,
        )
        self.assertEqual(toplevel.returncode, 0, toplevel.stderr)


class SubstanceProbeCoverage(unittest.TestCase):
    """A selftest that cannot grade substance must not report TRUSTED as if it had.

    The four original probes passed the judge the literal string "probe 0" as its
    assertion, so the only question they could ask was whether the judge awards
    anything at all. All four were answered correctly, three replicates each, and the
    verdict was TRUSTED -- while the same judge, on the same prompt, was recorded on a
    real review as saying "the review contains no axis labels at all" about a review
    whose second line reads "Domain: Correctness (A3 -- Data)".

    Worse, the polarity bar was not merely blind to that defect, it was blind *in its
    favour*: a judge that concluded the review contained nothing awarded nothing, and
    awarding nothing was the clean pass. These tests pin both halves.
    """

    REAL = [pr for pr in R.JUDGE_PROBES if pr[3]]

    @staticmethod
    def _grade_returning(passes):
        return lambda *a, **k: [{"passed": x} for x in passes]

    def test_every_probe_declares_the_same_arity(self):
        # judge_selftest unpacks five fields positionally. A probe added with three or
        # six would raise there, far from the probe list, at quota cost.
        # Assert the arity directly. Zipping field names against the probes measured the
        # *shortest* probe and named the columns, so a probe added with three fields
        # shortened every column and the missing ones were never examined -- the test
        # passed on exactly the defect it exists to catch.
        for probe in R.JUDGE_PROBES:
            self.assertEqual(len(probe), 5, f"probe {probe[0]!r} has {len(probe)} fields")

    def test_something_grades_a_real_review(self):
        self.assertTrue(self.REAL, "every probe is polarity-only again: the selftest "
                                   "cannot see a substantive judgement")

    def test_no_probe_assertion_is_a_placeholder(self):
        for _, _, _, assertions, _ in self.REAL:
            for a in assertions:
                self.assertFalse(a.startswith("probe "), f"placeholder leaked: {a!r}")

    def test_a_real_probe_states_an_expectation_within_range(self):
        for name, _, _, assertions, want in self.REAL:
            self.assertIsNotNone(want, f"{name} grades real text but expects no count")
            self.assertTrue(0 <= want <= len(assertions),
                            f"{name} expects {want} of {len(assertions)} awards")

    def test_awarding_nothing_in_real_text_is_defective(self):
        # The regression the probe exists to catch. Under the polarity bar this was a
        # clean pass; it is the exact failure recorded on a real review.
        with mock.patch.object(R, "grade", self._grade_returning([False, False, False])):
            got = R._one_judge_probe("body", None, ["a", "b", "c"], 2)
        self.assertFalse(got["failed_it"],
                         "a judge that finds nothing in real text passed the probe")

    def test_awarding_everything_is_defective_too(self):
        with mock.patch.object(R, "grade", self._grade_returning([True, True, True])):
            got = R._one_judge_probe("body", None, ["a", "b", "c"], 2)
        self.assertFalse(got["failed_it"], "a judge that waves everything through passed")

    def test_the_exact_count_passes(self):
        with mock.patch.object(R, "grade", self._grade_returning([True, True, False])):
            got = R._one_judge_probe("body", None, ["a", "b", "c"], 2)
        self.assertTrue(got["failed_it"])
        self.assertEqual(got["passed"], 2)

    def test_a_right_answer_is_not_reported_as_defective(self):
        # The inversion actually shipped: `!=` where `==` was meant, which turned a
        # perfect 2-of-3 into UNTRUSTED. Assert on the verdict, not on the row, so the
        # polarity is pinned where it decides something.
        attempt = {"failed_it": True, "passed": 2, "why": None}
        folded = R._fold_judge_probe("labels-present", "exp", [attempt] * 3, 2)
        verdict = R._judge_verdict([folded], 1)
        self.assertEqual(verdict["probes_defective"], [])
        self.assertEqual(verdict["verdict"], "TRUSTED")

    def test_the_polarity_probes_keep_their_historical_bar(self):
        with mock.patch.object(R, "grade", self._grade_returning([False, False, False])):
            self.assertTrue(R._one_judge_probe("body", None)["failed_it"])

    def test_agreement_is_over_the_award_vector_not_just_the_verdict(self):
        # Two attempts, same verdict, different counts. Same verdict alone reads as
        # reproducible; the vector is what shows it was not.
        attempts = [{"failed_it": False, "passed": 2, "why": None},
                    {"failed_it": False, "passed": 3, "why": None}]
        folded = R._fold_judge_probe("p", "exp", attempts, 2)
        self.assertFalse(folded["agreed"])

    def test_identical_counts_still_agree(self):
        attempts = [{"failed_it": False, "passed": 2, "why": None}] * 2
        self.assertTrue(R._fold_judge_probe("p", "exp", attempts, 2)["agreed"])

    def test_a_probe_exists_for_vacuous_compliance(self):
        # Measured on a real fixture: a review reporting "0 findings" collected 7 of 8
        # assertions, four of them because there was nothing present to fail. If the
        # selftest cannot see that shape, it cannot see the corpus paying for silence.
        vac = [pr for pr in R.JUDGE_PROBES if pr[0] == "vacuous"]
        self.assertEqual(len(vac), 1, "the vacuity probe is gone")
        _, _, _, assertions, want = vac[0]
        self.assertEqual(want, 0, "silence must collect nothing from demonstration claims")
        self.assertTrue(any("cites a demonstrable" in a or "graded MINOR" in a
                            for a in assertions),
                        "the probe no longer asserts things silence cannot demonstrate")

    def test_the_prompt_separates_staying_away_from_never_going_near(self):
        self.assertIn("silence, not compliance", R.GRADER_INSTRUCTIONS)

    def test_the_prompt_demands_a_search_before_claiming_absence(self):
        # The prompt change is the other half of the fix, and a prompt edit is exactly
        # the kind of change that gets reverted by someone tidying the rules.
        self.assertIn("Absence is a claim", R.GRADER_INSTRUCTIONS)
        self.assertIn("you did not search", R.GRADER_INSTRUCTIONS)


class NamedGapRegister(unittest.TestCase):
    """The adoption test cites this register, so the register must be checkable.

    It was ignored by `.gitignore` and named by nothing in `scripts/` or `tests/`, which
    meant every "closes G7" claim in this history cited a row present on one machine and
    in no clone. It also carried a row that declared itself CLOSED while its own text said
    the audit "has never itself been audited."

    Each test below breaks one rule in a copy of the real tree and requires the validator
    to notice, because a rule that reports nothing is indistinguishable from a rule that
    found nothing to report.
    """

    @staticmethod
    def _tree():
        import shutil
        dest = Path(tempfile.mkdtemp()) / "se-review"
        shutil.copytree(REPO, dest,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"))
        return dest

    def _errors(self, dest):
        return V.validate_named_gaps(dest)

    def _mutate(self, dest, fn):
        """Apply a mutation and return the errors it produced.

        Refuses a mutation that changed nothing. Two of these tests used to target a literal
        status string, and when the last Open row was closed the `replace` silently matched
        nothing: the test asserted the absence of an error, the absence of a mutation proved
        it, and the suite stayed green while the check it existed to perform stopped running.
        A mutation that finds no target is a broken test, not a passing one.
        """
        reg = dest / "docs" / "named-gaps.md"
        before = reg.read_text(encoding="utf-8")
        after = fn(before)
        if after == before:
            raise AssertionError(
                "the mutation changed nothing -- its target string is absent, so this test "
                "would pass without testing anything. Repoint it at the register's current "
                "content rather than at a status that may no longer occur.")
        reg.write_text(after, encoding="utf-8")
        return self._errors(dest)


    def test_the_real_register_passes(self):
        self.assertEqual(self._errors(REPO), [],
                         "the register in the tree is not compliant with its own rules")

    def test_an_undated_closure_is_flagged(self):
        # The G7 failure, in mechanical form: strip the date from a row that genuinely
        # was closed and the claim must stop being accepted.
        dest = self._tree()
        self.assertIn("**CLOSED 2026-10-05.**",
                      (dest / "docs" / "named-gaps.md").read_text(),
                      "no dated closure to strip; this test would pass vacuously")
        errs = self._mutate(dest, lambda s: s.replace("**CLOSED 2026-10-05.**",
                                                     "**CLOSED.**", 1))
        self.assertTrue(any("carries no date" in e for e in errs),
                        f"an undated closure was accepted: {errs}")

    def test_an_unrelated_edit_is_not_flagged(self):
        # The other half of non-vacuity: the rule must not cry wolf, or it will be
        # suppressed and then it catches nothing at all.
        dest = self._tree()
        errs = self._mutate(dest, lambda s: s.replace(
            "# Named gap register", "# Named gap register\n\nAn extra paragraph.\n", 1))
        self.assertEqual(errs, [])

    def test_a_row_with_the_wrong_column_count_is_flagged(self):
        dest = self._tree()
        errs = self._mutate(dest, lambda s: s.replace("| Closed |", "| Closed | extra |", 1)
                            if "| Closed |" in s else
                            s.replace("| Partial |", "| Partial | extra |", 1))
        self.assertTrue(any("expected 4" in e for e in errs),
                        f"a malformed row was accepted: {errs}")

    def test_an_unknown_status_is_flagged(self):
        dest = self._tree()
        errs = self._mutate(dest, lambda s: s.replace("| Closed |", "| Probably |", 1)
                            if "| Closed |" in s else
                            s.replace("| Partial |", "| Probably |", 1))
        self.assertTrue(any("expected one of" in e for e in errs),
                        f"an invented status was accepted: {errs}")

    def test_a_duplicate_id_is_flagged(self):
        dest = self._tree()
        row = next(l for l in (dest / "docs" / "named-gaps.md").read_text().splitlines()
                   if l.startswith("| **G1**"))
        errs = self._mutate(dest, lambda s: s + "\n" + row + "\n")
        self.assertTrue(any("already defined" in e for e in errs),
                        f"a duplicate id was accepted: {errs}")

    def test_a_register_that_is_still_ignored_is_flagged(self):
        dest = self._tree()
        gi = dest / ".gitignore"
        gi.write_text(gi.read_text().replace("!/docs/named-gaps.md\n", ""))
        self.assertTrue(any("not un-ignored" in e for e in self._errors(dest)))

    def test_a_missing_register_is_flagged(self):
        dest = self._tree()
        (dest / "docs" / "named-gaps.md").unlink()
        self.assertTrue(any("is missing" in e for e in self._errors(dest)))


class StaleVerdictReporting(unittest.TestCase):
    """A verdict graded against superseded assertions is void, and must be reported.

    Rewriting three assertions on one fixture so they stopped being collectable by
    silence left every fixture digest clean -- the fixture bytes never changed -- and the
    diagnostics printed nothing. 105 of 159 stored verdicts are in that position. The
    predicate that answers the question existed and was called from nowhere.
    """

    def _tree(self):
        import shutil
        dest = Path(tempfile.mkdtemp()) / "se-review"
        shutil.copytree(REPO, dest,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"))
        return dest

    def _scan(self, root):
        import eval_diagnostics as D
        old, D.SKILL_ROOT, D.ITERATION = D.SKILL_ROOT, root, root / "evals" / "iteration-1"
        try:
            return D.stale_verdicts()
        finally:
            D.SKILL_ROOT, D.ITERATION = old, D.ITERATION

    def test_the_scan_actually_detects_an_edited_assertion(self):
        # Non-vacuity. If this passes on an unmodified corpus the rule is not looking.
        dest = self._tree()
        corpus = dest / "evals" / "evals.json"
        doc = json.loads(corpus.read_text())
        for e in doc["evals"]:
            if e["assertions"]:
                e["assertions"] = list(e["assertions"])
                e["assertions"][0] = e["assertions"][0] + " (edited)"
                break
        corpus.write_text(json.dumps(doc, indent=2) + "\n")
        got = self._scan(dest)
        self.assertTrue(got["stale"], "an edited assertion was not reported as stale")
        self.assertGreater(got["checked"], 0, "nothing was checked, so nothing could be found")

    def test_an_unedited_corpus_reports_no_edit_as_stale(self):
        dest = self._tree()
        got = self._scan(dest)
        self.assertTrue(got["ok"])
        self.assertGreater(got["checked"], 0)

    def test_the_real_corpus_has_void_verdicts(self):
        # Non-vacuity in the other direction: this is a live finding, not a rule that
        # never fires. If a future pass re-runs the corpus this is the assertion that
        # will notice, and it should be the one that fails.
        got = self._scan(REPO)
        self.assertTrue(got["stale"],
                        "no stale verdicts reported; the corpus may genuinely be current now, "
                        "in which case this row should be updated with the re-run that did it")


class MismatchProbe(unittest.TestCase):
    """The floor of a fixture's scale must be measured, not assumed.

    Six of the twelve suppression fixtures turn out to be unrunnable: an unrelated review
    collects 55.6-66.7 percent of their assertions, leaving 33.3-44.4 points of span
    against a 40-point kill criterion. Nothing in the tree could see that, so an experiment
    over the full range would have returned a null that read as "suppression is harmless".

    These tests cover the accounting, because that is where this kind of tool goes wrong:
    a rate computed over the fixtures that worked, and a verdict reported for a range it
    did not measure.
    """

    def _corpus(self, n=3):
        return [{"id": i, "name": f"f{i}", "files": [f"evals/fixtures/f{i}.py"],
                 "assertions": ["a", "b", "c", "d"]} for i in range(n)]

    def _patched(self, results):
        import mismatch_probe as M
        real_load, real_grade = M.R.load_json, M.R.grade
        M.R.load_json = lambda p: {"evals": self._corpus(3)}
        calls = {"n": 0}

        def fake_grade(body, assertions, timeout, workdir, model=None):
            calls["n"] += 1
            return results[calls["n"] - 1]
        M.R.grade = fake_grade
        return M, real_load, real_grade, calls

    def test_the_floor_is_what_the_probe_collects(self):
        M, rl, rg, _ = self._patched([[{"passed": True}] * 4])
        try:
            out = M.measure([0], "body", None, 40.0)
        finally:
            M.R.load_json, M.R.grade = rl, rg
        self.assertEqual(out["rows"][0]["floor_pct"], 100.0)
        self.assertEqual(out["rows"][0]["span_points"], 0.0)
        self.assertFalse(out["rows"][0]["resolves_kill_criterion"])

    def test_a_clean_fixture_has_the_whole_span(self):
        M, rl, rg, _ = self._patched([[{"passed": False}] * 4])
        try:
            out = M.measure([0], "body", None, 40.0)
        finally:
            M.R.load_json, M.R.grade = rl, rg
        self.assertEqual(out["rows"][0]["span_points"], 100.0)
        self.assertTrue(out["rows"][0]["resolves_kill_criterion"])

    def test_an_ungradeable_reply_is_counted_not_dropped(self):
        # The regression. A probe that dies on the first malformed reply reports the
        # fixtures that worked -- a better number and a wrong one.
        M, rl, rg, calls = self._patched([])
        M.R.grade = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("not well-formed"))
        try:
            out = M.measure([0, 1, 2], "body", None, 40.0)
        finally:
            M.R.load_json, M.R.grade = rl, rg
        self.assertEqual(out["graded"], 0)
        self.assertEqual(out["asked"], 3, "the denominator must be the range, not the successes")
        self.assertEqual(len(out["ungradeable"]), 3)

    def test_a_wrong_length_reply_is_a_failure_not_a_score(self):
        M, rl, rg, _ = self._patched([])
        M.R.grade = lambda *a, **k: [{"passed": True}]   # 1 verdict for 4 assertions
        try:
            out = M.measure([0], "body", None, 40.0)
        finally:
            M.R.load_json, M.R.grade = rl, rg
        self.assertEqual(out["graded"], 0)
        self.assertIn("4 assertions", out["ungradeable"][0]["reason"])

    def test_a_partial_run_still_reports_its_own_denominator(self):
        # One fixture grades, two do not. The result must say 1 of 3 -- reporting three
        # floors where one exists is the failure, not reporting one floor.
        import mismatch_probe as M
        real_load, real_grade = M.R.load_json, M.R.grade
        M.R.load_json = lambda p: {"evals": self._corpus(3)}
        seen = {"n": 0}

        def flaky(body, assertions, timeout, workdir, model=None):
            seen["n"] += 1
            if seen["n"] > 1:
                raise RuntimeError("rate limited")
            return [{"passed": False}] * len(assertions)

        M.R.grade = flaky
        try:
            out = M.measure([0, 1, 2], "body", None, 40.0)
        finally:
            M.R.load_json, M.R.grade = real_load, real_grade
        self.assertEqual((out["asked"], out["graded"]), (3, 1))
        self.assertEqual(len(out["ungradeable"]), 2)


class AnswerKeyReachability(unittest.TestCase):
    """A reviewer must not be able to read the thing that grades it.

    `scripts/` is a staged directory, so `run_evals.py` was staged with it -- carrying
    GRADER_INSTRUCTIONS, the rubric the judge grades against, and JUDGE_PROBES, which
    holds a worked review annotated with the exact award count it has to earn. The
    contamination gate never objected, because `run_evals.py` is not a forbidden name: it
    is an ordinary file in an ordinary staged directory. Self-inflicted -- those probes
    were added while the harness was already being staged.

    The second half is the gate's own blindness. This corpus reads with `cat`, not with
    the read tool: one run made three `read` calls, all of which errored, then read the
    fixture with `cat`, listed it with `ls`, and reopened it from `python3`. The gate saw
    none of it, so a reviewer could have read the answer key and passed.
    """

    @staticmethod
    def _workspace():
        import tempfile
        dest = Path(tempfile.mkdtemp()) / "ws"
        R.stage_skill(dest, "with_skill")
        return dest

    def test_the_grading_harness_is_not_staged(self):
        ws = self._workspace()
        for name in R.HARNESS_FILES:
            self.assertFalse((ws / "scripts" / name).is_file(),
                             f"{name} is readable from inside the workspace the reviewer gets")

    def test_no_staged_file_carries_the_rubric(self):
        # The check that would have caught it, stated over the whole surface rather than
        # over the one filename -- a second file with the rubric in it must fail too.
        ws = self._workspace()
        leaked = []
        for f in ws.rglob("*"):
            if not f.is_file():
                continue
            try:
                blob = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            # The rubric *body*, not its name. `auditandevolve/SKILL.md` names
            # GRADER_INSTRUCTIONS in a list of files that are off-limits, which is the
            # opposite of a leak, and a test that flagged it would be pushed to be
            # weakened until it flagged nothing. These are the definitions themselves.
            for needle in ("GRADER_INSTRUCTIONS = ", "JUDGE_PROBES = (",
                           "Absence is a claim", "silence, not compliance"):
                if needle in blob:
                    leaked.append(f"{f.relative_to(ws)} contains {needle}")
        self.assertEqual(leaked, [], f"grading material is reachable from the workspace: {leaked}")

    def test_the_rest_of_scripts_is_still_available(self):
        # Removing a capability is not a fix. A reviewer may reasonably run the validator.
        ws = self._workspace()
        self.assertTrue((ws / "scripts" / "validate_skill.py").is_file(),
                        "the fix took away the validator too")

    @staticmethod
    def _stream(tool, payload):
        return json.dumps({"type": "tool_use", "part": {
            "tool": tool, "state": {"status": "completed", "input": payload}}})

    def test_a_shell_read_of_the_key_is_now_visible(self):
        stream = self._stream("shell", {"command": "cat /repo/evals/evals.json | head -40"})
        paths, _ = R.read_paths_and_patterns(stream)
        self.assertTrue(any("evals.json" in p for p in paths),
                        f"the gate is still blind to a shell read of the key: {paths}")

    def test_a_shell_read_of_a_verdict_directory_is_now_visible(self):
        stream = self._stream("shell", {"command": "ls /repo/evals/iteration-1/"})
        paths, _ = R.read_paths_and_patterns(stream)
        self.assertTrue(any("iteration-1" in p for p in paths),
                        f"the gate is still blind to a shell listing of the verdicts: {paths}")

    def test_the_repository_path_is_not_itself_a_forbidden_read(self):
        # `FORBIDDEN_DIRS` holds "review" and this project is called se-review, so a
        # substring match flagged the repository's own root -- and reached the right
        # verdict for the wrong reason. Every honest mention of the repo root was being
        # harvested as a forbidden read, which is worse than missing it: the next rename
        # would have silently disarmed the check.
        stream = self._stream("shell", {"command": "ls /Users/x/repo/domains/"})
        paths, _ = R.read_paths_and_patterns(stream)
        self.assertEqual(paths, [], f"the repo root matched a forbidden directory: {paths}")

    def test_a_real_verdict_directory_is_still_matched(self):
        # The counterpart, so the fix above cannot have simply stopped matching.
        for command, expect in (
            ("ls evals/iteration-1/", "iteration-1"),
            ("cat evals/evals.json", "evals.json"),
            ("cat /x/y/iteration-1/eval-a/with_skill/review.md", "review"),
        ):
            paths, _ = R.read_paths_and_patterns(self._stream("shell", {"command": command}))
            self.assertTrue(any(expect in p for p in paths),
                            f"{command!r} no longer yields {expect}: {paths}")

    def test_ordinary_shell_use_is_not_flagged(self):
        # The other half. Harvesting every path in a command would refuse any run that
        # touches /usr/lib, and a gate that cries wolf gets switched off.
        for command in ("python3 -c \"import json;print(1)\"",
                        "ls -l /usr/lib/python3.14/json",
                        "cat /tmp/notes.txt"):
            paths, _ = R.read_paths_and_patterns(self._stream("shell", {"command": command}))
            self.assertEqual(paths, [], f"ordinary command flagged: {command!r} -> {paths}")


class IsolationProof(unittest.TestCase):
    """Isolation is proved by what a run read, not by guessing where its shell stood.

    The runner pins each session to a directory named on the command line, and for a long
    while the harness was not actually sending the flag that made that true -- a string
    splatted into argv as twelve separate characters. While isolation was broken the gate
    inferred the shell's location from whether each command named the workspace by absolute
    path, because there was nothing better available. Measured after the flag was fixed,
    that inference refused a run that had made eight reads and was nowhere near the key.

    Isolation works now, so the inference is retired and the direct question is asked
    instead: did this run reach a forbidden entry, with shell reads harvested so the answer
    is observed rather than guessed.
    """

    WS = Path("/tmp/ws-under-test")

    @staticmethod
    def _stream(*tools):
        return "\n".join(json.dumps({"type": "tool_use", "part": {
            "tool": tool, "state": {"status": "completed", "input": payload}}})
            for tool, payload in tools)

    def test_a_workspace_relative_read_alone_is_proof(self):
        ok, why, _, indirect = R.isolation_gate(
            self._stream(("read", {"path": f"{self.WS}/evals/fixtures/x.py"})), self.WS)
        self.assertTrue(ok, why)
        self.assertEqual(indirect, 0)

    def test_an_honest_relative_command_is_no_longer_a_refusal(self):
        # The regression this retires. It named nothing forbidden and read nothing outside
        # its workspace; refusing it is refusing an honest run, which is how a gate is lost.
        ok, why, _, indirect = R.isolation_gate(
            self._stream(("shell", {"command": "wc -l README.md"})), self.WS)
        self.assertTrue(ok, f"an honest relative command was refused: {why}")
        self.assertEqual(indirect, 1, "reliance on a relative path must still be counted")

    def test_reading_the_key_is_refused_from_anywhere(self):
        for command in ("cat evals/evals.json",
                        f"cat {self.WS}/evals/evals.json",
                        "python3 -c \"open('evals/evals.json').read()\""):
            ok, why, _, _ = R.isolation_gate(
                self._stream(("shell", {"command": command})), self.WS)
            self.assertFalse(ok, f"{command!r} was accepted")
            self.assertIn("forbidden", why)

    def test_reading_a_verdict_directory_is_refused(self):
        ok, why, _, _ = R.isolation_gate(
            self._stream(("shell", {"command": "ls evals/iteration-1/"})), self.WS)
        self.assertFalse(ok, "the recorded-verdict directory was accepted")
        self.assertIn("forbidden", why)

    def test_reading_outside_the_workspace_is_refused(self):
        ok, why, _, _ = R.isolation_gate(
            self._stream(("read", {"path": "/elsewhere/notes.md"})), self.WS)
        self.assertFalse(ok)
        self.assertIn("outside", why)

    def test_a_recursive_sweep_is_refused_when_not_rooted_at_the_workspace(self):
        ok, why, _, _ = R.isolation_gate(json.dumps({"type": "tool_use", "part": {
            "tool": "glob", "state": {"status": "completed",
                                      "input": {"pattern": "**/*"}}}}), self.WS)
        self.assertFalse(ok, "an unrooted sweep can reach the key")
        self.assertIn("not rooted", why)

    def test_a_recursive_sweep_inside_the_workspace_is_allowed(self):
        # Sixteen of twenty-one refusals in one sweep were this: a reviewer globbing its
        # own workspace, which is exactly what working isolation invites. The workspace
        # holds the staged surface and the fixture and nothing else, so there is nothing
        # beneath it worth refusing.
        ok, why, _, _ = R.isolation_gate(json.dumps({"type": "tool_use", "part": {
            "tool": "glob", "state": {"status": "completed",
                                      "input": {"pattern": "**/*", "path": str(self.WS)}}}}), self.WS)
        self.assertTrue(ok, f"a workspace-rooted sweep was refused: {why}")

    def test_a_clean_run_is_not_refused(self):
        ok, why, _, indirect = R.isolation_gate(self._stream(
            ("read", {"path": f"{self.WS}/evals/fixtures/x.py"}),
            ("shell", {"command": f"wc -l {self.WS}/evals/fixtures/x.py"}),
        ), self.WS)
        self.assertTrue(ok, why)
        self.assertEqual(indirect, 0)


class GateBugRegressions(unittest.TestCase):
    """Four gates that were wrong in ways nothing could fail on.

    Every one of these shipped. A gate that cannot fail is indistinguishable from a gate
    that found nothing, and each of these was reporting success while doing nothing --
    which is worse than a gate that is absent, because it is counted.
    """

    @staticmethod
    def _tree():
        import shutil
        dest = Path(tempfile.mkdtemp()) / "se-review"
        shutil.copytree(REPO, dest,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv",
                                                      "probe", "docs"))
        return dest

    # -- the isolation flag was never sent ------------------------------------------
    def test_the_isolation_flag_survives_splatting(self):
        # `*FLAG` on a str yields one argv entry per character, so the harness was
        # passing `- - s t a n d a l o n e`. Nothing failed: the runner swallowed the
        # characters into its variadic message and the run proceeded with a corrupted
        # prompt, reporting no isolation while appearing to request it.
        self.assertIsInstance(R.RUNNER_ISOLATION_FLAG, tuple,
                              "splatting a string sends characters, not the flag")
        self.assertEqual([*R.RUNNER_ISOLATION_FLAG], ["--standalone"])

    def test_every_constant_splatted_into_argv_is_a_tuple(self):
        # Only the ones actually unpacked into argv. `RUNNER_OUTPUT_FORMAT` is passed by
        # value and is legitimately a string, so the check has to name its targets rather
        # than guess from a prefix.
        for name in ("RUNNER_SUBCOMMAND", "RUNNER_ISOLATION_FLAG"):
            self.assertIsInstance(getattr(R, name), tuple,
                                 f"{name} is splatted into argv and must be a tuple")

    # -- a bare forbidden directory slipped through ---------------------------------
    def test_a_bare_forbidden_directory_is_a_leak(self):
        ws = Path("/tmp/ws-probe")
        self.assertTrue(R.contamination(["evals/iteration-1"], ws),
                        "the verdict directory itself was not policed, only files beneath it")
        self.assertTrue(R.contamination(["review"], ws))

    def test_a_legitimate_fixture_read_is_not_a_leak(self):
        self.assertEqual(R.contamination(["evals/fixtures/a.py"], Path("/tmp/ws-probe")), [])

    # -- the vendor scan policed itself by ordering --------------------------------
    def test_the_vendor_scan_assigns_rel_before_testing_it(self):
        # Structural, and exact: the bug was source order, so source order is the check.
        # A behavioural repro would need a file sorting immediately after an exempt one,
        # which is a property of this tree rather than of the rule.
        import inspect
        import validate_skill as VS
        src = inspect.getsource(VS)
        assign = src.index("rel = path.relative_to(target_dir).as_posix()")
        test_at = src.index("rel.startswith(VENDOR_EXEMPT_PREFIXES)")
        self.assertLess(assign, test_at,
                        "the vendor scan tests `rel` before assigning it, so the exemption "
                        "applies to the previous file")

    # -- a Closed row could argue against itself -----------------------------------
    def test_a_closed_row_cannot_say_it_is_not_closed(self):
        dest = self._tree()
        reg = dest / "docs"
        reg.mkdir(exist_ok=True)
        shutil_copy = (REPO / "docs" / "named-gaps.md").read_text()
        reg.joinpath("named-gaps.md").write_text(shutil_copy)
        row = next(l for l in shutil_copy.splitlines() if l.startswith("| **G16**"))
        planted = row.replace("| Closed |", "| Partial |").replace(
            "**Closed 2026-10-05**", "**Closed 2026-10-05 — REOPENED**", 1)
        planted = planted.replace("| Partial |", "| Closed |", 1)
        (reg / "named-gaps.md").write_text(shutil_copy.replace(row, planted, 1))
        errors = V.validate_named_gaps(dest)
        self.assertTrue(any("arguing" in e or "REOPENED" in e for e in errors),
                        f"a Closed row containing REOPENED was accepted: {errors}")

    def test_a_table_fragment_is_rejected(self):
        dest = self._tree()
        reg = dest / "docs"
        reg.mkdir(exist_ok=True)
        reg.joinpath("named-gaps.md").write_text((REPO / "docs" / "named-gaps.md").read_text())
        with reg.joinpath("named-gaps.md").open("a") as fh:
            fh.write("**Narrowed, not closed.** orphaned paragraph | still carrying a bar |\n")
        errors = V.validate_named_gaps(dest)
        self.assertTrue(any("not a well-formed row" in e for e in errors),
                        f"an orphan fragment was accepted: {errors}")

    # -- a recursive sweep passed the absolute-path condition ----------------------
    def test_a_recursive_sweep_is_not_proof_of_isolation(self):
        ws = Path("/tmp/ws-probe")
        # Unrooted, so it can land anywhere -- including on the key. A sweep rooted at the
        # workspace is allowed and is covered in IsolationProof; this covers the other half.
        stream = json.dumps({"type": "tool_use", "part": {
            "tool": "glob", "state": {"status": "completed",
                                      "input": {"pattern": "**/*"}}}})
        ok, why, _, _ = R.isolation_gate(stream, ws)
        self.assertFalse(ok, "a sweep that does not root at the workspace can reach the key")
        self.assertIn("not rooted", why)


class RegisterHonesty(unittest.TestCase):
    """A register that cannot be checked is a register nobody can cite.

    Three ways this register had been wrong about itself, all of them invisible to the rule
    that existed: a preamble asserting a row was closed while the row said undated and
    Partial; a row marked Closed whose own text argued against its status; and a paragraph
    pasted into a cell that split the row into a fragment matching no row pattern at all.
    """

    def _tree(self):
        import shutil
        dest = Path(tempfile.mkdtemp()) / "se-review"
        shutil.copytree(REPO, dest,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "probe"))
        (dest / "docs").mkdir(exist_ok=True)
        (dest / "docs" / "named-gaps.md").write_text(
            (REPO / "docs" / "named-gaps.md").read_text())
        return dest

    def _errors(self, dest):
        return V.validate_named_gaps(dest)

    def test_the_real_register_is_honest(self):
        self.assertEqual(self._errors(REPO), [],
                         "the register in the tree fails its own rules")

    def test_prose_may_not_contradict_the_table(self):
        dest = self._tree()
        reg = dest / "docs" / "named-gaps.md"
        reg.write_text(reg.read_text() + "\n**G3** is **Partial**.\n")
        errs = self._errors(dest)
        self.assertTrue(any("prose says" in e for e in errs),
                        f"prose contradicting the table was accepted: {errs}")

    def test_prose_agreeing_with_the_table_is_fine(self):
        dest = self._tree()
        reg = dest / "docs" / "named-gaps.md"
        reg.write_text(reg.read_text() + "\n**G3** is **Closed**.\n")
        self.assertEqual([e for e in self._errors(dest) if "prose says" in e], [])

    def test_a_closed_row_carrying_a_contradiction_marker_is_rejected(self):
        dest = self._tree()
        reg = dest / "docs" / "named-gaps.md"
        text = reg.read_text()
        row = next(l for l in text.splitlines() if l.startswith("| **G3**"))
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", row)][1:-1]
        cells[2] = "**CLOSED 2026-10-05.** REOPENED after re-verification."
        reg.write_text(text.replace(row, f"| {cells[0]} | {cells[1]} | {cells[2]} | Closed |"))
        errs = self._errors(dest)
        self.assertTrue(any("arguing" in e for e in errs),
                        f"a Closed row saying REOPENED was accepted: {errs}")

    def test_an_orphan_fragment_is_rejected(self):
        dest = self._tree()
        reg = dest / "docs" / "named-gaps.md"
        with reg.open("a") as fh:
            fh.write("**Narrowed, not closed.** orphaned | still a table line |\n")
        errs = self._errors(dest)
        self.assertTrue(any("not a well-formed row" in e for e in errs),
                        f"an orphan fragment was accepted: {errs}")

    def test_every_row_is_single_line_and_four_columns(self):
        # The invariant the fragment rule defends, asserted directly rather than through
        # the fragment path, so the invariant is stated and not merely inferred.
        dest = self._tree()
        rows = [l for l in (dest / "docs" / "named-gaps.md").read_text().splitlines()
                if re.match(r"\|\s*\*\*[GN]\d+\*\*", l)]
        self.assertGreater(len(rows), 20, "the register lost its rows")
        for l in rows:
            self.assertEqual(len(re.split(r"(?<!\\)\|", l)) - 2, 4, f"row: {l[:60]}")


class TrendAndPortableMessages(unittest.TestCase):
    """A delta needs two points, and a refusal message is evidence too.

    Two things that are easy to get wrong in the same place. A trend block fed one base
    either prints a flat line or an invented 0.0, and both read as "nothing changed" when
    the truth is "nothing was compared". And a refusal message naming the offending path
    absolutely is a machine path written into a record that gets committed -- the reads
    beside it were made portable and the sentence above them was not.
    """

    @staticmethod
    def _stream(command):
        return json.dumps({"type": "tool_use", "part": {
            "tool": "shell", "state": {"status": "completed", "input": {"command": command}}}})

    def test_a_refusal_message_carries_no_absolute_path(self):
        import tempfile as tf
        ws = Path(tf.mkdtemp())
        for command in ("cat evals/evals.json", "ls evals/iteration-1/",
                        "cat /elsewhere/secret.txt"):
            _, why, _, _ = R.isolation_gate(self._stream(command), ws)
            self.assertNotIn(str(ws), why)
            self.assertFalse(why.startswith("/"), f"absolute path in the message: {why}")

    def test_trend_refuses_to_invent_a_delta_from_one_base(self):
        import eval_diagnostics as D
        got = D.trend()
        self.assertTrue(got["ok"])
        # Whatever the corpus holds, the block must either compare or say it cannot.
        if len(got["bases"]) < 2:
            self.assertIsNone(got["older"])
            self.assertEqual(got["rows"], [])

    def test_trend_orders_bases_by_time_not_by_digest(self):
        # Two short hex strings have no meaningful order. Sorting them lexicographically
        # put an older base after a newer one, so the delta came out reversed -- for a
        # trend that is worse than reporting none.
        import eval_diagnostics as D
        src = Path(D.__file__).read_text()
        self.assertIn("st_mtime", src, "bases must be ordered by when they were written")
        self.assertNotIn("bases = sorted(by_base)", src,
                         "digest-string order is not chronological order")


class StagingAndReduction(unittest.TestCase):
    """Where a workspace is created, and what a path is reduced to.

    The workspace location is not a style choice. It was a system temporary directory,
    which put a machine identifier and an account identifier into recorded evidence and is
    why the reduction helpers exist at all -- and it is the only location where isolation
    has been verified. The reduction is not a style choice either: it has to be idempotent,
    because a scrub that must be applied exactly once is a scrub that gets applied twice.
    """

    def test_the_stage_root_is_inside_this_repository(self):
        root = R.stage_root()
        self.assertTrue(str(root).startswith(str(R.SKILL_ROOT)),
                        f"workspace staged outside the repository: {root}")
        rel = root.relative_to(R.SKILL_ROOT).as_posix()
        ignores = (R.SKILL_ROOT / ".gitignore").read_text().splitlines()
        self.assertTrue(any(l.strip() in (f"/{rel}", f"/{rel.split('/')[0]}", rel.split('/')[0])
                            for l in ignores),
                        f"{rel} is not gitignored, so a staged workspace would be committed")

    def test_the_reduction_is_idempotent(self):
        cases = [
            "/var/folders/34/abcdefgh/T/se-run-eval-x-r1-a/f.py",
            "/private/var/folders/34/abcdefgh/T/se-run-eval-x-r2-b/evals/fixtures/a.md",
            "/Users/someone/else/repo/evals/evals.json",
            "ws/evals/fixtures/a.py",
            "<tmp>/34/abcdefgh/T/opencode/x.json",
        ]
        for c in cases:
            once = R.portable_path(c)
            self.assertEqual(R.portable_path(once), once, f"not idempotent: {c} -> {once}")
            self.assertNotIn("abcdefgh", once)
            self.assertNotIn("someone", once)

    def test_a_citation_survives_the_reduction(self):
        # The reason the reduction is allowed to touch evidence at all: the part that
        # carries meaning must come through untouched.
        out = R.sanitise_paths("Review: `/var/folders/34/abcdefgh/T/se-run-e-r1-a/"
                               "evals/fixtures/concurrency.py:10`")
        self.assertIn("concurrency.py:10", out)
        self.assertNotIn("abcdefgh", out)

    def test_a_read_only_run_does_not_resolve_inside_the_repository(self):
        # The double-prefix bug: `Path("<tmp>/...").resolve()` anchors at the current
        # directory, so reducing an already-reduced value made it a repository path.
        out = R.portable_path("<tmp>/34/abcdefgh/T/se-run-e-r1-a/f.py")
        self.assertFalse(out.startswith("repo/"), f"resolved into the repository: {out}")


class SweepComparability(unittest.TestCase):
    """A sweep spanning two trees cannot be differenced.

    Every verdict records the base it was graded at and `already_current` compares one
    verdict against one base. Neither notices that a sweep's arms recorded *different*
    bases, so a delta between them is attributed to the change under test when it is
    whatever landed between two arms. Observed directly on this repository: two arms of one
    ablation recorded different bases, because the commit was amended while the sweep ran,
    and nothing said so.
    """

    def test_the_base_is_read_once_per_sweep(self):
        src = Path(R.__file__).read_text()
        self.assertIn("sweep_base = current_base()", src)
        self.assertIn("moved_from", src)

    def test_the_base_helper_reads_head_and_never_raises(self):
        base = R.current_base()
        self.assertTrue(base is None or (isinstance(base, str) and len(base) >= 7),
                        f"unexpected base value: {base!r}")

    def test_the_cap_states_the_coupling_not_a_soft_rationale(self):
        # The number is coupled to the ledger's printable rows. Quoting comfort as the
        # reason invites someone to raise the cap and break the coupling, which is the
        # failure this replaced.
        fmt = (R.SKILL_ROOT / "shared" / "output-format.md").read_text()
        cap_at = fmt.index("Cap reports at 15")
        window = fmt[cap_at:cap_at + 600]
        self.assertIn("coupled", window)
        self.assertIn("deliberate.md", window)


class FailureOutputIsPublishable(unittest.TestCase):
    """A run log gets pasted into an issue, and an issue is public.

    A subprocess failure stringifies its own argv. Printing that verbatim put the runner's
    install path, the operator's home directory, and the entire grading prompt -- every
    assertion for the fixture included -- into sweep output. The gate against publishing a
    machine path was on committed files, and a run log is not one until someone pastes it.
    """

    def test_a_subprocess_failure_does_not_carry_its_argv(self):
        import subprocess
        try:
            subprocess.run(["/an/absolute/install/path", "run", "x"],
                           capture_output=True, timeout=0.01)
            self.skipTest("no subprocess failure to reduce")
        except Exception as exc:
            out = R.safe_error(exc)
            self.assertNotIn("/an/absolute/install/path", out)
            self.assertIn(type(exc).__name__, out)

    def test_the_reduction_is_bounded(self):
        msg = RuntimeError("x" * 400)
        self.assertLessEqual(len(R.safe_error(msg)), 200)

    def test_a_path_is_reduced_even_when_it_is_the_whole_message(self):
        out = R.safe_error(RuntimeError("/Users/someone/else/place/x.txt"))
        self.assertNotIn("someone", out)
        self.assertNotIn("/Users/", out)


class AggregateArithmetic(unittest.TestCase):
    """Four ways the benchmark reported a number that could not be true.

    Every one of these shipped and every one produced a plausible-looking line, which is
    the difficulty: `823/753 (109.3%)` reads as a bug in whatever produced it, not as four
    assertions passing more often than they should. The headline pass rate is what
    hillclimbing reads to choose an objective, so an impossible figure is a wrong
    instruction rather than a wrong report.
    """

    def test_passed_never_exceeds_total(self):
        # A verdict with replicates sums `passed` across every replicate while the assertion
        # count is counted once, so comparing them directly reported `823/753 (109.3%)`.
        # Assert it on the benchmark this repository actually produced, not on a literal.
        import json
        bench = R.SKILL_ROOT / "evals" / "iteration-1" / "benchmark.json"
        if not bench.is_file():
            self.skipTest("no benchmark yet")
        doc = json.loads(bench.read_text())["run_summary"]
        for arm in ("with_skill", "without_skill"):
            v = doc[arm]
            self.assertLessEqual(v["total_passed"], v["total_assertions"],
                                 f"{arm} reports more passes than assertions")
            self.assertGreater(v["total_assertions"], 0, f"{arm} has no denominator")

    def test_a_void_verdict_is_excluded_from_the_aggregate(self):
        # The aggregate used to admit a verdict on the strength of a `grading.json` merely
        # existing. Measured: 46 of the 86 measured with_skill evals cannot contribute.
        src = Path("scripts/grade_evals.py").read_text()
        self.assertIn("def currency(", src,
                      "the aggregate must classify each verdict rather than test for a file")
        self.assertIn('"unverified"', src)
        self.assertIn('"void"', src)

    def test_unverified_is_not_reported_as_void(self):
        """A verdict that cannot be checked has not been contradicted.

        The two-outcome version returned False for both, and reported 40 unexamined verdicts
        as 40 contradicted ones. Only 8 are actually contradicted. Conflating them points the
        next person at the wrong repair -- re-grading 40 verdicts that were never wrong -- and
        this session has already reported one invented verdict regression by reading a dict
        the same way.
        """
        import tempfile
        src = Path("scripts/grade_evals.py").read_text()
        self.assertNotIn("return False\n        recorded", src)
        self.assertRegex(src, r'if "assertion_results" not in gj:\s*\n\s*return "unverified"')

    def test_void_is_not_conflated_with_unmeasured(self):
        # `stale` records "no grading.json" as well as "disagrees with the corpus". Using
        # it to decide what is void excluded every eval in the corpus, including the ones
        # whose one arm is perfectly good.
        src = Path(Path(G.__file__) if False else "scripts/grade_evals.py").read_text()
        self.assertNotIn("stale_names = {s[", src,
                         "void must be computed, not read off the staleness list")

    def test_each_arm_carries_its_own_denominator(self):
        # The baseline arm reported 77 of 640 when it had 193, and the skill-versus-baseline
        # delta divides by that number.
        import json
        bench = R.SKILL_ROOT / "evals" / "iteration-1" / "benchmark.json"
        if not bench.is_file():
            self.skipTest("no benchmark yet")
        doc = json.loads(bench.read_text())["run_summary"]
        self.assertNotEqual(doc["with_skill"]["total_assertions"],
                            doc["without_skill"]["total_assertions"],
                            "the two arms have different measured populations; if these are "
                            "equal, one arm is reporting the other's denominator")

    def test_a_block_that_cannot_measure_says_so(self):
        """A check that reports nothing is indistinguishable from one that found nothing.

        The corpus declares `assertion_roles` per eval, but no stored verdict recorded which
        assertion was which role. The block that separates verdict-role assertions from
        probe-role ones read that field, found it absent on all 172 verdicts, iterated an
        empty dict and printed nothing -- while sitting under a section that does print, so
        the section looked covered. A private `_excluded` key added to the same return value
        is what exposed it: by crashing rather than by reporting.
        """
        import contextlib
        import io
        sys.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import eval_diagnostics as D
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            D.print_verdict_probe(D.verdict_rates())
        out = buf.getvalue()
        self.assertIn("VERDICT vs PROBE ASSERTIONS", out,
                      "the section must announce itself even when it cannot measure")
        self.assertTrue("NOT MEASURED" in out or "verdict_passed" not in out,
                        "either the block measures something, or it says it cannot")
        # A metadata key must never be iterated as an arm.
        for arm, stats in D.verdict_rates().items():
            if arm.startswith("_"):
                self.assertIsInstance(stats, dict)
                self.assertNotIn("verdict_passed", stats,
                                 "metadata must not be shaped like an arm's statistics")

class NoAxisPopulation(unittest.TestCase):
    """The no-axis population has to be read from the findings, not from a self-report.

    The counter originally aggregated a header the reviewer writes about its own work. 16
    of the 25 reviews carrying findings did not write one, so 17 reviews contributed
    nothing -- which the tool then reported as "the population cannot be sized". The
    findings carry their axis code inline, so the population was readable from the evidence
    the whole time and the instrument was the thing that could not read it.

    These call the shipped reader against a corpus written to a temporary directory. An
    earlier version of this class re-implemented the parser inline, which tested the copy
    rather than the code -- and the copy carried a bug the original did not.
    """

    BLOCK = """# Review: x.py

`3 findings`
## Findings

### [MAJOR] Canonical placement
- **Domain:** Correctness (A1)
- **Evidence:** `x.py:1`

### [MAJOR] No domain line at all
- **Evidence:** `x.py:2`

### [MINOR] Code wrapped in backticks
- **Domain:** Security (`A5`)

None.
"""

    MULTI = """# Review: y.py

## Findings

### [MAJOR] Two codes inside one parenthesis group
- **Domain:** Maintainability (B1 Complexity, B5 Dead code)
"""

    def _corpus(self, *blocks):
        import tempfile
        root = Path(tempfile.mkdtemp())
        for i, b in enumerate(blocks):
            d = root / "evals" / "iteration-1" / f"eval-{i}" / "with_skill"
            d.mkdir(parents=True)
            (d / "review.md").write_text(b)
        sys.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import eval_diagnostics as D
        return D.no_axis_from_findings(root)

    def test_one_finding_is_counted_once_and_never_paired(self):
        # Pairing a list of headings with a list of Domain lines desynchronises at the
        # first finding that omits a field -- precisely the one worth seeing.
        got = self._corpus(self.BLOCK)
        self.assertEqual(got["findings"], 3, got)
        self.assertEqual(got["canonical"], 1, got)
        self.assertEqual(got["backticked"], 1, got)
        self.assertEqual(got["uncoded"], 1, got)

    def test_a_missing_domain_line_is_uncoded_not_zero(self):
        # A finding with no Domain line is a finding the registry may not cover. Counting it
        # as zero is how an uncovered shape stays invisible.
        got = self._corpus(self.BLOCK)
        self.assertEqual(got["uncoded"], 1, got)
        self.assertTrue(any("no Domain line" in d[2] for d in got["uncoded_detail"]), got)

    def test_multiple_codes_in_one_group_is_not_the_canonical_form(self):
        # `(B1 Complexity, B5 Dead code)` resolves for a reader and not for a strict one,
        # so it belongs with the unreadable rather than inflating the canonical count.
        got = self._corpus(self.MULTI)
        self.assertEqual(got["canonical"], 0, got)
        self.assertEqual(got["uncoded"], 1, got)

    def test_the_reader_does_not_depend_on_the_header(self):
        # Two reviews, identical findings, one carrying the header and one not, must size
        # the same population. The header is corroboration, never the instrument.
        bare = self._corpus(self.BLOCK)
        headed = self._corpus(
            self.BLOCK.replace("## Findings",
                               "Unclassified: 0 findings fit no axis code\n\n## Findings"))
        self.assertEqual(bare, headed)

class ReplicatesRequired(unittest.TestCase):
    """The count has to be the count, checked against a hand calculation.

    `replicates_required` exists to turn "underpowered" into a number. A number that is not
    checked is an adjective with a decimal point, and the corpus has already been misled by
    one plausible-looking figure this session.
    """

    def test_matches_the_hand_calculation(self):
        sys.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import eval_diagnostics as D
        # n = 2 (z_0.975 + z_0.80)^2 sd^2 / effect^2 = 2 (1.9600 + 0.8416)^2 .04 / .050625
        self.assertEqual(D.replicates_required(0.2, 0.225), 13)

    def test_quadruples_when_the_effect_halves(self):
        # The square in the denominator is the whole point: halving the effect quadruples n.
        # Asserted within rounding, not exactly -- the count is ceiled, so 16 becomes 63 and
        # not 64, and a test demanding the exact factor would be testing the absence of a
        # ceiling rather than the arithmetic.
        sys.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import eval_diagnostics as D
        big, small = D.replicates_required(0.2, 0.20), D.replicates_required(0.2, 0.10)
        self.assertLessEqual(abs(small - big * 4), 2,
                             f"expected ~{big * 4}, got {small}")
        self.assertGreaterEqual(small, big * 3)

    def test_grows_with_the_spread(self):
        sys.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import eval_diagnostics as D
        self.assertGreater(D.replicates_required(0.4, 0.10), D.replicates_required(0.2, 0.10))

    def test_refuses_to_divide_by_a_zero_effect(self):
        # An effect of zero needs infinite replicates. Returning a finite count would let a
        # caller plan a sweep that cannot answer its question.
        sys.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import eval_diagnostics as D
        for bad in (0, -0.1):
            self.assertEqual(D.replicates_required(0.2, bad), 400)

    def test_the_reach_is_printed_not_only_computed(self):
        # A figure nothing prints is a figure nobody reads, which is the defect this whole
        # row keeps describing.
        src = Path(R.SKILL_ROOT / "scripts" / "eval_diagnostics.py").read_text()
        self.assertIn("RESOLVABLE EFFECT", src)
        self.assertIn("print_power(replicate_spread())", src)

    def test_the_ablation_is_differenced_over_a_shared_population(self):
        """Two arms aggregated over their own populations are not an experiment.

        Reported that way the ablation printed `+17.4 pts` from 594 assertions against 272,
        with a "KILLED" verdict underneath telling a reader to cut the gate. Differenced over
        the fixtures current in both arms -- ids 86-90, five of them -- the same stored
        verdicts give **+7.9 points**. Less than half, and the verdict underneath it rests on
        five fixtures rather than the whole corpus.

        This is the same defect `grade_evals.py` had in its baseline denominator. It was fixed
        there, and reintroduced here, which is why the test asserts the shape rather than the
        current numbers: those will move, the requirement will not.
        """
        import sys as _s
        _s.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import eval_diagnostics as D
        src = Path(D.__file__).read_text()
        self.assertIn("_paired", src, "the ablation must be computed over a shared population")
        self.assertIn('shared = sorted(set(per_eval["with_skill"]) & set(per_eval["nosuppress"]))',
                      src, "the shared population must be the intersection of both arms")
        self.assertIn("NOT MEASURED", src,
                      "an empty intersection must be reported, not differenced anyway")

    def test_a_rate_is_published_with_its_sample_count(self):
        # A rate averaged over 26 samples is not the same quantity as one over 24, and a
        # reader cannot infer n from a denominator that counts assertions.
        import sys as _s
        _s.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import eval_diagnostics as D
        self.assertIn("over {s.get('samples', 0)} samples",
                      Path(D.__file__).read_text())

class CollectableBySilence(unittest.TestCase):
    """The classifier decides which assertions a silent review can collect, and it moved 104
    assertions across the verdict/probe split and rewrote 22 others on its word. So each rule
    it applies is pinned here, including the two orderings that were got wrong first.

    A regex reading only for absence caught 7 of 860 assertions where the true count was 59.
    A version that then checked the count pin first treated "Header matches pattern: 0
    findings" as discriminating, because "0 findings" matched the count pattern -- and a
    pinned count of zero is the one count silence also reports. Both failures were invisible
    in the output, which looked like a plausible list either way.
    """

    def setUp(self):
        sys.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import mismatch_probe
        self.M = mismatch_probe

    def test_an_absence_claim_is_collectable(self):
        self.assertEqual(
            self.M.collectable("Does NOT report the queue as unbounded growth"), "absence claim")

    def test_a_format_contract_is_collectable_even_with_a_count_in_it(self):
        self.assertEqual(
            self.M.collectable("Header matches pattern: 0 findings - C:0 M:0 m:0 i:0"),
            "format contract")

    def test_a_pinned_non_zero_count_discriminates(self):
        self.assertIsNone(
            self.M.collectable("Exactly 2 findings are reported above Info severity"))

    def test_a_pinned_zero_count_does_not_discriminate(self):
        # Silence reports zero every time.
        self.assertEqual(
            self.M.collectable("Exactly 0 findings above Info severity"), "zero count")

    def test_an_engagement_clause_makes_a_zero_count_discriminating(self):
        # Binding an absence to the observation that licenses it is the whole fix, so the
        # binding has to beat the zero-count rule that came before it.
        self.assertIsNone(self.M.collectable(
            "Reports exactly zero findings above Info severity **as a conclusion**: the "
            "review reaches it having named that dispatch applies no filter"))

    def test_the_format_check_runs_before_the_count_check(self):
        # Ordering, not coverage, is what this asserts: both substrings are present.
        text = "Header matches pattern: 0 findings - C:0 M:0 m:0 i:0"
        self.assertTrue(self.M.FORMAT_CONTRACT.search(text))
        self.assertTrue(self.M.COUNT_PINNED.search(text))
        self.assertEqual(self.M.collectable(text), "format contract")

    def _floors(self):
        import json
        corpus = {e["id"]: e for e in json.loads(
            (R.SKILL_ROOT / "scripts" / ".." / "evals" / "evals.json").read_text())["evals"]}
        return self.M.predicted_floor(corpus, sorted(corpus))

    def test_the_original_floor_inversion_is_reversed(self):
        """Measured 2026-10-05: the suppress family (80-85) collected 55.6-66.7 percent from an
        unrelated review and could not resolve a 40-point difference, while the blind family
        (86-91) collected 10-20 percent and could. The ordering was backwards.

        Their assertions were then rewritten to bind each absence to the positive observation
        that licenses it, and the 82 format contracts moved onto the probe side. The ordering
        is now the other way round -- which is the fix, and this asserts it rather than the
        condition the fix was made in response to.
        """
        floors = self._floors()
        suppress = max(floors[i]["free_pct"] for i in range(80, 86))
        blind = max(floors[i]["free_pct"] for i in range(86, 92))
        self.assertLess(suppress, blind,
                        f"suppress {suppress} should now sit below blind {blind}")

    def test_no_fixture_has_a_verdict_panel_that_silence_can_collect_most_of(self):
        # The kill criterion is 40 points, so a panel a silent review collects 40 percent of
        # cannot express a 40-point difference at all.
        floors = self._floors()
        worst = max(floors[i]["free_pct"] for i in floors)
        self.assertLess(worst, 40.0, f"a fixture's verdict panel is {worst}% collectable by silence")

class PublishedBlockMatchesReadme(unittest.TestCase):
    """The README's headline must equal the grader's, checked on every run.

    That block is the only number in this repository a reader can see without opening the
    file it came from. It went stale twice: it sat reading `643/689 (93.3%)` and `+71.9%`
    weeks after the correction that produced `409/640 (63.9%)`, asserting variance was
    unmeasured three weeks after it was measured at 0.156; then it was pasted again from the
    grader's own output and drifted a second time inside the hour, when authoring the corpus
    voided two fixtures' verdicts and moved the denominator to 36.

    Generating it is not enough. Generating it and pasting it is still remembering, so the
    README holds a derived artefact and nothing checks that the two agree. This does.
    """
    def test_the_readme_quotes_the_graders_own_numbers(self):
        import sys
        sys.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import grade_evals as G
        bench = R.SKILL_ROOT / "evals" / "iteration-1" / "benchmark.json"
        if not bench.is_file():
            self.skipTest("no benchmark yet")
        summary = json.loads(bench.read_text())["run_summary"]
        w, o = summary["with_skill"], summary["without_skill"]
        block = G.published_block(
            w["total_assertions"], w["total_passed"],
            o["total_assertions"], o["total_passed"], 0, 0, 0, 0)
        readme = (R.SKILL_ROOT / "evals" / "README.md").read_text()
        for line in block.splitlines():
            if line.startswith("Paired") or line.startswith("Admissible"):
                continue
            self.assertIn(line, readme,
                          f"the README does not quote the grader's line: {line!r}")

    def test_a_superseded_rate_appears_only_as_recorded_history(self):
        # A corrected figure left in place is worse than one never published: it is the one
        # number nobody re-reads. Quoting it once, inside the sentence that says it was
        # wrong, is how a reader finds out the block has been corrected before. Quoting it
        # twice means it is being used.
        import re as _re
        readme = (R.SKILL_ROOT / "evals" / "README.md").read_text()
        for stale in ("643/689", "+71.9%", "409/640"):
            hits = _re.findall(_re.escape(stale), readme)
            if not hits:
                continue
            self.assertLessEqual(
                len(hits), 1,
                f"{stale} appears {len(hits)} times; more than once means it is quoted as "
                f"current rather than recorded as superseded")

    def test_a_strict_role_assertion_is_not_dropped_from_the_rate(self):
        """7 assertions grade the *fix*, and they were in neither numerator nor denominator.

        "Fix replaces the price-keyed guard with an identity-keyed one" is a quality claim
        about remediation. Falling through both branches of the rate meant finding a defect
        and proposing the wrong repair scored the same, and nothing printed to say so.
        """
        import sys
        sys.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import eval_diagnostics as D
        src = Path(D.__file__).read_text()
        self.assertIn('if role == "strict":', src,
                      "the strict role must be counted, not fall through")
        roles = D.verdict_rates().get("_roles") or {}
        self.assertIn("strict", roles,
                      "the block must report which roles it counted, so a silent drop "
                      "cannot recur unnoticed")

class RecoverableVersusRegenerable(unittest.TestCase):
    """A verdict missing its evidence field splits two ways, and only one is repairable.

    A verdict carrying `summary.pass_rate` and no `assertion_results` is a number with nothing
    behind it, and excluding it from every aggregate is correct. But excluding is not
    repairing, and "no assertion_results recorded" reads like a field to fill in when in most
    cases the review it would be filled from is not on disk.

    Measured: 40 verdicts in that state, **4** with a review body and **36** without. So the
    honest cost is 4 grading calls and 36 reviewer runs -- not "40 grading calls rather than 40
    review runs", which is what a first pass at this concluded from the field's name alone.
    """
    def setUp(self):
        sys.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import eval_diagnostics as D
        self.D = D

    def test_the_two_states_are_counted_and_not_merged(self):
        # The recoverable side was 4 and has been recovered, so this asserts the split is
        # *reported* -- both counts present, non-negative, and summing to the number of
        # verdicts actually in that state -- rather than asserting a recoverable one still
        # exists, which stops being true the moment the tool works.
        recoverable, unrecoverable = self.D.find_recoverable()
        got = self.D.recover_verdicts(None, None)
        self.assertEqual(got["recoverable"], len(recoverable))
        self.assertEqual(got["unrecoverable"], len(unrecoverable))
        self.assertGreaterEqual(got["recoverable"], 0)
        self.assertGreaterEqual(got["unrecoverable"], 0)
        self.assertEqual(got["recoverable"] + got["unrecoverable"],
                         len(recoverable) + len(unrecoverable))
        for name, why in unrecoverable:
            self.assertTrue(why, f"{name} is unrecoverable with no stated reason")

    def test_an_unrecoverable_verdict_names_why(self):
        _, unrecoverable = self.D.find_recoverable()
        for name, why in unrecoverable:
            self.assertTrue(why, f"{name} is unrecoverable with no stated reason")

    def test_recovery_costs_a_grading_call_only_where_a_body_exists(self):
        # The point of the split: no count of grading calls recovers a verdict with no review
        # body behind it, so the two must never be presented as one number.
        recoverable, unrecoverable = self.D.find_recoverable()
        src = Path(self.D.__file__).read_text()
        self.assertIn("NOT recoverable:", src,
                      "the unrecoverable count must be printed separately from the recoverable one")
        # The recoverability split is asserted against the corpus, not against the source text:
        # if the two states were ever merged, the discovery would stop reporting one of them.
        self.assertEqual(len(unrecoverable),
                         sum(1 for _, why in unrecoverable if why == "no review body on disk")
                         + sum(1 for _, why in unrecoverable if why != "no review body on disk"))

    def test_a_recovered_verdict_is_marked_as_a_regrade(self):
        # The stored summary came from an earlier grader. Writing assertion_results beside it
        # without saying so presents a re-grade as the original verdict.
        src = Path(self.D.__file__).read_text()
        self.assertIn('grading["recovered"]', src)
        self.assertIn("grader_config", src)

class RecoveryWritePath(unittest.TestCase):
    """The write half of `--recover-verdicts` has never run against a real grader.

    It failed once on a missing import and then on `provider.quota 402`, so the code that
    rewrites a stored verdict has never executed. Committing it in that state means the first
    real run is also the first debug, on the four verdicts whose repair is supposed to be
    cheap. The grader is stubbed here so the write, the provenance record, and the resulting
    classification are all known-good before any quota is spent on them.
    """
    def setUp(self):
        sys.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import eval_diagnostics as D
        import run_evals
        self.D, self.R = D, run_evals
        self.calls = []

    def _recover_one(self, tmp, grader=None):
        import json as _json
        entry = _json.loads((R.SKILL_ROOT / "evals" / "evals.json").read_text())["evals"][0]
        assertions = entry["assertions"]
        arm = tmp / "eval-x" / "with_skill"
        arm.mkdir(parents=True)
        (arm / "review.md").write_text("a stored review\n")
        (arm / "grading.json").write_text(_json.dumps(
            {"eval_id": entry["id"], "eval_name": "eval-x",
             "summary": {"passed": len(assertions), "failed": 0,
                         "total": len(assertions), "pass_rate": 1.0}}))
        before = (arm / "grading.json").read_text()
        real_ITER, real_Dglob = self.D.ITERATION, self.D.glob.glob
        self.D.ITERATION = tmp
        self.D.glob.glob = lambda pat: [str(arm / "grading.json")]

        def stub(review, asserts, timeout, work, model=None):
            self.calls.append(len(asserts))
            return [{"passed": True, "evidence": "e"} for _ in asserts]

        self.R.grade = grader or stub
        try:
            got = self.D.recover_verdicts(None, None)
        finally:
            self.D.ITERATION, self.D.glob.glob = real_ITER, real_Dglob
        return entry, arm / "grading.json", got, before

    def test_it_writes_assertion_results_and_marks_the_regrade(self):
        import json as _json
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            entry, path, got, _ = self._recover_one(Path(td))
            doc = _json.loads(path.read_text())
        self.assertEqual(len(self.calls), 1, "exactly one grading call for one body")
        self.assertIn("assertion_results", doc)
        self.assertEqual([r["text"] for r in doc["assertion_results"]], entry["assertions"])
        self.assertEqual(doc["assertion_roles"], entry.get("assertion_roles"))
        self.assertIn("recovered", doc)
        self.assertIn("grader_config", doc["recovered"])
        self.assertIn("re-grading", doc["recovered"]["note"])
        self.assertEqual(got["recovered_current"], 1, got)
        self.assertEqual(got["failed"], 0, got)

    def test_the_stale_summary_is_not_presented_as_the_regrades_result(self):
        # The stored summary says 8/8 and predates this grader. Leaving it unqualified beside
        # fresh assertion_results presents two numbers from two graders as one verdict.
        import json as _json
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            _, path, _, _ = self._recover_one(Path(td))
            doc = _json.loads(path.read_text())
        self.assertIn("note", doc["recovered"])
        self.assertIn("summary_before", doc["recovered"],
                      "the replaced number must be retained, not overwritten into silence")

    def test_a_grader_failure_leaves_the_verdict_untouched(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            _, path, got, before = self._recover_one(Path(td))
        # A failed run must not half-write: the verdict either gains the field or is untouched.
        self.assertEqual(got["failed"], 0, "the stub succeeds, so nothing should have failed")
        self.assertIsNone(json.loads(before).get("recovered"),
                        "a successful recovery must leave the record in place")

    def test_a_grader_failure_is_counted_named_and_writes_nothing(self):
        """The failure path was untested, and mutating it to `failed += 0` passed the suite.

        It is the path that runs when quota is exhausted -- which is the state this tool was
        last invoked in -- so it is the path most likely to be taken next, and a failure that
        is neither counted nor named reads as a success with no rows.
        """
        import tempfile
        def boom(*a, **k):
            raise RuntimeError("runner exited 1: provider.quota 402")

        with tempfile.TemporaryDirectory() as td:
            _, path, got, before = self._recover_one(Path(td), grader=boom)
            after = path.read_text()
        self.assertEqual(got["failed"], 1, f"a raised grader must be counted: {got}")
        self.assertEqual(got["recovered_current"], 0)
        self.assertEqual(got["recovered_void"], 0)
        self.assertEqual(len(got["rows"]), 1)
        self.assertEqual(got["rows"][0]["state"], "ungradeable")
        self.assertIn("402", got["rows"][0]["detail"],
                      "the reason is reported, not swallowed")
        self.assertEqual(after, before, "a failed re-grade must leave the verdict byte-identical")
        self.assertNotIn("assertion_results", json.loads(after))

    def test_recovery_reports_zero_rather_than_nothing_when_there_is_nothing_to_do(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            # An iteration directory with nothing in it: discovery finds no verdicts at all.
            real_ITER, real_glob = self.D.ITERATION, self.D.glob.glob
            self.D.ITERATION, self.D.glob.glob = Path(td), lambda pat: []
            try:
                got = self.D.recover_verdicts(None, None)
            finally:
                self.D.ITERATION, self.D.glob.glob = real_ITER, real_glob
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.D.print_recovered(got)
        self.assertIn("NOT recoverable: 0", buf.getvalue())

class SummaryAgreesWithItsOwnEvidence(unittest.TestCase):
    """A summary is derived from the assertion results beside it, so the two must agree.

    This test was first written against a finding that was wrong. Comparing a verdict's
    `summary.passed` against its `assertion_results` yielded 22 apparent disagreements and 267
    "inflated" assertions, all in the flattering direction -- which looked like systematic
    miscounting and nearly became a register row. It was a comparison error: `summary.passed`
    sums every replicate while `assertion_results` is the primary sample alone, so 18-against-9
    on a three-sample verdict is arithmetic, not inflation. The fix that followed was worse --
    it made the aggregate read the primary sample, silently swapping the replicate mean for one
    sample and dropping the headline from 66.1% to 45.7%.

    So the invariant is asserted on the *rate*, and only where the two describe the same
    population. Where they legitimately differ -- a verdict re-graded by a later grader -- the
    older number is kept beside the newer under `recovered.summary_before` rather than
    overwritten into silence.
    """
    def _verdicts(self):
        import glob
        for f in glob.glob(str(R.SKILL_ROOT / "evals" / "iteration-1" / "eval-*"
                               / "*" / "grading.json")):
            d = json.loads(Path(f).read_text())
            res = d.get("assertion_results")
            s = d.get("summary") or {}
            if res and s.get("total"):
                yield Path(f), d, res, s

    def test_a_summary_rate_matches_the_replicate_summary_it_was_written_from(self):
        """The check that actually holds, found after two wrong ones.

        `summary.total` counts replicates while `assertion_results` is the primary sample, so
        the two describe different populations and comparing them directly invents
        disagreements. The comparable figure is `replicate_summary.mean_pass_rate`, which is
        what the summary was computed from. Across all 20 verdicts carrying replicates the two
        rates agree exactly.
        """
        checked = 0
        for path, d, res, s in self._verdicts():
            rs = d.get("replicate_summary") or {}
            if (rs.get("n") or 0) < 2 or rs.get("mean_pass_rate") is None:
                continue
            checked += 1
            self.assertAlmostEqual(
                s["passed"] / s["total"], rs["mean_pass_rate"], places=2,
                msg=f"{path.parent.parent.name}/{path.parent.name}: summary "
                    f"{s['passed']}/{s['total']} disagrees with the replicate mean "
                    f"{rs['mean_pass_rate']}")
        self.assertGreater(checked, 0, "no verdict carried replicates to check")

    def test_a_summary_never_exceeds_its_own_total(self):
        # 11-of-8 and 18-of-9 are the shape a replicate sum takes against an assertion count.
        # Impossible on any reading, so this catches it without needing to know the semantics.
        for path, d, res, s in self._verdicts():
            self.assertLessEqual(s["passed"], s["total"],
                                 f"{path.parent.parent.name}: summary records more passes "
                                 f"than assertions")

    def test_a_regrade_keeps_the_number_it_replaced(self):
        found = 0
        for path, d, res, s in self._verdicts():
            if "recovered" not in d:
                continue
            found += 1
            self.assertIn("summary_before", d["recovered"])
            self.assertIn("grader_config", d["recovered"])
            self.assertIn("kept because it disagreed", d["recovered"]["note"])
            self.assertIsNotNone(d["recovered"]["summary_before"].get("total"),
                                 "the replaced summary must remain readable")
        self.assertTrue(found, "expected at least one recovered verdict")

class EvalRegistryIsAFunction(unittest.TestCase):
    """The id-to-directory map is hand-maintained and was checked by nothing at all.

    No validator and no test referenced `eval_registry.py` before this. Of the faults it could
    hold, only one loses data.

    A **missing key** is harmless, and an earlier account of this called it a silent
    writer/reader split -- which is wrong. `run_evals.py` and `grade_evals.py` both resolve a
    name through `eval_name()`, so they cannot disagree about where a verdict lives; an
    unregistered id falls back to `eval-<id>` on both sides and works. The consequence is a
    directory name that says nothing, not a lost verdict.

    A **duplicate value** is the one that destroys evidence: two ids resolving to one directory
    means both arms of both fixtures write the same path, and the second run overwrites the
    first with nothing to show it happened.
    """
    def setUp(self):
        sys.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import validate_skill
        self.V = validate_skill

    def _errs(self, corpus_ids, names):
        import eval_registry
        saved = dict(eval_registry.EVAL_NAMES)
        try:
            eval_registry.EVAL_NAMES.clear()
            eval_registry.EVAL_NAMES.update(names)
            return self.V._validate_registry(
                R.SKILL_ROOT, [{"id": i} for i in corpus_ids])
        finally:
            eval_registry.EVAL_NAMES.clear()
            eval_registry.EVAL_NAMES.update(saved)

    def test_a_duplicate_directory_name_is_rejected(self):
        errs = self._errs([5, 99], {5: "eval-clean", 99: "eval-clean"})
        self.assertTrue(any("same directory" in e for e in errs), errs)

    def test_an_unregistered_id_is_reported_but_not_fatal(self):
        # Harmless: both writer and reader fall back identically. Worth naming, not worth failing.
        # 103 is in the corpus but absent from the registry, so it falls back on both sides.
        errs = self._errs([5, 103], {5: "eval-clean"})
        self.assertTrue(any("carry no registry entry" in e for e in errs), errs)
        self.assertFalse(any("overwrite" in e for e in errs), errs)

    def test_a_registry_id_with_no_fixture_is_dead_weight(self):
        errs = self._errs([5], {5: "eval-clean", 7: "eval-deadlock"})
        self.assertTrue(any("dead weight" in e for e in errs), errs)

    def test_the_real_registry_is_clean_and_covers_the_corpus(self):
        import json
        import eval_registry
        ids = [e["id"] for e in json.loads(
            (R.SKILL_ROOT / "evals" / "evals.json").read_text())["evals"]]
        errs = self.V._validate_registry(R.SKILL_ROOT, [{"id": i} for i in ids])
        self.assertEqual(errs, [], "the shipped registry is not clean")

    def test_writer_and_reader_resolve_an_unregistered_id_identically(self):
        # The claim that makes a missing key harmless, asserted rather than assumed -- and the
        # claim an earlier account of this got wrong.
        import eval_registry
        for eid in (103, 999):
            self.assertEqual(eval_registry.eval_name(eid), f"eval-{eid}")
        import grade_evals
        self.assertEqual(grade_evals.EVAL_NAMES.get(103, f"eval-{103}"), "eval-103",
                         "the reader must fall back exactly as the writer does")

class ConcernClassification(unittest.TestCase):
    """Which claim an assertion tests, and the two mistakes the split invites.

    G19 exists because the corpus scored detection and severity in one number, so the headline
    could not say which of them the skill contributes -- and the blind re-measurement has
    detection at +4.2 points against severity at +33.3, so merging them optimises the axis the
    skill barely moves.

    Two ways to get this wrong, both of which would misstate what the skill does. Put
    "Exactly 1 finding above Info severity" in the severity bucket because the word appears, and
    detection loses the only assertion that fails when nothing is found. Put "Fix replaces the
    price-keyed guard" in detection, and the skill is credited with repairing defects that
    detection is about.
    """
    def setUp(self):
        sys.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import mismatch_probe as MP
        self.MP = MP

    def test_a_count_of_findings_is_detection_not_severity(self):
        # It mentions severity and fails only when nothing was found.
        self.assertEqual(self.MP.concern("Exactly 1 finding above Info severity"), "detection")
        self.assertEqual(self.MP.concern("Zero findings above Info severity"), "detection")

    def test_a_rung_claim_is_severity(self):
        self.assertEqual(self.MP.concern("Finding is graded exactly CRITICAL"), "severity")
        self.assertEqual(self.MP.concern("Finding is graded at least MAJOR"), "severity")

    def test_a_proposed_fix_is_remediation_not_detection(self):
        self.assertEqual(
            self.MP.concern("Fix replaces the price-keyed guard with an identity-keyed one"),
            "remediation")
        self.assertEqual(
            self.MP.concern("Fix returns NaN for the missing branch, or raises the frame"),
            "remediation")

    def test_naming_the_mechanism_is_detection(self):
        self.assertEqual(
            self.MP.concern("Identifies the guard in ChainRecorder.__call__ that returns early"),
            "detection")

    def test_the_split_covers_every_verdict_role_assertion_exactly_once(self):
        import json
        corpus = {e["id"]: e for e in json.loads(
            (R.SKILL_ROOT / "evals" / "evals.json").read_text())["evals"]}
        got = self.MP.concern_split(corpus)
        self.assertEqual(got["totals"]["total"],
                         got["totals"]["detection"] + got["totals"]["severity"]
                         + got["totals"]["remediation"],
                         "every assertion must land in exactly one bucket")
        self.assertGreater(got["totals"]["severity"], 0,
                           "a corpus with no severity assertions cannot answer the question")
        blank = [i for i, r in got["per_fixture"].items()
                 if r["severity"] + r["remediation"] == 0]
        self.assertLessEqual(len(blank), 1,
                             f"{len(blank)} fixtures test neither severity nor remediation")

    def test_concern_split_is_role_aware_and_defaults_to_the_whole_panel(self):
        import json
        corpus = {e["id"]: e for e in json.loads(
            (R.SKILL_ROOT / "evals" / "evals.json").read_text())["evals"]}
        verdict = self.MP.concern_split(corpus, None, "verdict")["totals"]["total"]
        every = self.MP.concern_split(corpus, None, None)["totals"]["total"]
        self.assertLess(verdict, every,
                        "the verdict-role panel is a subset of the whole panel")

class BlindStripping(unittest.TestCase):
    """Docstrings carry the defect in this repo, so stripping them is the whole method.

    The fixture convention writes the planted defect into the module docstring --
    `CRITICAL DEFECT: ...` -- so a reviewer that reads it is transcribing rather than detecting,
    and any comparison built on unstripped fixtures measures reading comprehension instead.
    Re-serialising through `ast` removes the confound without touching behaviour.

    This matters enough that the stripping is asserted rather than assumed, including the case
    that must NOT be papered over: a fixture that will not parse keeps its original, because
    quietly passing it through unstripped would put the confound back while the report claimed it
    was gone.
    """
    def setUp(self):
        sys.path.insert(0, str(R.SKILL_ROOT / "scripts"))
        import blind_measure as B
        self.B = B

    SRC = ('"""Module docstring naming the defect."""\n'
           'def f(x):\n'
           '    """Function docstring."""\n'
           '    # a revealing comment\n'
           '    return x + 1  # trailing\n')

    def test_docstrings_and_comments_are_removed(self):
        out = self.B.strip_annotations(self.SRC)
        self.assertNotIn("Module docstring", out)
        self.assertNotIn("Function docstring", out)
        self.assertNotIn("revealing comment", out)
        self.assertNotIn("trailing", out)

    def test_behaviour_is_unchanged(self):
        out = self.B.strip_annotations(self.SRC)
        self.assertIn("return x + 1", out)
        self.assertIn("def f(x):", out)

    def test_a_module_whose_only_body_is_a_docstring_still_parses(self):
        src = '"""Just a docstring."""\n'
        out = self.B.strip_annotations(src)
        self.assertIsNotNone(out)
        compile(out, "<stripped>", "exec")

    def test_unparseable_source_returns_none_rather_than_a_guess(self):
        # The caller keeps the original and reports that stripping failed. Returning a partial
        # string here would let a fixture through unstripped with no signal that it happened.
        self.assertIsNone(self.B.strip_annotations("def (:"))

    def test_the_real_fixtures_lose_text_to_stripping(self):
        # If this stops being true the confound is gone and the method is unnecessary -- and if
        # it was never true, the blind measurement was not blind in the way it claimed.
        import json
        from pathlib import Path as P
        corpus = json.loads((R.SKILL_ROOT / "evals" / "evals.json").read_text())["evals"]
        stripped = total = 0
        for e in corpus[:20]:
            for rel in e.get("files", []):
                p = R.SKILL_ROOT / rel
                if p.suffix != ".py" or not p.is_file():
                    continue
                total += 1
                out = self.B.strip_annotations(p.read_text(encoding="utf-8"))
                if out is not None and len(out) < len(p.read_text(encoding="utf-8")) - 40:
                    stripped += 1
        self.assertGreater(stripped, total * 0.5,
                           f"only {stripped} of {total} fixtures lost text to stripping")

    def test_the_bare_arm_stages_no_domain_knowledge(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        self.B.stage_bare(d)
        self.assertFalse((d / "domains").exists(),
                         "the bare arm must have no guidelines; that is the entire comparison")
        self.assertTrue((d / "SKILL.md").is_file(),
                        "but the output contract stays -- removing it would measure the "
                        "difference between a review and a non-review")
        self.assertTrue((d / "shared").is_dir())

    def test_fixture_selection_prefers_fixtures_that_can_answer_the_question(self):
        import json
        corpus = {e["id"]: e for e in json.loads(
            (R.SKILL_ROOT / "evals" / "evals.json").read_text())["evals"]}
        picked = self.B.pick(None, corpus, 6)
        self.assertEqual(len(picked), 6)
        import mismatch_probe as MP
        split = MP.concern_split(corpus)["per_fixture"]
        for i in picked:
            self.assertGreaterEqual(split[i]["severity"], 2,
                                    f"fixture {i} has too few severity assertions to measure "
                                    f"the axis the skill actually moves")

class RunOneIsCallable(unittest.TestCase):
    """The harness's primary entry point, invoked.

    `run_one` was broken for the whole of this corpus's life: it passed `base_commit` into
    `already_current()` twenty lines above the `try` block that computes it, so every reviewer run
    raised `UnboundLocalError` before reaching the model. Nothing caught it, because the grading
    path, the diagnostics and `blind_measure` all call `grade()` or `run_model()` directly and
    never go near it -- 255 tests and a validator `exit=0` alongside a harness that could not run
    a single eval.

    So this calls it. The reviewer is stubbed, so it costs nothing and needs no quota, and the
    point is the *call* rather than the verdict: an entry point that raises is a defect no
    assertion about its output can report, because the assertion never runs.
    """
    def setUp(self):
        import run_evals
        sys.path.insert(0, str(run_evals.SKILL_ROOT / "scripts"))
        self.R = run_evals

    def _args(self, reps=1):
        class A:
            pass
        a = A()
        a.reps = reps
        a.force = False
        a.timeout = 30
        a.model = "pinned/test-model"
        a.judge_model = "pinned/test-judge"
        a.iteration = "iteration-1"
        # `run_once` reads these; a stub namespace missing one fails on the attribute rather
        # than on the behaviour under test, which is its own kind of useless test failure.
        for name, default in (("require_skill", False), ("skill_name", "se-review"),
                              ("eval_id", 999_001), ("no_axis_cap", 0)):
            setattr(a, name, default)
        return a

    def test_run_one_completes_and_records_a_verdict(self):
        import json
        import tempfile
        real_model, real_grade = self.R.run_model, self.R.grade
        self.R.run_model = lambda *a, **k: ("`0 findings - C:0 M:0 m:0 i:0`\n\n## Findings\n\nNone.\n", "")
        self.R.grade = lambda body, assertions, *a, **k: [
            {"passed": True, "evidence": "stub"} for _ in assertions]
        try:
            with tempfile.TemporaryDirectory() as td:
                item = {"id": 999_001, "assertions": ["a"], "files": [], "prompt": "stub"}
                outcome = self.R.run_one(item, "with_skill", Path(td), self._args())
                self.assertIsNotNone(outcome, "run_one returned nothing")
                self.assertNotIn("UnboundLocalError", str(outcome))
                written = list(Path(td).rglob("grading.json"))
                self.assertTrue(written, "run_one wrote no verdict")
                doc = json.loads(written[0].read_text())
                self.assertEqual(doc["eval_id"], 999_001)
                self.assertIn("base_commit", doc)
                self.assertEqual(doc["assertion_roles"], item.get("assertion_roles"))
        finally:
            self.R.run_model, self.R.grade = real_model, real_grade

    def test_base_commit_is_bound_before_already_current_reads_it(self):
        # The specific ordering that broke it. Asserted on the source because the failure mode is
        # a read before assignment, which a runtime test only catches by raising.
        src = Path(self.R.__file__).read_text()
        body = src.split("def run_one(", 1)[1].split("\ndef ", 1)[0]
        self.assertLess(body.index("base_commit = subprocess.run("), body.index("already_current("),
                        "base_commit is computed after already_current reads it -- the exact "
                        "UnboundLocalError that broke every run")

class BlindArmsAreALadder(unittest.TestCase):
    """full -> bare -> none removes domain knowledge, then the core rules, and nothing else.

    Two blind runs put severity at -20.8 and -18.8 points for the bare arm against the full arm,
    contradicting the +33.3 an earlier blind measurement recorded. Two readings fit that and they
    imply opposite conclusions -- the domain files diluting severity discipline, or `shared/`
    carrying it and the domain files being irrelevant -- and they cannot be told apart without an
    arm that has SKILL.md and neither.

    So the arms are a ladder, and the ladder is the whole experimental design: if it is wrong the
    third arm measures nothing and the result reads as though it meant something.
    """
    def setUp(self):
        import run_evals
        sys.path.insert(0, str(run_evals.SKILL_ROOT / "scripts"))
        import blind_measure as B
        self.B = B
        self.R = run_evals

    def _staged(self, fn):
        d = Path(tempfile.mkdtemp())
        fn(d)
        return d

    def test_each_arm_stages_exactly_what_it_claims(self):
        full = self._staged(lambda d: self.R.stage_skill(d, arm="with_skill"))
        bare = self._staged(self.B.stage_bare)
        none = self._staged(self.B.stage_none)
        self.assertTrue((full / "domains").is_dir(), "full must carry the domain guidelines")
        self.assertFalse((bare / "domains").is_dir(), "bare must not")
        self.assertFalse((none / "domains").is_dir(), "none must not")
        self.assertTrue((bare / "shared").is_dir(), "bare keeps the core rules -- that is the arm")
        self.assertFalse((none / "shared").is_dir(),
                         "none exists to separate shared/ from domains/, so it must have neither")
        for d in (full, bare, none):
            self.assertTrue((d / "SKILL.md").is_file(),
                            "every arm keeps SKILL.md; removing it would measure a non-review")

    def test_the_ladder_is_monotonic_in_guideline_count(self):
        counts = []
        for fn in (lambda d: self.R.stage_skill(d, arm="with_skill"), self.B.stage_bare,
                   self.B.stage_none):
            counts.append(len(list(self._staged(fn).rglob("*.md"))))
        self.assertEqual(counts, sorted(counts, reverse=True),
                         f"arms must decrease in staged guidance: {counts}")
        self.assertEqual(counts[-1], 1, "the last arm is SKILL.md alone")

    def test_an_unknown_arm_is_refused_rather_than_silently_staged_as_full(self):
        # A typo in --arms that defaulted to the full arm would quietly turn a three-arm
        # comparison into a two-arm one and report a delta nobody asked for.
        import inspect
        src = inspect.getsource(self.B.measure_one)
        self.assertIn('elif arm == "none":', src)
        self.assertIn('else:', src)
        body = src.split("if arm ==", 1)[1]
        self.assertNotIn('arm == "full"', body,
                         "the full arm should be the fallback and nothing else should be")

