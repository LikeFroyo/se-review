# Adherence — verdicts, grading, and the boundary of this skill

Conformance is measured against the rule that applies. It is not a quality judgement, and it is not a review of whether the code is good.

## Verdicts

Every rule evaluated against the project gets exactly one verdict.

| Verdict | Meaning |
|---|---|
| **Conformant** | The project satisfies the rule as written. Cite the evidence. |
| **Non-conformant** | The project violates a normative requirement. Cite the requirement and the evidence. |
| **Behind** | The project is valid on its version line, but the steward has deprecated, ended support for, or published a security advisory against it. Cite the notice and its date. |
| **Divergent by choice** | The project deliberately differs and the deviation is documented or self-evident. Not a finding. Record it so the next run does not re-litigate it. |
| **Not applicable** | The rule does not bind this project. State why — an absent feature is a legitimate outcome, not an unchecked box. |
| **Unknown** | Could not be evaluated. State what blocked it and the attribution impact. |

**Unknown is mandatory, not optional.** Anything not evaluated is Unknown. A run with no Unknown verdicts has either a very small scope or an overconfident one; check which.

## Grading

Grade by consequence, using the same blast-radius discipline as every other se-review verdict. The scale itself is **not restated here** — the deductions, the severity conditions, and the grade bands come from [`../../shared/severity-and-rules.md`](../../shared/severity-and-rules.md), so a conformance finding and a defect finding are graded on one scale and can be counted together.

Map conformance classes onto that scale:

| Conformance class | Blast-radius condition | Lands on |
|---|---|---|
| Non-conformant, breach has a security, integrity, loss, or availability consequence | The Critical row | Critical |
| Behind on a deprecated or end-of-life line; or non-conformant with a bounded but real failure mode | The Major row | Major |
| Divergence with limited spread and low probability; documented-current version with a known operational risk | The Minor row | Minor |
| Observation, recommendation, or an unverifiable claim | The Info row | Info |

Two rules constrain grading:

- **A recommendation is not a violation.** T4 practice and T2 guidance marked as a recommendation are graded as observations, never as non-conformance. Grade the obligation the source itself states.
- **Version risk is not code risk.** Being behind is graded on the steward's own notice, not on an imagined failure. If you cannot cite a deprecation, an end-of-life date, or an advisory, it is Info.

## Severity is per root cause

Collapse every instance of one rule violation into a single finding that cites the primary site and the total occurrence count. Then report the per-site list, so the primary citation does not hide the rest.

Where two rules are violated by one change, that is two findings, one per breached rule. Report one finding per rule, or one finding citing both rules with both verdicts recorded — never a single finding carrying only the higher grade, which discards the lower breach's evidence.

## Scope and coverage

Adherence is only as good as what was read. Every report states:

- **Examined** — files, directories, and declarations actually read.
- **Not examined** — what was excluded and why (generated, vendored, out of scope by the boundary chosen in identification).
- **Sample basis** — where a category was sampled rather than read exhaustively, what the sample was and why it is representative.
- **Unresolvable** — anything that could not be read and what that costs.

Never report a category as clean because it was not opened.

## Hand-off, not overlap

This skill is not a code review. When an observation is a defect, a security hole, a design problem, or a performance problem, it is recorded as a **hand-off note** — the observation plus where it was seen — and referred out. Do not grade it, do not fix it, and do not drop it silently: a hand-off note that is never routed is a finding that was lost.

| Observation type | Belongs to this skill? |
|---|---|
| Version, specification, or standard conformance | Yes |
| Deprecated or unsupported version | Yes |
| Declared compatibility that the project does not meet | Yes |
| Configuration required by a specification is absent | Yes |
| A bug in the product code | No — hand off |
| A security vulnerability in the code | No — hand off |
| Design or maintainability quality | No — hand off |
| Formatting, naming, import order | No — a formatter owns it |
| Style preference with no specification behind it | No |

## Restraint

- A project that conforms gets a conforming verdict and a Grade A. Do not invent a rule to have something to report.
- Unclear intent is Info. If it is genuinely ambiguous whether a construct is deliberate, ask or record it as Unknown — do not resolve the ambiguity in the project's disfavour.
- A rule the project satisfies is worth recording in the profile. A profile that only lists violations loses the baseline it exists to keep.
