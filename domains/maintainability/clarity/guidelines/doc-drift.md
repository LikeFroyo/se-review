# Documentation drift — stale comments, docstrings, and doc files

Audit every documentation claim against its current source of truth. The code is the authority on what *is*: a statement describing current behavior survives only if it can be reproduced from the source. Where the doc states intent or contract — what *should be* — the mismatch may be a code defect; report both readings instead of rewriting the doc to match the bug. (Commented-out code is not drift — it is dead code, covered under Leanness L1.)

## What to look for

- **Stale comments contradicting code:** A comment asserting behavior the code no longer has — wrong limits, renamed symbols, replaced algorithms, moved logic the comment still points at. Includes conflicting comments where two comments assert opposite behavior.
- **Docstring drift:** A docstring documenting parameters, returns, or behavior the signature no longer has — or omitting new ones. Check `Args`/`Returns` against the actual signature, not against intent.
- **Doc-file drift:** README, setup, the repository's agent-instruction file, or usage docs claiming commands, scripts, flags, paths, routes, or env vars that no longer exist in the repo. Docs are a cache of the codebase; an invalidated cache entry misleads users and agents.

## Verification

- Reproduce each claim from the source: the comment from the adjacent code, the docstring from the signature, the doc-file statement from repo facts (manifest scripts, CLI definitions, file paths). Counts and totals are re-measured from the source, never quoted from another doc.
- A reference that resolves is not proven: read the target and confirm it says what the claim asserts — a path, section, or symbol pointing at the wrong place is drift even though nothing is missing.
- Where intent is unclear, use history: code changed without a matching doc change in the same diff is drift until proven otherwise.
- History stays history: changelogs, release notes, and records of past states are exempt — correct one only if it is false about the past.
- Repair at the smallest scale that makes the doc true: patch the changed detail, delete claims about removed code, rewrite only when most of the file is stale.
