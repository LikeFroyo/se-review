# Coupling & cohesion — modular boundaries and dependency flow

Audit inter-module dependencies and coherence of responsibilities.

## What to look for

- **Circular dependencies:** Two modules importing each other, fusing their lifecycles and complicating build/test pipelines.
- **Global mutable singletons:** Global dictionaries, module-level state, or singletons coupling unrelated callers across threads and files.
- **Shotgun surgery:** A single conceptual business requirement requiring edits across many dispersed files.
- **Feature envy:** A method that accesses another object's fields and methods significantly more than its own.
- **Middle-man layers:** Wrapper classes or layers that do nothing except delegate calls to an underlying object without adding logic.
