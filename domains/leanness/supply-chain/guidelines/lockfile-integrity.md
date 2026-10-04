# Lockfile integrity — deterministic installs and artifact verification

Audit lockfiles and frozen build environments.

## What to look for

- **Missing lockfiles:** Deployable services or production applications omitting committed lockfiles.
- **Out-of-sync declarations:** Manifest dependencies modified without re-resolving and updating the corresponding lockfile.
- **Hand-edited entries:** Manually tweaked version numbers or checksum fields inside machine-generated lockfiles.
- **Disabled cryptographic verification:** Build configurations disabling package hash enforcement (`--no-verify`, `--trusted-host`).
- **Mutable installs in release images:** Release containers executing editable installs (`pip install -e`, `npm link`) instead of immutable frozen dependencies.
