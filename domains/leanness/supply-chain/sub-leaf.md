# Supply Chain Sub-Domain Evaluator

Evaluates dependencies, manifest scoping, lockfile determinism, and what the build executes and consumes.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Manifest Hygiene** | Unbounded version ranges, dev in prod, trivial packages, confusable names | `guidelines/manifest-hygiene.md` |
| **Lockfile Integrity** | Missing lockfiles, manual edits, hash verification | `guidelines/lockfile-integrity.md` |
| **Build Integrity** | Install-time execution, mutable CI/image references, absent provenance | `guidelines/build-integrity.md` |

## Sub-domain scoring & deduction rules
- Dependency executes code at install time, or the build consumes a mutable reference: **CRITICAL** (-25 points).
- Vulnerable, abandoned, or confusion-prone dependency: **MAJOR** (-10 points).
- Unbounded upper range or missing lockfile: **MAJOR** (-10 points).
- No signature or provenance verification of consumed artifacts: **MAJOR** (-10 points).
- Minor dependency scope misplacement: **MINOR** (-3 points).
