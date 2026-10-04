---
name: se-review-correctness-ai-systems
description: Sub-domain evaluator for AI Systems — audits LLM and agent application correctness and safety across untrusted input, model output, tool use, retrieval, and evaluation gates.
metadata:
  domain: correctness
  role: pillar
  type: sub-domain-evaluator
---

# AI Systems Sub-Domain Evaluator

Evaluates code that calls a language model, retrieves context for one, or lets one take actions. The defect classes here are specific to systems where a non-deterministic component produces input that the rest of the program treats as trusted.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Untrusted Model Input** | Prompt injection, instruction/data confusion, retrieval poisoning | `guidelines/untrusted-model-input.md` |
| **Output Handling** | Model output used as data, code, SQL, or a decision without validation | `guidelines/output-handling.md` |
| **Tool Use & Agency** | Tool-call authorization, argument validation, scope, confirmation, loops | `guidelines/tool-use-and-agency.md` |
| **Evaluation & Drift** | Missing regression gates, golden-set staleness, non-determinism in business logic | `guidelines/evaluation-and-drift.md` |

## Sub-domain scoring & deduction rules
- Untrusted content reaching a model that can reach a privileged tool (prompt injection with effect): **CRITICAL** (-25 points).
- Model output executed, interpolated into a query, or used as an authorization decision without validation: **CRITICAL** (-25 points).
- Retained content or tool result reaching the model with no provenance or trust label: **MAJOR** (-10 points).
- Agent loop with no bound, no confirmation on a destructive action, or no tool allowlist: **CRITICAL** or **MAJOR** (-25 to -10 points).
- Model call on a path that must be deterministic, with no seed, cache, or deterministic mode: **MAJOR** (-10 points).
- Behaviour change with no eval or golden-set update: **MAJOR** (-10 points).
- Prompt wording, temperature choice, or model selection with no correctness or safety consequence: **INFO** (0 points).

## Scope boundary

- This sub-domain grades the **application code around the model**. A defect in the model provider, in the inference service, or in the training data is out of scope and is recorded as a dependency note.
- Model *quality* — whether the answers are good — is not a code defect and is out of scope. Grounding, tool correctness, validation, and authorization are in scope.
- Anything found here that is a conventional defect (injection, authz, data loss) is graded at its normal severity **and** cross-referenced to the owning sub-domain, so it is never counted twice. Report the highest grade once.
