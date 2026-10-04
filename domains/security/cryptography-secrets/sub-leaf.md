# Cryptography & Secrets Sub-Domain Evaluator

Evaluates the primitives and the material. Most defects here are not weaknesses in an algorithm but
misuse of a correct one — a mode that does not match the job, or a secret that reaches somewhere it
should not.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Cryptography** | Primitives, modes, key derivation, randomness, comparison | `guidelines/cryptography.md` |
| **Secret Material** | Storage, logging, rotation, generation, distribution | `guidelines/secret-material.md` |

## Sub-domain scoring & deduction rules

- **Live credential material reachable from an untrusted source:** **CRITICAL** (-25).
- **Primitive or mode that provides no security for the claimed property:** **CRITICAL** (-25).
- **Secret logged, returned, or persisted in the clear:** **CRITICAL** (-25).
- **Comparison of a secret or tag that is not constant-time:** **MAJOR** (-10).
- **Unrotatable, unsalted, or low-entropy generated secret:** **MAJOR** (-10).
