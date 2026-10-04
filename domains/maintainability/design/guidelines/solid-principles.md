# SOLID principles — symptom detection

Audit code against SOLID design symptoms.

## What to look for

- **Single Responsibility (SRP) — Divergent change:** A class or module that must be modified for multiple unrelated business reasons (e.g. database schema changes + email layout tweaks).
- **Open-Closed (OCP) — Type switches:** Cascading `if-elif` or `switch` statements checking object types or enum variants, requiring changes to existing core logic when adding a new variant.
- **Liskov Substitution (LSP) — Refused bequest:** A derived class that overrides a method by raising `NotImplementedError`, no-oping, or weakening preconditions.
- **Interface Segregation (ISP) — Fat interfaces:** Interfaces forcing consumers or implementors to depend on methods they never call.
- **Dependency Inversion (DIP) — Concrete dependencies:** High-level business logic importing and instantiating low-level storage, network, or third-party client implementations directly.
