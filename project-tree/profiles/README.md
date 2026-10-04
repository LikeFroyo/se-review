# Profile contract

A profile records which rules apply to this project and whether it meets them. It is written for the human who reads it next, not for a later run to diff against.

One profile per technology. Name the file after the technology as the project's own tooling names it, lowercased with hyphens (`profiles/<technology>.md`). Never name a profile after a technology the project does not use.

**A profile may outlive its run** because its binding is external and re-fetchable: the steward's
specification page is fetched again and compared, byte for byte, rather than trusted because a
date says it was once checked. Everything in the profile derives from that fetch. A stored date
is a hint about where to look, never the answer, and a claim with no re-fetchable source behind
it does not belong in a profile.

## Required sections

```markdown
# <technology> — <one-line role in this project>

## Identity
- Steward: <the normative body>
- Normative source: <tier T1> — <title> — <version or publication it describes>
- Official reference: <tier T2> — <locator> — <version line>
- Currency source: <tier T3> — <locator> — <date checked>
- Project resolved version: <version> — evidence: <file:line>
- Version line current as of: <date> — <version>
- Support status: supported | deprecated <date> | end-of-life <date> | unknown

## Determination
- Detected via: <evidence rung, per ../shared/identification.md>
- Confidence: high | medium | low
- Boundary: <what is in scope for this technology>

## Ruleset

| # | Rule | Source | Tier | Obligation | Consequence if violated |
|---|---|---|---|---|---|
| 1 | <what the project must or should do> | <retrievable source> | T1 | must | <what breaks> |

## Conformance

| Rule | Verdict | Evidence |
|---|---|---|
| 1 | conformant | <file:line> |
| 2 | non-conformant | <file:line> |

## Currency
- Pinned <version>; current <version>
- <deprecation or advisory notice> (<date>)
- Migration path: <ordered steps, coexistence requirements> — cost: <what it costs>

## Hand-off
- <observation> — <file:line> — <referred to>

## Re-check triggers
- <the condition that makes this profile stale>
```

## Rules for writing one

- **Conformant verdicts are mandatory.** A table of violations only is not a baseline. Record what the project gets right, so the next run can tell a regression from a standing condition.
- **Cite both sides.** Every rule carries a retrievable source; every verdict carries a project-side `file:line`. One without the other is not an entry.
- **Record the obligation's own strength.** If the source says *should*, the profile says *should*. Promoting a recommendation to a requirement here is how a compliance report starts crying wolf.
- **Date the currency section.** Without a date, "current as of" is meaningless and a re-run cannot tell what moved.
- **Keep it flat.** No cross-profile links to other profiles' internals — reference the profile, not its contents. Deep reference chains rot.
- **No style rules.** A profile records conformance, not preferences.
- **Re-check triggers are the point.** Name what would invalidate this profile — a version bump, a deprecation notice, a steward change — so a human knows where to look first. Note that no index is kept over these profiles: a self-authored table of which profiles exist is itself a thing that rots silently, and a capability missing from such a table is one whose claims are never re-verified.
- **Neutrality.** A profile may name technologies freely. Only this skill's own files stay stack-blind.
- **One finding per root cause.** Collapse repeat instances into a single row with an occurrence count, and list the sites below the table.

## Updating

On a re-run, diff before writing:

- Version moved → update Identity and Currency, re-run every rule whose obligation text changed.
- Notice published → update Support status, re-grade the affected rows.
- Rule text changed → update the Ruleset row and every dependent verdict.
- Nothing moved → do not rewrite the file. Say "unchanged" in the report and leave the bytes alone.

A profile rewritten without cause is a profile whose diff can no longer be trusted, and the baseline stops being evidence.
