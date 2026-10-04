# Change surface — what it costs to change this, and to check the change

Audit the two questions that decide whether a change is safe: how many places must move together, and whether the change can be verified at all.

## Change blast radius

- **No seam at the highest-churn dependency:** The dependency that changes most often is wired in concretely, so verifying a change means standing up the real system — a real database, a real broker, a real network.
- **One rule, many edit sites:** A business rule whose definition is duplicated across handlers, jobs, and UIs, so a change is correct only if every site is found and none is missed.
- **Change coupled to a schema or a published contract:** A change that cannot be deployed independently of a migration, a queue message, or a client release, so every change is a coordinated multi-party deploy.
- **Change with no owner boundary:** A behaviour split across modules that no single file owns, so the engineer who changes it cannot tell whether they have found all of it.

## Verification surface

- **Test harder than the code:** A test whose setup, fixtures, or mock choreography exceed the complexity of the function it verifies, so the protected code is easier to break than to check.
- **Test asserts the mock, not the behaviour:** A test that passes when the collaborator's configuration changes, so it pins the current wiring rather than the required outcome.
- **No failing-case test:** Only the happy path is covered, so the guard clause, the empty input, and the error branch are the code most likely to be broken by a change and the code never exercised.
- **Boundary behaviour untested:** The seam between two components is never exercised, so each side is tested only against its own assumptions about the other.
