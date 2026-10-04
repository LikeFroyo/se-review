# Test adequacy — coverage honesty and assertion validity

Audit unit and integration tests accompanying production changes.

## What to look for

- **Untested changed behavior:** Adding new execution logic or bug fixes without adding tests that would fail if the change were reverted.
- **Assertion-free tests:** Tests that execute functions without asserting return values, state changes, or database effects.
- **Mock-asserting-mock tests:** Unit tests that script mock behaviors and only assert that the mocks were invoked, without verifying actual business logic outcomes.
- **Happy-path only testing:** Suites completely omitting failure paths (timeouts, network errors, permission denials, invalid payloads).
- **Weak assertions surviving trivial mutants:** Tests executing the real code with assertions that still pass for obviously-wrong outputs (`is not None`, `>= 0`, `len > 0`) — covered but not killing, so the suite reports protection it does not provide.
- **Untested boundary conditions:** Boundary on/off points never exercised (`<` vs `<=`, 0/100 percent, empty vs one element), where the most fault-revealing mutants live.
- **Disabled test with no owner:** A test marked skip, xfail, quarantine, or commented out with no reason and no owner, so it reports green while covering nothing — a deleted test that still costs runtime and still reads as protection.
- **Expected-failure that cannot fail:** A marker that does not turn the suite red when the test starts passing, so a real fix goes unnoticed and the marker silently rots.
- **Impossible marker condition:** A skip or quarantine condition that can never be true, so the check never runs and can never fail.
- **Marker scoped too wide:** An expected-failure marker applied to a whole module or class, hiding which specific cases regressed behind one entry.
- **Stale marker:** A skip whose reason points at an issue already resolved, leaving the check permanently disabled with no remaining justification.
- **Uncounted marker set:** Nothing asserts the size of the skip or quarantine list, so its growth is invisible to anyone reviewing the change.
