# Phase 1 — DeepResearch

Research a target folder and return graded findings. Read this file only during Phase 1.

## Input

- Target folder: `domains/<domain>` or `domains/<domain>/<sub-domain>`.
- Goal statement: the coverage gap or theme to investigate.

## Procedure

1. **Read existing coverage first.** Load the target's `leaf.md` or `sub-leaf.md` plus every
   `guidelines/*.md` beneath it. List what is already covered. For the research class this list is
   the *only* coverage reference permitted — do not open the corpus, and see step 4.
2. **Choose a source class.** A class carries its own admission gate and disposition vocabulary.

   | class | procedure | output |
   |---|---|---|
   | Project conventions, specs, primary documentation | this step | graded findings, capped at 10 |
   | **Published engineering research** | `research-sources.md` | closed disposition set, no number |

3. **Research broadly.** Survey authoritative sources for the goal: engineering principles,
   established guidelines, design patterns, anti-patterns, and relevant design-system rules. Prefer
   primary sources over blog opinion. Record the source per finding — it is how you decide whether a
   check is real and how severe it is, and it stays in this report rather than travelling into the
   guideline.
4. **Admit, do not score.** The research class has four predicates, all of which must hold; see
   `research-sources.md`. The one that decides most items is A3, and it comes from this tree's own
   measurement: guideline text buys **+4.2 points on detection and +33.3 on severity**, so an item
   adding a defect class a competent reviewer already finds unaided is carrying cost, not coverage.
   An item that sharpens a threshold or a boundary is what this rubric is short of.

   **Coverage is searched over guidelines and axis codes only.** `evals/evals.json`,
   `evals/iteration-*/` and the per-fixture tables in `evals/README.md` are off limits to a research
   pass: `evals/README.md` names, per guideline, the exact planted defect, which is the answer key in
   prose. Coverage counts come from the gap register, which carries the numbers and no key.
5. **Convert research into review checks.** Each finding must be expressible as a reviewer check:
   what to look for, the defect trigger, and a concrete failure scenario (production outage, breach,
   corruption, or carrying cost). Research that cannot become a check is an Info note, not a finding.
6. **Grade every finding** with the blast-radius scale (`../shared/severity-and-rules.md`): Critical
   (-25), Major (-10), Minor (-3), Info (0). No grade, no advance to Phase 2.
7. **Deduplicate and cap.** Collapse findings with a shared root cause into one. Items that duplicate
   existing coverage are dropped here. Cap at 10 findings per run; keep the highest grades.
8. **Reconcile and record.** Every declared item gets exactly one disposition from its class's closed
   set, and the rows must reconcile against the declared item count:

   ```
   printf '%s\n' "$ROWS" | python3 ../scripts/research_ledger.py --rows <n>
   ```

   The script re-runs every receipt against the tree and refuses to write on any of four counts:
   reconciliation, receipt replay, anchor resolution, or a `covered` row carrying no action. **A
   record a pass is only instructed to keep will be empty** — `attempts.jsonl` is specified in two
   files and does not exist — so the disposition table is the script's *input* and there is no second
   path by which a row reaches the ledger. To omit a row you must decline to report the item, and
   then reconciliation fails and nothing is written at all.

   **No number is attached to a source, ever.** `research-sources.md` gives the reason and the
   report line that states it in this pass's own output.

## Output schema (one block per finding)

```markdown
### [GRADE] <short title>
- **Principle:** <the engineering principle or pattern/anti-pattern>.
- **Source:** <authoritative source> — provenance for this report only; do not upsert it.
- **Review check:** <what the reviewer looks for + defect trigger>.
- **Failure scenario:** <concrete production or maintenance breakdown>.
- **Suggested placement:** <guidelines/<file>.md (new|existing)>.
- **Receipt:** `<glob>::<regex>` → <n> hits · <anchor, or none>.
- **Disposition:** <one token from the class's closed set>.
- **Action:** <delete-candidate | retain-because-<threshold>> — required on `covered` and `known`.
- **Already covered:** <derivable from the receipt; never asserted without one>.
```

Findings marked already-covered do not advance. Return the blocks plus a one-line tally: `<n> findings · C:<n> M:<n> m:<n> i:<n> · <n> advancing to Phase 2`.
