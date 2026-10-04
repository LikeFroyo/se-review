# Phase 2 — DeepUpsert

Turn Phase 1 findings into file edits. Read this file only during Phase 2.

## Input

- Graded findings advancing from Phase 1 (ungraded or already-covered findings are not input).

## Decision per finding

| Verdict | Condition | Action |
|---|---|---|
| **Insert** | Check fits no existing guideline file | Create `guidelines/<name>.md`, add its row to the parent `sub-leaf.md` table |
| **Update** | Check extends an existing guideline | Append a section to that file; do not rewrite it |
| **Drop** | Duplicate, linter territory, style-only, or ambiguous intent | Log `DROP — <finding> — <reason>`; make no edit |
| **Delete** | The file states something the model already knows, or the finding proves a section unearned — carrying cost with nothing it catches | Log `DELETE — <path> — <finding> — <what proved it unearned>`. The proof procedure is `shared/severity-and-rules.md § Leanness override`, and its exclusions apply unchanged: rarely used is not dead, and a retiring path is a human decision |

## Placement rules

- Guideline files hold defect triggers, failure scenarios, and verification steps — one concern per file.
- `sub-leaf.md` holds the checklist and the guidelines table — add a row only when adding a file.
- `leaf.md` holds domain identity and the sub-domain table — touch it only when adding a sub-domain or guideline area that changes the table.
- Mirror the existing file voice: headings, trigger-first layout, and the shared severity vocabulary.

## Edit rules

- Every edit cites its finding (`<title> [<grade>]`); an edit without a finding is reverted.
- Minimal diffs: change only what the finding requires. Never reformat, rename, or "improve" unrelated text.
- One finding per root cause: if two findings land in one file, keep them as separate sections, not merged prose.

## Output

List each applied edit as `<file> — <finding title> [<grade>] (insert|update)`, followed by the DROP log. This list is the input to Phase 3.
