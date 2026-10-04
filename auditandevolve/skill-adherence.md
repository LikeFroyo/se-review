# Phase 3 — SkillAdherence

Gate every Phase 2 edit against the published skill specification and best
practices. Read this file only during Phase 3. Fail returns the edit to
Phase 2 for fix or drop — nothing advances on fail.

Sources: `https://agentskills.io/specification`,
`https://agentskills.io/skill-creation/best-practices`,
`https://agentskills.io/skill-creation/optimizing-descriptions`,
`https://agentskills.io/eval-design`.

## Core rule: what, not how

Guidelines state the check and its failure scenario, never tutorials,
implementation steps, or lengthy explanations. Verbosity is itself a failure.

- Bad: a guideline that teaches how to implement retries with code samples and configuration options.
- Good: the defect trigger (`immediate retry with no delay`), the failure scenario (thundering herd on 503), the verification (no sleep/backoff between attempts).

## Checklist (pass/fail each item per edited file)

Spec (`/specification`):

1. **Frontmatter:** `name` 1–64 chars, lowercase alnum + hyphens, no leading/trailing `-`, no `--`, matches parent directory; `description` 1–1024 chars; `compatibility` ≤500 when present; `metadata` str→str; `allowed-tools` space-separated string.
2. **Description triggers:** imperative (`Use when…`), user intent not implementation, lists contexts including unnamed ones, concise. Enforced by `scripts/validate_skill.py`.
3. **Size:** edited `SKILL.md` stays <500 lines and ~<5000 tokens; detail moves to referenced files.
4. **One-level references:** `SKILL.md` references at most `subdir/file.md`; never references `guidelines/` directly; each file states *when* to load the next (progressive disclosure).

Content (`/best-practices`):

5. **What-not-how:** check + trigger + failure scenario present; no tutorial, no how-to steps, no code samples beyond a minimal trigger quote. No `**Source:**` line, standard number, or external citation — the check states the trigger and the threshold; the citation was how the finding was justified in Phase 1, not something a reviewer needs at review time.
6. **Agent-lacks-only:** adds project-specific conventions, edge cases, APIs the agent would get wrong; omits what the model already knows. — **checked per corpus, not per edited file.** Scoped to the file Phase 2 chose to edit, this item cannot fire on the file that most needs it: one whose content the model already has, which Phase 2 never touches and Phase 3 therefore never examines. So it also runs as a sweep — for every guideline, one of {still needed · already known · unproven}, and `unproven` is reported whether or not anything was edited
7. **Coherent unit + moderate detail:** one task per file; stepwise guidance with one working example, not exhaustive edge cases.
8. **Calibrated control:** fragile sequences are prescriptive (exact command); flexible judgments explain *why*; one default with escape hatch, never a menu; reusable method, not a single-instance answer.
9. **Correct tier:** defect detail lives in `guidelines/`, checklist in `sub-leaf.md`, identity in `leaf.md` — nothing in the wrong tier.
10. **Blast-radius severity:** any severity claim matches `../shared/severity-and-rules.md`; no style or preference issue graded above Minor.
11. **Progressive disclosure:** parent files reference the new content without inlining it; a reviewer can load the checklist without loading every guideline.
12. **One-level references:** new cross-references point at most one level out (sibling guideline or parent sub-leaf); no deep chains.
13. **No linter work:** no formatting, naming-style, or import-order rules.
14. **Restraint:** unclear-intent checks are Info or dropped, never inflated.
15. **Single source of truth:** numbers, thresholds, and flag definitions are stated once (severity in `shared/`, flags in `SKILL.md` Arguments) and referenced elsewhere — never restated, where restating lets copies drift.
16. **Scripts when repeated:** logic the agent reinvented across runs ships as `scripts/` with error messages and edge-case handling.

## Verdict format

```markdown
## Adherence verdict
- <file>: PASS | FAIL — <failing item number(s)> → <fix applied or DROP with reason>
```

All PASS advances to Phase 4. Any FAIL goes back to Phase 2.
