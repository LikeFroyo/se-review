# Synthetic code patterns — detecting AI-generated failure shapes

Audit code suspected of being AI-authored for common generation defects.

## Ground rule

Grade the observed defect, never the suspected authorship. "Looks AI-generated" is not a valid finding — a hallucinated method, an insecure query, or an unprovable test is.

## What to look for

- **Hallucinated APIs:** Methods, classes, or parameters called that do not exist in the pinned dependency versions.
- **Intent misuse:** Invoking a real library method with inverted or incorrect semantic parameters.
- **Mirror tests:** Unit tests that assert mock configurations rather than production logic, or pass even when production code is removed.
- **Block duplication:** 5+ lines of identical code copied across handlers instead of calling existing utility helpers.
- **Echo comments:** Superficial inline comments that mechanically restate what the syntax already shows, lacking any explanation of why or invariants.
- **Error masking:** Broad catch-all blocks (`except Exception: return None`) silently dropping errors to make code appear happy-path green.
