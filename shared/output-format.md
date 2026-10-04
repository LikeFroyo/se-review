# Output format — orchestrator and standalone domain reports

All reviews must follow these structured formats. Findings are always sorted most severe first (Critical -> Major -> Minor -> Info/Suggestion).

Evidence is anchored to survive: cite `<file>` plus the symbol (function, class, flag, heading) and quote the offending lines. Bare line numbers alone rot when the file shifts, and commit ids orphan on rewrite — the symbol tells the next reader where to look. Where you ruled between two readings (e.g. doc-as-intent vs code-is-right), state the ruling in one line.

Every finding carries **how it was established**, and the value obliges the reviewer to have
done something, so the label cannot be decoration:

| `Verified by` | The reviewer must have | The reader may conclude |
|---|---|---|
| `RAN` | Executed the reproduction, or run the project's own checks and observed the failure | The failure was observed, not argued. |
| `DERIVED` | Traced the path statically and can name the chain of sites that produces the failure | The failure follows from the code as written. |
| `READ` | Read the cited sites and judged. No execution, no completed trace | A plausible reading, unconfirmed. **The default when unmarked.** |

Name the execution, or the trace, in the finding — `RAN` without saying what was run, or
`DERIVED` without the chain, is not that value and is downgraded to `READ`. A `READ` finding may
be Critical; it is simply one the reader can discount by the weight of the evidence. **This field
changes no grade and no cap.** It is an honesty feature, not an accuracy feature: it reports the
reviewer's epistemic position rather than improving it, and nothing here should treat `READ` as
disqualifying.

A fix covers every cited instance: repeat instances collapse to one root cause for reporting, but the fix addresses all sites, not just the primary — fixing one and leaving two is the ordinary failure.

`<Axis Code>` is a code from `axis-codes.md`, which is the single source of truth: `A1`–`A8` correctness, `B1`/`B2`/`B4`/`B5` maintainability, `C1`–`C8` operations, `D1`–`D4` interoperability, `L1`–`L6` leanness. A defect that fits no listed axis is reported with no code, tagged `UNCLASSIFIED`, and counted in a header field — never dropped, and never given a plausible-looking invented code, which sends the reader to a guideline that does not discuss their defect.

**The header count is the size of the uncoded population, and it is printed at every value including
zero.** `Unclassified: 0` is a result: the reviewer raised findings and every one fit a registered
axis. A report with no `Unclassified:` line says something entirely different — that nothing was
recorded — and `eval_diagnostics.py` reads those as different states, because a total computed over
reviews where the count is missing would claim *measured, and nothing found* about runs where
nothing was measured.

**Every agent's `fits-no-axis` return increments this count** — see the dispatch preflight in
domain-fanout.md. The token exists so the orchestrator has something to count; without that link the
population is sized by nobody, which is the condition `axis-codes.md` says leaves a reserved code
unreviewable: *a reserved code with no periodic review is a defect nobody can size, and it cannot be
sized if nothing records its occurrences.*

---

## 1. Full orchestrator report format (multi-domain)

Use when reviewing across all software engineering pillars:

```markdown
# Review: <scope>

`<n> findings · C:<n> M:<n> m:<n> i:<n> · Mean <score>/100 · Final Grade <A-F>`
Covered: <examined>/<in-scope> files · Scope: <whole tree | diff | focused on: <paths>> · Not examined: <n> — <reason, or `none` at zero>
Paths: <resolved open | n> · Unmapped: <n> — <crossings nothing could reach or classify>
Unclassified: <n> findings fit no axis code
Domain Scores: <Domain1>: <score>/100 · <Domain2>: <score>/100 · ... (for all evaluated domains)
Gated by: <`Critical finding` | `weakest domain: <Domain>` | `neither — <highest grade reached>`> — **always printed.** A header missing this line is indistinguishable from a truncated report, and absence must never read as "no cap bound".

**Every header line is a fixed slot, printed at every value including zero.** A field printed only
when it binds teaches the reader that absence means clean, and a truncated report then reads as a
whole one. That is the one failure this format exists to prevent.

`Covered` is the denominator the score cannot hide behind: `in-scope` is the surface the flags
selected, and the score is computed over a subset of a report that says so.

**`Paths:` and `Unmapped:` are printed on every report that includes the security domain, including
at zero.** An open path is not a finding and an unmapped crossing is not a defect, so neither
appears in the `C/M/m/i` tally — and both are exactly what a reader needs before trusting a clean
security line. A report carrying a security line and neither field is internally inconsistent, in
the same way a partial entry-point list beside a zero `unmapped` is. `Unmapped` is the security
equivalent of `Not examined`: the number that can grow while the score stays flat.

| Flag | `in-scope` becomes | Effect on `Covered` |
|---|---|---|
| *(none)* · `--full` | the whole project-authored tree | `Not examined` is 0 only if it truly was |
| `--diff-only` | changed files only | denominator shrinks; say `Scope: diff`, never imply a tree review |
| `--focus <paths>` | those paths | denominator shrinks to them |
| `--min <severity>` | unchanged | drops *findings*, not coverage — disclosed under the cut policy, never here |

At zero the reason is the word `none`, never an empty dash. A trailing `—` with nothing after it
implies a reason was withheld, which is the same defect as omitting the field: absence that reads
as concealment rather than as absence. Observed on a live run, where the reviewer wrote
`Not examined: 0 —` and stopped.

When context, cost, or access prevented covering the declared scope, `Not examined` is non-zero and
the reason is stated in the header. **A partial review presented as a whole one is a false report**,
and the score of an incomplete sweep means only that of the part swept.

## Findings

### [CRITICAL] <short title describing root cause>
- **Domain:** <Domain name> (<Axis Code>)   -- one code, bare, as `(A1)`. Never backticked,
  never two codes inside one parenthesis group, and never omitted. A code a reader cannot
  resolve is a finding the axis registry cannot be shown to cover: measured over the stored
  corpus, 5 of 50 findings carried a Domain line that no strict reader resolves -- 2 wrapped
  the code in backticks, 1 put two codes in one group, and 2 omitted the line entirely,
  including a CRITICAL. The format is the only thing between a finding and the no-axis
  population, so a variance here is not cosmetic.
- **Verified by:** `RAN` | `DERIVED` | `READ` — what was run, or the trace chain.
- **Evidence:** `<file>:<lines>` — quote offending lines or describe structure.
- **Failure scenario:** Concrete breakdown in production, state corruption, or permanent carrying tax.
- **Fix:** Concrete change proposed (deletion for Leanness; code refactor for others), naming its scope: local, module, boundary, or codebase.
- **Trade-off:** What the proposed fix costs at that scope (not required for deletions).

### [MAJOR] <short title describing root cause>
- **Domain:** <Domain name> (<Axis Code>)   -- one code, bare, as `(A1)`. Never backticked,
  never two codes inside one parenthesis group, and never omitted. A code a reader cannot
  resolve is a finding the axis registry cannot be shown to cover: measured over the stored
  corpus, 5 of 50 findings carried a Domain line that no strict reader resolves -- 2 wrapped
  the code in backticks, 1 put two codes in one group, and 2 omitted the line entirely,
  including a CRITICAL. The format is the only thing between a finding and the no-axis
  population, so a variance here is not cosmetic.
- **Evidence:** `<file>:<lines>` — code quote or structure description.
- **Failure scenario:** Observable defect, performance cliff, race condition, or testing obstruction.
- **Fix:** Concrete implementation change, naming its scope: local, module, boundary, or codebase.
- **Trade-off:** Engineering cost at that scope, latency delta, or complexity added.

### [MINOR] <short title>
- **Domain:** <Domain name> (<Axis Code>)   -- one code, bare, as `(A1)`. Never backticked,
  never two codes inside one parenthesis group, and never omitted. A code a reader cannot
  resolve is a finding the axis registry cannot be shown to cover: measured over the stored
  corpus, 5 of 50 findings carried a Domain line that no strict reader resolves -- 2 wrapped
  the code in backticks, 1 put two codes in one group, and 2 omitted the line entirely,
  including a CRITICAL. The format is the only thing between a finding and the no-axis
  population, so a variance here is not cosmetic.
- **Verified by:** `RAN` | `DERIVED` | `READ`
- **Evidence:** `<file>:<lines>`
- **Fix:** Localized cleanup.

### [INFO / SUGGESTION] <short title>
- **Domain:** <Domain name> (<Axis Code>)   -- one code, bare, as `(A1)`. Never backticked,
  never two codes inside one parenthesis group, and never omitted. A code a reader cannot
  resolve is a finding the axis registry cannot be shown to cover: measured over the stored
  corpus, 5 of 50 findings carried a Domain line that no strict reader resolves -- 2 wrapped
  the code in backticks, 1 put two codes in one group, and 2 omitted the line entirely,
  including a CRITICAL. The format is the only thing between a finding and the no-axis
  population, so a variance here is not cosmetic.
- **Verified by:** `RAN` | `DERIVED` | `READ`
- **Evidence:** `<file>:<lines>`
- **Fix:** Recommendation or observation.

## Aligns well
- <Positive engineering pattern observed, citing axis code>
- <Positive engineering pattern observed, citing axis code>
```

---

## 2. Standalone domain report format (independent execution)

Use when a domain is executed independently (e.g. `--domain <name>` or running `domains/<domain>/leaf.md`):

```markdown
# <Domain> Review: <scope>

`<n> findings · C:<n> M:<n> m:<n> i:<n> · Domain Score: <score>/100 (Grade <A-F>)`
Covered: <examined>/<in-scope> files · Scope: <whole tree | diff | focused on: <paths>> · Not examined: <n> — <reason>
Paths: <resolved open | n> · Unmapped: <n> — <crossings nothing could reach or classify>

## Findings
... [Same finding structure as above] ...

## Aligns well
- <Positive domain observations>
```

---

## 3. Standalone sub-domain report format (independent execution)

Use when a sub-domain is executed independently (e.g. running `domains/<domain>/<sub-domain>/sub-leaf.md`):

```markdown
# <Sub-Domain> Review: <scope>

`<n> findings · C:<n> M:<n> m:<n> i:<n> · Sub-Domain Score: <score>/100 (Grade <A-F>)`
Covered: <examined>/<in-scope> files · Scope: <whole tree | diff | focused on: <paths>> · Not examined: <n> — <reason>
Paths: <resolved open | n> · Unmapped: <n> — <crossings nothing could reach or classify>

## Findings
... [Same finding structure as above] ...
```

---

## Evolution candidates
- <one-line observation> — seen in <n> run(s), <scope> — rubric gap: <guideline or domain> — evidence: <finding id>

Only when there are candidates. Never a file, never an edit, and never read by a
judge or a subagent — see `shared/evolution-candidates.md`. Omit the section
entirely rather than printing an empty one.

## Cut policy

Cap reports at 15 findings maximum. **The number is coupled, not chosen for comfort:** 15 is
the suppression ledger's printable row count and the run-wide probe cap, and a finding above
it would enter the ledger with no row to print, no evidence classes recorded against it, and
no way back. Fatigue is a real cost at the margin but it is not the reason, and quoting it as
the reason invites someone to raise the cap and break the coupling. See the knob table in
`project-tree/shared/deliberate.md` for the derivation.

Keep all Critical and Major findings, in that order; cut from the bottom.

**Disclose the cut with its real composition, never an assumed one.** The old template asserted
the cut was "all Minor or Info" — a false statement precisely when it matters, since when the
surplus is Critical there is no Minor left to cut and the note invents a composition to excuse
itself. Compute the cut from what was actually dropped:

```
Cut by 15-cap: <n> findings (C:<n> M:<n> m:<n> i:<n>) on axes <X, Y>.
```

**Every cut Critical and Major is stubbed**, even though its full entry is not shown. A reader who
sees 15 findings and no note cannot tell there were 40; a reader who sees a stub knows to go looking.

```
- [CRITICAL] <title> — <file>:<lines> (<Axis Code>)
```

**The cut reconciles.** `shown + stubbed + dropped == raised`, where `raised` is the number of
findings the review produced before the cap and `dropped` is the sub-stub tail the stubs do not
account for. A section whose parts do not sum to its own total is wrong, and the reader cannot tell
which part is wrong: two of the three are printed and one is derived. State the total, state which end
was cut (the bottom, at equal severity the later-listed), and let the reader check the arithmetic. This
is the same rule as the coverage denominator, applied to the finding count instead of the file count:
a number nothing can reconcile against is a number nothing can check.

Never stub at or below `--min`: the reader asked not to be shown those, so naming them would
override their own filter. The stub rule is about *silence*, not disclosure — `--min` already
discloses itself.

**`--min` and the cap are different things and are reported with different verbs.** The cap is the
orchestrator's triage; `--min` is the reader's filter. Conflating them tells the reader the skill
chose not to report something it was asked to report:

```
Excluded by --min <severity>: <n> findings (C:<n> M:<n> m:<n> i:<n>).
```

Both lines print when both apply. Neither is ever omitted for being empty in a way that reads as
"nothing was dropped" — print `0` instead.

Exception: under `--full` whole-tree audits there is no cap — a cap would silently drop findings from entire areas. Report every root cause, most severe first; the 15-cap applies to `--diff-only` reviews.
