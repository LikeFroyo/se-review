# Injection & Interpretation Sub-Domain Evaluator

Evaluates what happens when data is *interpreted* — executed as code, parsed as a structure, or
rendered into another context. The shared failure is a value crossing into a context that gives it
meaning it was never meant to carry.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Injection & Secrets** | Query, command, path, template, and header injection; secret leakage | `guidelines/injection-secrets.md` |
| **Unsafe Parsing** | Deserialisation, archive extraction, markup and protocol parsers | `guidelines/unsafe-parsing.md` |
| **Cross-Origin Trust** | Origin checks, credentialed cross-origin reads, forgery tokens, referrer, frame messaging | `guidelines/cross-origin-trust.md` |

## Sub-domain scoring & deduction rules

- **Attacker-controlled value interpreted as code or structure, path shown:** **CRITICAL** (-25).
- **Secret material reachable from an untrusted source:** **CRITICAL** (-25).
- **Origin or credential check derived from a value the client controls:** **CRITICAL** (-25).
- **Context-mismatched escaping — right defence, wrong context:** **MAJOR** (-10).
- **Parser accepts a structure it has no reason to accept:** **MAJOR** (-10).
