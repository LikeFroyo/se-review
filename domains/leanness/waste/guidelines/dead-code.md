# Dead code — L1 detection and verification procedure

Ask this first: does this code earn its place at all? The fix for dead code is always deletion.

## What to look for

- **Unreachable code:** Branches behind impossible conditions, return statements after unhandled returns, abandoned fallback paths.
- **Orphaned symbols:** Functions, classes, variables, and imports with zero internal callers in the repository.
- **Commented-out code blocks:** Code kept in comments "just in case" instead of relying on version control history.
- **Dead tests & fixtures:** Unit tests asserting behaviors of already-deleted functions, or test fixtures never imported.

## Dead-code proof procedure

Prove death before grading Critical. Run in order, stop at the first live caller:
1. **Repository text search:** Search every tracked file, not only source — manifests, CI configs, env examples, entry-point and skill/command definitions included. Search the bare string as well as the identifier: config keys and string references often differ from symbol casing. State any search excludes; a caller hidden by your own exclude is a false death. A truncated search proves nothing: narrow or page it to completion, and treat an uncompletable search as unproven.
2. **Dynamic dispatch inspection:** Check reflection, dynamic imports (`getattr`, `importlib`), string-keyed dependency injection registries, and plugin manifests.
3. **External public API check:** If the symbol is part of an exported library package or versioned public interface, grade Info ("no in-repo references; confirm external callers"), never Critical.
4. **Live reference verification:** Confirm references found are live. References inside backups, scratch files, or dead test modules do NOT count as callers.

**Excluded from death grading:** Recovery, break-glass, and rollback paths. Rarely used is not dead — retiring such a path is a human decision. Flag it at Info, never Critical.

## Caller-hiding mechanisms

| Mechanism | Where callers hide | Proof step |
|---|---|---|
| Dynamic dispatch / reflection | string names, `getattr`, DI keys | search string literals, container registrations |
| Plugin entry points | manifests (`package.json`, `pyproject.toml`) | inspect entry point declarations |
| Framework conventions | class/file name routing, decorators | verify framework discovery conventions |
| Serialized database names | DB rows, migration scripts, queue jobs | search database seeds, migrations, fixtures |
