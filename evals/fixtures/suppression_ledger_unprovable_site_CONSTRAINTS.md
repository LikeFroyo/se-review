# Sizing constraints

**C1 (binding).** Position sizing has **one** implementation, `size_order`.
**Why:** two implementations of a signed quantity can disagree and the disagreement is
undetectable after the fact.
**What depends on this:** every order, regardless of the path that reached it, is sized
by the same function.
