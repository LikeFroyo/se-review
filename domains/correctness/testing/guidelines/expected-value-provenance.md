# Expected-value provenance — where the asserted answer came from

Audit where the expected value in a check came from. This is the question that separates a check
that can fail from one that cannot: a value derived from the code under test confirms that code,
whatever it does.

- **Expected value re-derived from the implementation:** The expected result is recomputed using the same algorithm, helper, or expression the code under test uses, so a mistake in the algorithm passes both sides.
- **Assertion comparing a call to a call:** Output is compared against a second invocation of the same function — a tautology that can fail only if the function is non-deterministic.
- **Expected value copied from a previous run's output:** The recorded answer is current behaviour, including its defects, so the check freezes a bug as correct.
- **Undocumented literal:** A bare value is asserted with no recorded source, derivation, or requirement it traces to, so nobody can say what would make it wrong.
- **Co-mutated expectation:** The expected value was changed in the same change as the code, so the check was never independently asked whether the new behaviour is right.
- **One literal across cases that should differ:** A single expected value is reused across inputs whose correct answers differ, so most cases assert nothing about their own input.
- **Expectation stale against a deliberate change:** Behaviour changed on purpose and the expected value was not revisited, so the check now fails for the wrong reason — or was weakened until it passed.
