# Cognitive & cyclomatic complexity — nesting and method length

Audit code complexity and structural understandability.

## What to look for

- **Nesting past 3 levels:** Deeply nested `if`, `for`, `while`, or `try` blocks that multiply the internal states an engineer must mentally track.
- **High cyclomatic complexity:** Methods with >10–15 decision points (`if`, `elif`, `case`, `&&`, `||`, ternaries).
- **Long methods:** Functions spanning 50+ lines conflating multiple domain duties (e.g. validating input + computing pricing + updating database + sending notifications).
- **God objects / Large classes:** Classes coupling dozens of unrelated duties with few shared instance fields (low cohesion).
