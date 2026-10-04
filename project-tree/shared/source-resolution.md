# Source resolution — finding the current rule, not the remembered one

Every rule in a profile must be traceable to a source that was actually fetched, at a version that was actually checked. This file is the procedure that makes that possible for a technology the skill has never heard of.

## Source tiers

Rank every source. The tier decides how a rule is graded, and a rule may not be promoted above its source.

| Tier | Source | Authority |
|---|---|---|
| **T1 — Normative** | The standard or specification itself: a published specification, a language reference defined by its steward, a published protocol definition, a normative standard from a recognised body | Authoritative for what *is* required |
| **T2 — Official** | The steward's or vendor's own versioned documentation, reference manual, and migration guides | Authoritative for intended practice within its version line |
| **T3 — Currency** | Official release notes, changelogs, deprecation and end-of-life notices, security advisories, published roadmaps | Authoritative for *what changed and when*; never for design intent on its own |
| **T4 — Maintained community** | Independently maintained practice guides and recognised security or style references, where the steward publishes none | Authoritative for advice, never for conformance |
| **T5 — Everything else** | Discussions, opinion, tutorials, unenumerated third-party summaries, and your own prior knowledge | **Never a basis for a finding.** Use it to find a source, then go to the source |

## Resolution procedure

1. **Find the steward.** The language or technology is specified by exactly one normative body. Locate it from the project's own documentation, the technology's own site, or its package metadata. Do not guess the steward.
2. **Locate the specification for the pinned version line.** Specifications are versioned, and current documentation routinely describes behaviour the pinned version does not have. If the specification is unversioned, treat the current publication as normative for the *current* line and record that the project is behind.
3. **Establish currency separately.** Determine the current published version and date, and any deprecation or removal notice affecting the pinned version. This is a T3 step and it is not optional — currency is the single most common finding this skill exists to produce, and it cannot come from T1 or T2 alone.
4. **Find the conformance obligations.** Extract the requirements expressed as obligations — the specification's own normative keywords, or its equivalent status markers. Record the obligation's own strength; do not restate it more strongly than the source does.
5. **Find the official migration path.** If the pinned version is behind, the steward's own migration guidance is the source for both the required change and its cost.
6. **Record the fetch.** Every rule stores: source, tier, version or publication the source describes, and the date it was retrieved. A rule without a retrievable source is not a rule.

## Currency rules

- **Never review against a remembered version.** Past knowledge of what a technology requires is a hypothesis. Fetch, then assert.
- **A pin is not a version.** A version range admits future behaviour, so a project on a range has no knowable resolved version until resolution runs.
- **Pinned behind is not the same as non-conformant.** A project pinned to a supported older version is conformant. It becomes a finding only when the steward has deprecated or ended support for it, or when a security advisory names it.
- **Detect the removal, not just the addition.** Upgrades break code at the removed thing. A ruleset that only tracks new features will call a project conformant right up until the upgrade that removes its dependency.
- **Date every claim.** A conformance baseline without a date cannot be re-evaluated later, because the rules move underneath it.

## Handling disagreement between sources

- T1 outranks T2, which outranks T3, which outranks T4.
- Where T1 and T2 conflict, the specification governs and the divergence is itself reportable — a project's own tooling documenting behaviour the specification does not permit is a real conformance question.
- Where only T4 exists, rules are recorded as recommendations, never as requirements, and are never graded as violations.
- Where sources cannot be reached, record the gap as **unknown**, never as compliant.
