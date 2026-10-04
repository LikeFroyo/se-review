# Manifest hygiene — dependency scoping and version boundaries

Audit third-party package declarations in application and service manifests.

## What to look for

- **Unbounded version ranges:** Upper-unbounded ranges (`>=1.0`, `*`) that invite upstream breaking changes into fresh builds.
- **Scope pollution:** Development, test, or linting packages declared inside runtime dependencies instead of distinct optional groups.
- **Trivial dependencies:** Adding third-party libraries for trivial logic easily satisfied by the standard library.
- **Uncontrolled registries:** Hybrid feed configurations where public package feeds take precedence over private internal feeds (dependency confusion).
- **Abandoned packages:** Dependencies with no active maintenance, archived repositories, or unpatched critical CVEs.
- **Confusable names:** A package whose name is a near miss of a popular one — a one-edit typo (`requsts`), a grammar-stem variant (`swaggerize` for `swaggerify`), a scope or delimiter variant of a scoped name, or a similarly-named author or group id in a hierarchical registry. Confusion is mostly semantic, not a typo, and a lookalike is often benign until a later version.
