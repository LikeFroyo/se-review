# Evaluation & drift — knowing whether the change made it better or worse

Audit the evidence that a model-dependent change is safe. A model change is a behaviour change, and without a gate it is an unreviewed production change wearing a config diff.

## What to look for

- **Behaviour change with no eval:** A prompt edit, a model or version change, a retrieval or chunking change, or a temperature change shipped with no test, golden set, or recorded comparison of before and after.
- **Golden set that has gone stale:** An evaluation corpus built once from historical data and never refreshed, so it validates behaviour against cases the product no longer has, and the score rises while the product does not improve.
- **No regression gate in the pipeline:** Evaluations that run manually or on a schedule, so a failing result is discovered after deployment rather than before it.
- **Pass/fail assertion on probabilistic output:** A test asserting an exact string match, an exact ordering, or an exact number from a model, which is either flaky or, worse, written to match whatever the model currently says.
- **Scored metric with no failure threshold:** A quality, accuracy, or safety score recorded in CI with no defined value below which the build fails.
- **Non-determinism on a required-deterministic path:** A model call in classification, routing, pricing, compliance, or authorization logic with no seed, no cache, and no deterministic mode, so the same input yields a different decision on each run.
- **Silent provider change:** No pinning or version assertion on the model or endpoint, so a provider-side change alters behaviour with no diff in the repository and no test to catch it.
- **Evaluation that cannot fail:** An eval asserting the model produced *some* output, or that a call happened, with nothing checking whether the output was correct.
