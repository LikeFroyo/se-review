I'll read that file.
Let me get context on how this fixture is used.
Now I understand: this is eval fixture #45. Let me load the skill's own rubric for this domain plus the expected assertions.
I have the full picture. This is eval fixture #45 (`Leanness / Waste`, axis L4). Here's the review, run through the repo's own rubric.

---

# Waste Review: `evals/fixtures/vendored_fork.py`

`2 findings · C:0 M:1 m:0 i:1 · Sub-Domain Score: 90/100 (Grade A)`

## Findings

### [MAJOR] Three un-synced in-tree upstream forks, frozen 2019, two with unpatched CVEs
- **Domain:** Leanness / Waste (L4)
- **Evidence:** `vendored_fork.py` → `VENDOR_MANIFEST` (lines 5–9) pins `pyjwt` 1.7.1, `idna` 2.8, `chardet` 3.0.4, all at `synced_through: "2019-08-14"`. `UPSTREAM_LATEST` (lines 11–15) — the file carries its own drift evidence: 2.10.1 / 3.10 / 5.2.0. `KNOWN_UNPATCHED` (lines 19–22) names `("pyjwt","CVE-2022-29217")` (< 2.4.0) and `("idna","CVE-2024-3651")` (< 3.7) — both pins sit below their fix. `vendor_issue_counts()` (lines 25–27) returns `0` for all three. `encode_jwt` (line 32) imports in-function — `import jwt  # resolves to vendor/pyjwt` — so the shadowing happens at the call site and is invisible to a reader.
- **Failure scenario:** Because these are in-tree `vendor/` copies rather than manifest entries, no dependency scanner or CVE feed can match them: Dependabot, `pip-audit`, Snyk and `safety` all key off declared dependencies, and these are declared nowhere. Every upstream fix must be hand-ported by a human who first has to learn the fix exists. `chardet` is the sharper case — two major versions of drift, no CVE listed, and therefore no known bound on what was missed. The copies have now been frozen **over seven years** (2019-08-14 → today), the gap stays invisible until an audit happens to read this file, and the "just in case" retention rationale has produced a permanent carrying cost on every future security response.
- **Fix:** Delete `vendor/` and declare all three as real dependencies pinned to current versions — the in-tree copies carry no recorded local patch, and `upstream: "jwt"` says the code is an unmodified copy, so there is nothing here a package cannot express. **Scope: codebase.** Fix must cover both sites: the manifest *and* `vendor_issue_counts()` (lines 25–27), which hardcodes `0` rather than reading any tracking system — it would keep reporting "no issue" even after one was opened.
- **Trade-off:** Not required for a deletion, but the honest cost is unknown rather than zero: the file records no divergence from upstream, so if the fork *was* patched locally, that patch is undocumented and the port cost cannot be scoped from here. Confirm that before deleting.

### [INFO / SUGGESTION] Hardcoded HS256 signing key in `encode_jwt`
- **Domain:** Correctness / Security (A5) — **hand-off, not graded here.** Surfacing it rather than dropping it; it belongs to a different domain than the defect above.
- **Evidence:** `vendored_fork.py` → `encode_jwt` (line 34) — `jwt.encode(payload, "shared-signing-secret", algorithm="HS256")`.
- **Fix:** Left as-is deliberately: `"shared-signing-secret"` reads as an obvious placeholder, not a demonstrated live credential, and inflating it would be an unclear-intent call. Worth noting for the real-world case: HS256 is symmetric, so any party able to *verify* a token can also *mint* one — a design property worth revisiting if this pattern reaches production.

## Ruling
`vendor_issue_counts()` is **not** filed separately as dead code (L1): dead code requires proof of death, and a hardcoded-constant smell is not proof. It is cited as a second site the L4 fix must cover.

## Grade
**MAJOR, not CRITICAL** — deliberately, and by the rubric rather than by judgement. `domains/leanness/waste/sub-leaf.md:17` requires proof of death before grading an L1–L4 finding Critical; these copies are live, not dead. Line 19 of the same file names the case directly: *"an un-synced vendored fork: MAJOR (-10 points)"*. Score: 100 − 10 = **90/100 (Grade A)**.