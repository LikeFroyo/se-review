# Intent — establishing what the project is supposed to do

Load for any Phase 3 step that produces or grades an intent claim.

## Why this cannot be skipped

A reviewer handed a folder infers intent **from the code**, then checks the code against
that inference. The code therefore defines its own intent, and anything internally
consistent passes — including the defects. Every conclusion is circular.

Intent has to come from evidence *independent of the implementation being judged*, and it
has to be written down before verification starts. That written statement is the intent
contract. Without it, "is this working as intended?" has no answer to compare against.

## Evidence precedence

Rank intent evidence by how honestly it records what someone believed. Later classes
corroborate; they never override.

| Rank | Evidence class | Why it ranks here |
|---|---|---|
| **1a** | **Stated tests** — written from an expectation: an error or edge the author named, an output the author specified, a case the author believed would fail | Someone wrote down what should happen and enforced it, *before* the implementation existed. A belief specific enough to be wrong. |
| **1b** | **Recorded tests** — characterisation, mirror, mock-dominant, and nominally-shaped tests: written by running the code and writing down the answer | The implementation's own behaviour, transcribed. This is evidence **of the implementation**, not of intent — and it has no rank as intent evidence at all. |
| 2 | **Public contracts** — signatures, schemas, declared types, interface definitions | The promises the code makes to its callers, committed to in the type surface. |
| 3 | **Structural evidence** — module boundaries, layering, naming, dependency direction | Intent expressed as architecture; usually the most stable layer. |
| 4 | **Operational configuration** — deployment definitions, flags, thresholds, runbooks | What the system must do in production, stated for the environment rather than the source. |
| 5 | **Declared intent** — prose documentation | What someone *says* it should do. A claim to be tested, never a premise. |
| 6 | **History** — change records, change requests | Why the code exists, and what was believed at the time it was written. |

### The rank-1 discriminator

Every test an agent cites must be classified, and the classification stated on the claim. Rank 1a
is earned by a stated expectation, never by a passing test.

| Signal in the test | Class |
|---|---|
| Names an input the author expected to break; asserts an output the author chose rather than observed; a case that had to be **added** when something failed | **1a** |
| Asserts the same expression, helper, or call the implementation uses, recomputed in the test | **1b** — mirror; passes whenever the code passes, catches nothing |
| Substitutes the unit's own dependencies or the logic under test, so the production path never runs | **1b** — records the stub's contract |
| Inputs all nominal — well-formed, present, in-range, non-empty, one actor | **1b** — records behaviour on inputs production never produces |
| No assertion, a tautological one, or one on a value the test itself just computed | **1b** — unfalsifiable, carries zero evidence |
| Written after the code, in bulk, mirroring its branch structure | **1b** by default; promote to 1a only with a stated reason recorded on the claim |

Default when signals conflict or cannot be read: **1b**.

**Stated tests outrank prose, and that ordering is the whole discipline.** A *stated* test
contradicting its implementation is the highest-yield result this phase produces: intent was known,
written down, and not delivered. A *recorded* test contradicting its implementation is **not a
result at all** — it is the implementation agreeing with its own transcript, which is the absence of
a finding wearing its shape.

### Independence is provenance, not subject

Two sources that share a derivation are **one** class, however different they look. For the
confidence gate this means:

- a **1b** test and the code it was written from are one class, always;
- two **1b** tests over the same implementation are one class;
- a **1b** test and a rank-2 signature that merely agrees with it are one class — the signature is
  the same behaviour seen from outside, not a second derivation;
- a **1a** test and rank 2 are genuinely independent, and remain two.

So the suppression-grade pair is **1a + rank 2**, never 1b + anything. With only 1b available a
constraint reaches Medium at most. This closes the worst path available to this design: a
characterisation test reproducing a bug, its signature agreeing, High confidence reached, a finding
withdrawn — with the only trace being a transcript agreeing with itself.

## Documentation is a hypothesis, not a premise

Prose is where intent is *declared*. It is the weakest link in the chain above and it is
the one a reader is most tempted to over-trust, because it reads like an answer.

- A document never raises a claim above **Low** confidence on its own.
- A document's job is to tell you **where to look**, never **what to conclude**. Use it to
  seed the contract; let code, tests, and configuration confirm or refute it.
- When a document and the implementation disagree, the disagreement is a finding in its own
  right (drift), and it does **not** change the contract. The contract records what the
  system is meant to do; drift is reported separately.
- Never treat a document as establishing that a behaviour exists. Only a site in the code
  does that.

## Relevance gate for discovered prose

Scan the tree for project-authored prose. Most of what you find is noise, and noise costs
the user attention you will need later. A file is a **candidate** only if it clears all
four:

| # | Test | Reject when |
|---|---|---|
| 1 | **Project-authored and in scope** | Vendored, generated, third-party, licence text, generated API docs, badge or template files. |
| 2 | **Makes a falsifiable claim about this tree** | It names no module, entry point, flag, schema, or invariant that actually exists here. Aspirational or speculative text fails this. |
| 3 | **Current, not historical or proposed** | Archived, superseded, a proposal not adopted, a migration guide for work not done, or a plan rather than a description of the present. |
| 4 | **Materially redirects the work** | Acting on it would send verification at different code than ignoring it. A file that only restates what the code plainly shows does not clear the bar. |

Only survivors reach the user.

## Asking the user

Ask **once**, and only about survivors. Batch them into a single question: each candidate by
filename, one line on the claim it makes, and one line on what adopting it would change.
Never one question per file, and never ask about anything that failed the gate.

**The answer is an accelerant, not a dependency.** If the user declines every candidate, or
gives no answer, Phase 3 continues on self-discovery alone and records that it did. A phase
that stalls waiting for a human has failed; the contract is buildable from code, contracts,
tests, and configuration alone.

## Claim grammar

One claim is one falsifiable statement about intended behaviour.

```
- **Claim <id>** — <capability>: <what must be true, stated as an expectation>
  - Evidence: <class from the precedence table> — <file:line>
  - Confidence: High | Medium | Low
  - Verify by: <the technique from `shared/fanout.md` that would falsify it>
```

- A claim states **what must be true**. It never names a defect, never names a suspicious
  pattern, and never tells the verifier where to look. A claim that hands over the answer
  converts verification into confirmation, and a confirmatory phase is worse than none.
- Confidence **High** requires two independent classes agreeing. **Medium** is one class
  corroborated by structure. **Low** is declared intent alone, or a single weak signal.
- A claim with no falsifiable expectation is not a claim. Delete it rather than softening it.

## Silence is a claim

Record what the contract **assumes but nothing establishes** as its own Low-confidence
claim. The gaps between capabilities — a value assumed validated, an ordering assumed, a
transaction assumed to span two calls — are where intent is least often written down and
most often wrong. Deriving them is part of establishing intent, not an optional extra.