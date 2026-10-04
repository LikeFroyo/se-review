# Identification — what is this project actually built with

Detection is evidence-ranked. A name matching a known technology is the weakest evidence in the list, not the first check.

## Evidence ladder

Work down the ladder and stop at the first rung that yields a determination. Cite the rung in the output.

| Rank | Evidence | Strength |
|---|---|---|
| 1 | Build or manifest declarations, resolved lock data, toolchain version pins | **Declared** — the project asserts it |
| 2 | Import/require graph, dependency resolution output | **Declared** (transitive or direct) |
| 3 | Build scripts, task definitions, CI configuration, container and infrastructure definitions | **Inferred** — the project configures it |
| 4 | Framework conventions: routing tables, ORM models, middleware registration, schema and migration directories, plugin entry points | **Inferred** |
| 5 | File extensions and shebangs, directory layout, test and config file naming | **Suggested** — evidence of a language, never of a framework |
| 6 | A name that resembles a known technology | **Suspected** — not evidence |

**Rungs 1–2 are auditable.** Rung 3–4 items are audited once confirmed by the project asserting or configuring them. Rung 5 alone establishes a *language* candidate and nothing about the stack. Rung 6 enters no report except as an open question.

## Version resolution

A technology's version is the **resolved** version, not the requested range.

1. Read the lock data or equivalent resolved-state file the project's own toolchain produces. A range or constraint is a request, not an installation.
2. If no resolved state exists, record the declared range and mark the version `unresolved` — an unresolved version blocks a currency claim, not the whole audit.
3. Where several versions of one technology coexist, record each with its owning path. A monorepo routinely runs more than one.
4. Distinguish the version the project is *pinned to* from the version the project *declares compatibility with*. Only the first is an installation fact.

## Boundaries to carve before enumerating

Decide these first, because they decide what counts:

- **Product code** — ships and runs. In scope.
- **Generated code** — produced by a tool from another source. Report the generator and the pinned version; audit the generator, not the output.
- **Vendored or third-party code** — in scope only if the project modified it, which makes the project responsible for it.
- **Scripts and tooling** — build, test, and maintenance scripts. In scope, and often where the stale pins live.
- **Fixtures, samples, documentation examples** — in scope only where a reader would treat them as authoritative.

State the boundary you used. Two runs with different boundaries produce incomparable results.

## Enumeration discipline

- Enumerate **every** category, including the ones that come back empty. An empty category is a result; an unenumerated one is a gap.
- Detect from the project, never from a list you carry in your head. If a technology is present, the project should be able to show you.
- Report what you looked for and did not find, in the categories where absence is meaningful.

## Confidence

State confidence per determination:

- **High** — declared in the project's own resolved data, and consistent across the build, the import graph, and the configuration.
- **Medium** — declared or configured, but the repository is internally inconsistent (two version pins, a lockfile that disagrees with a manifest).
- **Low** — inferred from convention or file layout only. Low-confidence determinations are reported as open questions and are **not** audited.

A Medium determination that is a *version* conflict is itself an auditable finding: a project whose lock data and manifest disagree does not have a single resolved version, and every currency claim built on it is unsafe.
