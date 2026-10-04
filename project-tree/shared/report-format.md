# Report format

One report per phase, plus a profile update. The header is a single line so runs can be compared.

## Phase report

```markdown
# project-tree Phase <n> — <scope>

`<technology> · <resolved version> · <conformant>/<evaluated> conformant · C:<n> M:<n> m:<n> i:<n> · Score: <score>/100 (Grade <A-F>)`

Phases 1 and 2 only. Phase 3 has no score and uses its own header, below.

## Determinations
- <technology> — <resolved version> — <confidence> — evidence: <file:line> (<evidence rung>)

## Coverage
- Examined: <paths, declarations>
- Not examined: <paths> — <reason>
- Sampled: <category> — <sample> — <why representative>
- Unresolvable: <item> — <attribution impact>

## Rules
- Conformant: <n> · Non-conformant: <n> · Behind: <n> · Divergent: <n> · N/A: <n> · Unknown: <n>

## Findings
- [<GRADE>] <rule> — <file:line> — <requirement, source, tier> — <consequence> — <fix>

## Behind
- <technology> — pinned <version>, current <version> — <notice> (<date>) — <migration path> — <cost>

## Unknown
- <rule> — <what blocked evaluation> — <what the gap does to the verdict>

## Hand-off
- <observation> — <file:line> — <referred to>

## Profile
- <profiles/<name>.md> — created | updated | unchanged
```

## Grades

- **A (90–100)** conforms, or diverges only by documented choice.
- **B (80–89)** conforms with Info-level currency risk.
- **C (70–79)** bounded non-conformance or a supported version with advisories.
- **D (60–69)** deprecated or unsupported version in the critical path.
- **F (<60)** normative violation with a security, integrity, or availability consequence, or a version the steward has ended support for.

## Phase 3 report — intent and behaviour

No score. Phases 1 and 2 grade the project against a specification; Phase 3 has no
specification to grade against — it establishes one. A score here would measure the audit
and be read as a measure of the project, which is exactly the confusion this section exists
to prevent.

```markdown
# project-tree Phase 3 — <scope>

`<capabilities> · <claims> claims · verified:<n> contradicted:<n> unverified:<n> · claimed:<v+c> of <ep> entry points <p>% · unmapped:<n> · uncovered:<n> · packages <n>`

The denominator is entry points, never claims. A claims denominator is the run's own output, so it
cannot fall without the run looking harder — which is exactly backwards.

## Structure
- Entry points: <what work arrives where>
- Modules: <module — what it owns — what depends on it>
- Seams: <process · service · store · queue · file · trust boundary>

## Capabilities
- <capability> — <entry point> — <owning module> — <seams crossed>

## Contract
- <claim id> · <evidence class> · <confidence> — <what must be true>

## Provenance of intent
- Documentation considered: <n> · cleared the relevance gate: <n> · adopted: <n> — <sources, or "self-discovery only">
- Prose contradicted by the implementation: <n> — <handed off as drift>

## Verification
- <claim id> — verified | contradicted | unverified — <technique> — <trace, or what blocked it>
- entry point <id> — uncovered — <no claim reached a verdict: why>

## Contradictions
- <claim id> — <expected> — <actual> — <evidence> — <referred to>

## Coverage
- Verified: <n> · Contradicted: <n> · Unverifiable: <n> — <reason>
- Not examined: <paths> — <reason>
- Packages: <n> vertical · <n> horizontal · <n> boundary · overlap: none

## Hand-off
- <observation> — <file:line> — <referred to>

## Artifacts
- intent/<capability>.md — created | updated | unchanged
```

**Rules for this report.**

- Coverage is a measure of the audit. Never present it as a quality score, and never combine
  contradicted with unverified into one number — they measure different things.
- `unmapped` and `uncovered` are always printed, including at zero. A report with neither, beside a
  partial entry-point list, is internally inconsistent.
- `unverified` is always listed with its reason. A report with none and a partial coverage
  list is internally inconsistent.
- A contradiction carries the claim, both sides of the evidence, and the trace, so the
  receiving review does not re-derive the intent.
- State provenance of intent explicitly. A run that silently used documentation is a run
  whose conclusions cannot be weighed.

## Rules for the report

- One line per determination, one line per finding, sorted Critical → Major → Minor → Info. Cap at 15 findings; the profile carries the rest.
- The header is the only place a score appears. Do not restate a score per section.
- `Unknown` is always listed. A report with an empty Unknown section and a partial coverage list is internally inconsistent — one of them is wrong.
- Cite `file:line` for every project-side claim and a retrievable source for every rule-side claim. A finding with only one of the two is not a finding.
- State the date. A conformance report without a date cannot be re-evaluated.
- Never state a technology, language, framework, or vendor that detection did not establish. Including one from prior knowledge is a defect in the report, not a useful detail.

## Re-run report

When re-running, add:

```markdown
## Delta
- Added: <technology>
- Removed: <technology>
- Version moved: <technology> <from> → <to> — <notice> — <consequences>
- Rules changed: <rule> — <what changed> — <source, date>
- Carried forward unchanged: <n> rules
- Re-evaluated: <n> rules
```

When nothing moved, say so in one line and stop. A re-run that rewrites unchanged findings is noise, and noise destroys the signal the baseline exists to provide.
