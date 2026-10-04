# Phase 1 — Language

Establish what language the project is implemented in, find the current rules for that language, and check the project against them. Gate for Phase 2.

Load `shared/identification.md` for step 1, `shared/source-resolution.md` for step 2, `shared/adherence.md` and `shared/report-format.md` for steps 3 and 4.

## Step 1 — Identify the language

Apply the evidence ladder in `shared/identification.md`.

1. Walk the ladder. A language is determined by its own toolchain declaration or resolved data wherever the project has one; file extensions and layout are rung 5 and are never sufficient on their own.
2. Resolve the version from resolved lock data or the toolchain's own version pin. A version range is not an installation. Mark `unresolved` when no resolved state exists and carry that into step 2.
3. Carve the boundary: product code, generated code, vendored code, scripts and tooling, fixtures and examples. Record the boundary used.
4. Enumerate **every** language present, including ones that appear in a minority of the tree. A polyglot project is audited per language, and the boundary decides which of them is in scope.
5. Record each determination with its evidence citation, its evidence rung, and its confidence.

**Do not start step 2 for a Low-confidence determination.** Report it as an open question and move on.

## Step 2 — Research the language

This is the deep research. It is specified as a fixed agenda so that two runs produce comparable rulesets and so that a re-run can tell what changed.

1. Find the steward and the normative reference for the pinned version line, per `shared/source-resolution.md`.
2. Establish currency: the current published version, and any deprecation, removal, or end-of-life notice touching the pinned version. Record dates.
3. Work the agenda. For each item, record rules that carry a source, a tier, and the source's own obligation strength. Items that yield no rule for this project are recorded as assessed-and-clear, not dropped.

### Research agenda

| # | Question | Typical rules it produces |
|---|---|---|
| 1 | What is the current version, and what happened to the pinned one? | Support status, deprecation, removal, migration path |
| 2 | What does the normative reference require of a conforming implementation? | Reserved identifiers, observable semantics, ordering and evaluation guarantees, required behaviour |
| 3 | What does the version's own reference document guarantee? | Standard-library surface, undefined versus unspecified behaviour, implementation-defined points |
| 4 | What is the memory and concurrency model? | Data-race definition, atomicity guarantees, what is safe without synchronisation, what must be synchronised |
| 5 | What is the error and termination contract? | Required propagation, resource cleanup on unwinding, what must not be swallowed, exit behaviour |
| 6 | What is the type system's normative boundary? | Where casts or escapes are defined, what is undefined, what a conforming program may not rely on |
| 7 | What does the toolchain require? | Minimum toolchain version, required build settings, module resolution and declaration requirements |
| 8 | What is being removed? | Features the next version deletes or changes, so the upgrade cost is known before it is paid |
| 9 | What is the compatibility policy? | What the steward promises to preserve, and what it reserves the right to change |
| 10 | What is the module and dependency contract? | Resolution rules, transitive-dependency obligations, vendoring and redistribution terms |

Agenda items 5, 6, 8, and 10 are the ones most often skipped and the ones that most often carry a real finding. Do not skip them.

## Step 3 — Adhere

1. Select scope using `shared/identification.md`'s boundary. Read toolchain declarations, build configuration, module manifests, and the module graph **first** — they carry the highest conformance signal per byte.
2. Sample rather than read exhaustively where a category is large, and record the sample and why it is representative. Configuration and declarations are read exhaustively; usage sites are sampled.
3. Evaluate every rule. Record a verdict per rule from `shared/adherence.md`, including Not applicable and Unknown.
4. Collapse per root cause; sort by grade; cap the report at 15 findings.
5. Route non-conformance observations that are actually defects out as hand-off notes.

## Step 4 — Write the language profile

Write or update `profiles/<language>.md` to the contract in `profiles/README.md`. No index is kept
over these profiles: a list of which ones exist is something a reader has to keep current, and a
technology missing from that list is one whose conformance is never re-checked while nothing looks
wrong. Re-detect the set from the tree every run.

The profile must carry, at minimum: the steward, the normative source and the version it describes, the resolved project version, the currency position with dates, the ruleset with per-rule source and strength, and the project's conformance state per rule — **including the rules it satisfies**. A profile of violations only is not a baseline.

## Gate to Phase 2

Phase 2 may start when all of the following hold:

- [ ] Every in-scope language has a profile with a resolved (or explicitly unresolved) version.
- [ ] Every ruleset entry carries a retrievable source, a tier, and its obligation strength.
- [ ] Currency has been established — current version, deprecation status, and the date both were checked.
- [ ] Every detected technology has a profile, or is recorded as unaudited.

If a language has no profile, Phase 2 may still enumerate components, but every component that depends on that language's toolchain is reported as **unaudited** until the profile exists. Do not quietly audit a component against a ruleset you could not resolve.
