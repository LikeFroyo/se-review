#!/usr/bin/env python3
"""Validation tool for Agent Skills (agentskills.io specification).

Validates:
1. Frontmatter syntax and constraints in SKILL.md and leaf.md.
2. Completeness and validity of domain orchestrators (leaf.md) and sub-domain evaluators (sub-leaf.md).
3. Sibling guideline files across every discovered sub-domain (count is dynamic, never hardcoded).
4. Internal link integrity across all shared, domain, and sub-domain documents.
5. Heading and backtick formatting consistency.
6. evals/evals.json schema, assertions, and fixture file paths.
"""

import fnmatch
import json
import os
import re
import sys
from pathlib import Path

# Safe stdout encoding for cross-platform terminals (including Windows cp1252)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def validate_frontmatter(file_path: Path) -> tuple[dict, str, list[str]]:
    errors = []
    if not file_path.is_file():
        return {}, "", [f"Missing file: {file_path}"]

    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}, content, [f"{file_path.name} does not start with YAML frontmatter delimiter (---)"]

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content, [f"{file_path.name} frontmatter is not properly closed with '---'"]

    raw_yaml = parts[1].strip()
    body = parts[2]

    metadata = {}
    lines = [ln for ln in raw_yaml.splitlines() if ln.strip() and not ln.strip().startswith("#")]

    # Pass 1: find keys whose value is a block sequence (`key:` then `- item`), and
    # whether that key was nested (under `metadata:`) or top level. A scalar-only
    # parser cannot represent a list, so recording the key here is the only way
    # the str->str and space-separated checks below can reject one instead of
    # silently accepting it as "".
    list_valued: dict[str, bool] = {}
    head: str | None = None
    head_nested = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            if head:
                list_valued[head] = head_nested
                head = None
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            head_nested = line.startswith(("  ", "\t"))
            head = key.strip() if not val.strip() else None

    # Pass 2: collect scalars. List-valued keys are skipped, never coerced.
    head = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key in list_valued:
            continue
        if not val:
            # `metadata:` with no inline value is a container, not a scalar.
            if key == "metadata" and not line.startswith((" ", "\t")):
                metadata[key] = {}
            continue
        if line.startswith(("  ", "\t")):
            if not isinstance(metadata.get("metadata"), dict):
                metadata["metadata"] = {}
            metadata["metadata"][key] = val
        else:
            metadata[key] = val

    # Spec: https://agentskills.io/specification — name 1-64, lowercase alnum
    # + hyphens, no leading/trailing hyphen, no consecutive hyphens, must
    # match parent directory name.
    name = metadata.get("name", "")
    if not name:
        errors.append(f"{file_path.name} frontmatter missing required 'name' field")
    else:
        if not 1 <= len(name) <= 64:
            errors.append(f"'name' length {len(name)} out of 1-64 range in {file_path}")
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
            errors.append(f"'name' '{name}' invalid in {file_path.name}: must be lowercase alphanumeric and hyphens")
        if name.startswith("-") or name.endswith("-"):
            errors.append(f"'name' '{name}' must not start or end with a hyphen ({file_path})")
        if "--" in name:
            errors.append(f"'name' '{name}' must not contain consecutive hyphens ({file_path})")
        # Parent directory match applies to SKILL.md files per Agent Skills spec.
        if file_path.name == "SKILL.md":
            parent = file_path.parent.resolve().name
            if parent != name:
                errors.append(
                    f"SKILL.md name '{name}' must match parent directory '{parent}' "
                    f"({file_path}). See https://agentskills.io/specification"
                )

    desc = metadata.get("description", "")
    if not desc:
        errors.append(f"{file_path.name} frontmatter missing required 'description' field")
    else:
        if not 1 <= len(desc) <= 1024:
            errors.append(f"'description' length {len(desc)} out of 1-1024 range in {file_path}")
        # Best practice: https://agentskills.io/skill-creation/optimizing-descriptions
        # — imperative trigger language describing what + when to use.
        if file_path.name == "SKILL.md":
            lowered = desc.lower()
            if "when" not in lowered and "use " not in lowered:
                errors.append(
                    f"{file_path} description must state when to use it "
                    f"(imperative 'Use when/whenever'). See optimizing-descriptions."
                )

    # Optional spec fields: compatibility <=500, metadata str->str, allowed-tools str.
    compat = metadata.get("compatibility", "")
    if compat and len(str(compat)) > 500:
        errors.append(f"'compatibility' exceeds 500 chars in {file_path}")
    meta = metadata.get("metadata", {})
    if isinstance(meta, dict):
        for k, v in meta.items():
            if not isinstance(v, str):
                errors.append(f"metadata.{k} must be a string in {file_path}")
    for key, nested in list_valued.items():
        if nested:
            errors.append(
                f"metadata.{key} is a list in {file_path}; spec requires a str->str mapping"
            )
        elif key == "allowed-tools":
            errors.append(
                f"'allowed-tools' is a list in {file_path}; spec requires a space-separated string"
            )
        else:
            errors.append(f"'{key}' is a list in {file_path}; spec requires a scalar string")

    # Progressive disclosure: SKILL.md <500 lines and <5000 tokens (spec
    # recommends both). Token estimate via chars/4.
    if file_path.name == "SKILL.md":
        body_lines = len(body.splitlines())
        est_tokens = len(body) // 4
        if body_lines > 500:
            errors.append(f"{file_path} body {body_lines} lines exceeds 500-line spec guideline")
        if est_tokens > 5000:
            errors.append(f"{file_path} body ~{est_tokens} tokens exceeds 5000-token spec guideline")

    return metadata, body, errors


def validate_skill_refs(skill_root: Path, entry: Path, body: str) -> list[str]:
    """Enforce one-level file references from SKILL.md (spec: file references).

    SKILL.md may reference subdir/file.md (one level deep). It must not reach
    directly into guidelines/ — detail loads via leaf -> sub-leaf -> guideline.
    """
    errors = []
    refs = set(re.findall(r"`((?:shared|domains|project-tree|auditandevolve|scripts)/[^`]*?\.md)`", body))
    for ref in refs:
        depth = len(Path(ref).parts)
        if depth > 3:
            errors.append(f"{entry} reference `{ref}` exceeds one-level disclosure (depth {depth})")
        if "/guidelines/" in ref:
            errors.append(
                f"{entry} must not reference guidelines directly (`{ref}`); "
                f"load via leaf.md -> sub-leaf.md"
            )
        target = skill_root / ref.split("*")[0].split("<")[0]
        # Skip wildcards/placeholders like domains/*/leaf.md.
        if "*" in ref or "<" in ref:
            continue
        if not target.is_file() and not target.is_dir():
            errors.append(f"{entry} references non-existent path: {ref}")
    return errors


def check_markdown_backticks(file_path: Path) -> list[str]:
    errors = []
    if not file_path.is_file():
        return [f"File not found for backtick check: {file_path}"]
    lines = file_path.read_text(encoding="utf-8").splitlines()
    in_code_block = False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        clean = line.replace("```", "")
        count = clean.count("`")
        if count % 2 != 0:
            errors.append(f"{file_path.name}:{i}: Unmatched backtick: {line.strip()}")
    # A file that ends inside a code block never reports a mismatch, because every
    # line after the opening fence is skipped. That is not a cosmetic hole: the rest
    # of the file is then never checked for unbalanced backticks either, so a single
    # unterminated fence silently disables the rule for the whole document.
    if in_code_block:
        errors.append(
            f"{file_path.name}: code block opened with ``` is never closed; every "
            f"line after it was skipped, including its unbalanced backticks"
        )
    return errors


def validate_shared(shared_dir: Path) -> list[str]:
    errors = []
    if not shared_dir.is_dir():
        return [f"Missing shared directory: {shared_dir}"]

    required_shared = ["severity-and-rules.md", "output-format.md", "council.md"]
    for req in required_shared:
        target = shared_dir / req
        if not target.is_file():
            errors.append(f"Missing shared document: shared/{req}")
        else:
            errors.extend(check_markdown_backticks(target))
    return errors


def validate_subdomain(subdomain_dir: Path) -> tuple[int, list[str]]:
    """Validates a single sub-domain directory containing sub-leaf.md and guidelines/ folder."""
    errors = []
    sub_leaf = subdomain_dir / "sub-leaf.md"
    if not sub_leaf.is_file():
        errors.append(f"Missing sub-leaf.md in sub-domain: {subdomain_dir}")
        return 0, errors

    errors.extend(check_markdown_backticks(sub_leaf))
    sub_leaf_content = sub_leaf.read_text(encoding="utf-8")

    guidelines_dir = subdomain_dir / "guidelines"
    if not guidelines_dir.is_dir():
        errors.append(f"Missing guidelines/ directory in sub-domain: {subdomain_dir}")
        guideline_files = []
    else:
        guideline_files = list(guidelines_dir.glob("*.md"))
        if not guideline_files:
            errors.append(f"No guideline documents found in: {guidelines_dir}")

    for gfile in guideline_files:
        errors.extend(check_markdown_backticks(gfile))

    # Check references in sub-leaf.md to guideline files
    file_refs = re.findall(r"`guidelines/([a-z0-9_-]+\.md)`", sub_leaf_content)
    for ref in set(file_refs):
        target = guidelines_dir / ref
        if not target.is_file():
            errors.append(f"{sub_leaf} references missing guideline: guidelines/{ref}")

    # The reverse direction, which is the one that actually loses work. A dangling
    # reference is loud; an unenumerated guideline file is silent -- the sub-leaf
    # loads, every reference resolves, and the one guideline nobody listed is
    # simply never read by any agent following that table.
    referenced = set(file_refs)
    for gfile in guideline_files:
        if gfile.name not in referenced:
            errors.append(
                f"{gfile.name} exists but is not enumerated in "
                f"{subdomain_dir.name}/sub-leaf.md; an agent loading that table "
                f"would never read it"
            )

    return len(guideline_files), errors


def validate_domain(domain_dir: Path) -> tuple[int, int, list[str]]:
    """Validates a single domain directory containing leaf.md and sub-domain directories."""
    errors = []
    leaf_file = domain_dir / "leaf.md"
    if not leaf_file.is_file():
        errors.append(f"Missing leaf.md in domain: {domain_dir}")
        return 0, 0, errors

    _, leaf_body, leaf_fm_errs = validate_frontmatter(leaf_file)
    errors.extend(leaf_fm_errs)
    errors.extend(check_markdown_backticks(leaf_file))

    sub_dirs = [d for d in domain_dir.iterdir() if d.is_dir()]
    if not sub_dirs:
        errors.append(f"No sub-domain directories found in {domain_dir}")
        return 0, 0, errors

    total_subdomains = len(sub_dirs)
    total_guidelines = 0

    for sdir in sorted(sub_dirs):
        g_count, sub_errs = validate_subdomain(sdir)
        total_guidelines += g_count
        errors.extend(sub_errs)

    # Check references inside leaf.md to sub-domain sub-leaf.md files
    subleaf_refs = re.findall(r"`([a-z0-9_-]+/sub-leaf\.md)`", leaf_body)
    for sref in set(subleaf_refs):
        target_sub = domain_dir / sref
        if not target_sub.is_file():
            errors.append(f"{domain_dir.name}/leaf.md references missing sub-leaf: {sref}")

    return total_subdomains, total_guidelines, errors


def validate_projecttree(pt_dir: Path) -> list[str]:
    """Validates the project-tree conformance sub-skill (not a review domain)."""
    errors = []

    if not pt_dir.is_dir():
        errors.append(f"Missing project-tree sub-skill directory: {pt_dir}")
        return errors

    required = [
        "SKILL.md",
        "phase1-language.md",
        "phase2-stack.md",
        "phase3-intent.md",
        "shared/identification.md",
        "shared/source-resolution.md",
        "shared/adherence.md",
        "shared/report-format.md",
        "shared/intent-contract.md",
        "shared/fanout.md",
        "profiles/README.md",
        "intent/README.md",
        "shared/deliberate.md",
        "shared/anti-pattern-gate.md",
    ]
    for rel in required:
        if not (pt_dir / rel).is_file():
            errors.append(f"Missing project-tree document: project-tree/{rel}")

    entry = pt_dir / "SKILL.md"
    if entry.is_file():
        metadata, body, fm_errors = validate_frontmatter(entry)
        errors.extend(fm_errors)
        errors.extend(check_markdown_backticks(entry))
        if metadata.get("name") != "project-tree":
            errors.append(
                f"project-tree/SKILL.md name '{metadata.get('name')}' != 'project-tree'"
            )
        # One-level internal references only; no deep chains.
        for ref in set(re.findall(r"`((?:shared|profiles|intent)/[a-zA-Z0-9._-]+\.md)`", body)):
            if not (pt_dir / ref).is_file():
                errors.append(f"project-tree/SKILL.md references non-existent path: {ref}")

    for rel in required:
        f = pt_dir / rel
        if f.is_file():
            errors.extend(check_markdown_backticks(f))

    # Profile directory: only README.md and INDEX.md ship; technology profiles
    # are created by runs, so any other .md must be a real profile with the
    # required sections from profiles/README.md.
    profiles_dir = pt_dir / "profiles"
    if profiles_dir.is_dir():
        required_sections = ("## Identity", "## Ruleset", "## Conformance", "## Re-check triggers")
        for profile in profiles_dir.glob("*.md"):
            if profile.name == "README.md":
                continue
            content = profile.read_text(encoding="utf-8")
            missing = [s for s in required_sections if s not in content]
            if missing:
                errors.append(
                    f"project-tree profile {profile.name} missing sections: {', '.join(missing)}"
                )

    # Every project-tree document must resolve the files it names. The root
    # SKILL.md is checked by validate_skill_refs, but the phase files were not,
    # and a phase file naming a deleted artifact is a silent instruction to an
    # agent to recreate the thing a ground rule just forbade.
    for doc in sorted(pt_dir.rglob("*.md")):
        if doc.name in ("README.md", "INDEX.md"):
            continue
        rel_doc = doc.relative_to(pt_dir)
        body = doc.read_text(encoding="utf-8")
        for ref in set(re.findall(r"`([a-z0-9_][a-zA-Z0-9_./-]*\.md)`", body)):
            depth = len(Path(ref).parts)
            if ref.startswith(("shared/", "profiles/", "intent/")):
                if depth > 2:
                    errors.append(
                        f"{rel_doc} reference `{ref}` is {depth} levels deep; "
                        "keep references one level from the file that makes them"
                    )
                if not (pt_dir / ref).exists():
                    errors.append(f"{rel_doc} references non-existent path: {ref}")
            elif ref.startswith(("phase1-", "phase2-", "phase3-", "SKILL")):
                if not (pt_dir / ref).exists():
                    errors.append(f"{rel_doc} references non-existent path: {ref}")

    # Invariants that prose alone cannot hold. Each is a rule whose failure mode
    # is a silently wrong verdict rather than a broken link, so the gate has to
    # notice the rule being absent. The 1a/1b split is the sharpest: without it a
    # characterisation test plus a matching signature reads as two independent
    # evidence classes, reaches High, and suppresses a real finding.
    invariants = {
        "shared/intent-contract.md": (
            "the rank-1 discriminator",
            "independence is provenance, not subject",
            "recorded tests",
        ),
        "shared/deliberate.md": (
            "run-wide probe cap",
            "suppression-grade pair",
        ),
        "shared/fanout.md": (
            "10 claims per package",
        ),
    }
    for rel, needles in invariants.items():
        doc = pt_dir / rel
        if not doc.is_file():
            continue
        body = doc.read_text(encoding="utf-8").lower()
        missing = [n for n in needles if n.lower() not in body]
        if missing:
            errors.append(
                f"project-tree {rel} is missing a load-bearing invariant: "
                f"{'; '.join(missing)}"
            )

    # Invariants whose failure mode is a silently wrong report or a silently wrong
    # division of labour -- the class this skill exists to prevent, reappearing in
    # its own output. Absence of a field reads as absence of a problem, so the gate
    # checks each rule is specified, not merely mentioned.
    # Intent artifacts carry a different shape from profiles: a contract and its
    # verification rather than a ruleset and its conformance.
    intent_dir = pt_dir / "intent"
    if intent_dir.is_dir():
        intent_sections = ("## Shape", "## Contract", "## Verification", "## Re-check triggers")
        for artifact in intent_dir.glob("*.md"):
            if artifact.name == "README.md":
                continue
            content = artifact.read_text(encoding="utf-8")
            missing = [s for s in intent_sections if s not in content]
            if missing:
                errors.append(
                    f"project-tree intent {artifact.name} missing sections: {', '.join(missing)}"
                )

    return errors


def validate_evals(skill_dir: Path, skill_name: str) -> list[str]:
    errors = []
    evals_file = skill_dir / "evals" / "evals.json"
    if not evals_file.is_file():
        return [f"Missing evals file: {evals_file}"]

    try:
        data = json.loads(evals_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"evals.json is not valid JSON: {exc}"]

    if data.get("skill_name") != skill_name:
        errors.append(f"evals.json skill_name '{data.get('skill_name')}' != '{skill_name}'")

    evals = data.get("evals", [])
    if not evals:
        errors.append("evals.json contains no test cases")

    for item in evals:
        eid = item.get("id")
        prompt = item.get("prompt", "")
        expected = item.get("expected_output", "")
        files = item.get("files", [])
        assertions = item.get("assertions", [])

        if not prompt:
            errors.append(f"Eval {eid} missing prompt")
        if not expected:
            errors.append(f"Eval {eid} missing expected_output")
        if not assertions:
            errors.append(f"Eval {eid} missing assertions array (Agent Skills spec)")

        for fpath in files:
            full = skill_dir / fpath
            if not full.is_file():
                errors.append(f"Eval {eid} references missing file: {fpath}")

        # assertion_roles is optional, but when present it must line up with the
        # assertions it annotates. A drifted array would make the kill criterion
        # score mislabelled assertions while reporting a clean result.
        roles = item.get("assertion_roles")
        if roles is not None:
            if not isinstance(roles, list) or len(roles) != len(assertions):
                errors.append(
                    f"Eval {eid} assertion_roles has {len(roles) if isinstance(roles, list) else '?'} "
                    f"entries for {len(assertions)} assertions"
                )
            else:
                unknown = sorted({r for r in roles if r not in ("verdict", "probe", "strict")})
                if unknown:
                    errors.append(
                        f"Eval {eid} assertion_roles has unknown roles: {', '.join(unknown)}"
                    )
                elif "verdict" not in roles:
                    errors.append(
                        f"Eval {eid} assertion_roles marks no verdict assertion; the "
                        "false-positive and false-negative rates read verdict roles only"
                    )

    errors.extend(_validate_registry(skill_dir, evals))

    return errors


def _validate_registry(skill_dir: Path, evals: list) -> list[str]:
    """The eval id to directory map must be a function, and must cover the corpus.

    `scripts/eval_registry.py` is hand-maintained and nothing else checked it -- no validator,
    no test. Two faults matter, and only one of them loses data.

    A **missing key** is harmless: `eval_name()` falls back to `eval-{id}`, and `run_evals.py`
    and `grade_evals.py` both call it, so a fixture added at id 103 without a registry entry
    runs and grades fine, just under a synthetic name. An earlier account of this described
    that as a silent writer/reader split, which is wrong -- the fallback is shared, so the two
    cannot disagree about where a verdict lives.

    A **duplicate value** does lose data. Two ids resolving to one directory means both arms of
    both fixtures write into the same path, and the second overwrites the first. That is the
    only fault here worth a red test, and it cannot be reached by adding a domain -- which
    appends ids rather than reusing them.
    """
    errors = []
    sys.path.insert(0, str(skill_dir / "scripts"))
    try:
        from eval_registry import EVAL_NAMES
    except Exception as exc:  # noqa: BLE001 -- the reason is the message
        return [f"eval_registry.py could not be imported: {exc}"]

    by_name: dict[str, list[int]] = {}
    for eid, name in EVAL_NAMES.items():
        by_name.setdefault(name, []).append(eid)
    for name, ids in sorted(by_name.items()):
        if len(ids) > 1:
            errors.append(
                f"eval_registry maps ids {sorted(ids)} to the same directory '{name}'; both "
                f"fixtures would write into one path and the second would overwrite the first"
            )

    corpus_ids = {e.get("id") for e in evals if isinstance(e, dict)}
    uncovered = sorted(corpus_ids - set(EVAL_NAMES))
    if uncovered:
        errors.append(
            f"{len(uncovered)} eval id(s) in evals.json carry no registry entry "
            f"({uncovered[:8]}{'...' if len(uncovered) > 8 else ''}); they resolve to "
            f"eval-<id> and run correctly, but the name says nothing about the fixture"
        )
    stale = sorted(set(EVAL_NAMES) - corpus_ids)
    if stale:
        errors.append(
            f"{len(stale)} registry id(s) have no fixture in evals.json ({stale[:8]}"
            f"{'...' if len(stale) > 8 else ''}); the entry is dead weight"
        )
    return errors


# A load-bearing numeral is published by name in several files, and nothing made
# them equal. The finding cap is the clearest case: it is taught in the root
# orchestrator, the report format, the severity rules and the project-tree
# sub-skill, and the suppression ledger *couples its own probe and row caps to it
# by reference* -- "equal to both the ledger's printable rows and the report's
# finding cap". Raise the finding cap and that sentence silently becomes false
# while every file still reads correctly in isolation.
#
# The sites are listed rather than discovered. An auto-discovered scan cannot
# tell this numeral from an unrelated one -- the project-tree phase-2 question
# list is numbered to 15 and has nothing to do with finding caps -- so a
# discovery-based check either misses real sites or "corrects" prose it does not
# understand. An explicit table is checkable by reading.
#
# The extras clause is the load-bearing half. A presence-and-equality check alone
# passes the moment someone adds a sixth copy stating a different number, because
# the new site is simply not in the table. So the numeral is also searched for
# across the tree, and any site stating one that is not registered is an error in
# its own right: an unregistered publisher is a value nothing holds to account.
PUBLISHED_CONSTANTS: tuple[tuple[str, str, str], ...] = (
    # (relative path, what the numeral means there, pattern with one group)
    ("SKILL.md", "finding cap", r"[Cc]ap at (\d+) findings"),
    ("shared/output-format.md", "finding cap", r"[Cc]ap reports at (\d+) findings"),
    ("shared/severity-and-rules.md", "finding cap", r"\*\*[Cc]ap at (\d+) findings:\*\*"),
    ("project-tree/shared/report-format.md", "finding cap", r"[Cc]ap at (\d+) findings;"),
    ("project-tree/phase1-language.md", "finding cap", r"cap the report at (\d+) findings"),
    # Coupled by the ledger's own stated rationale, so held to the SAME value as the
    # finding cap. `deliberate.md` declares the probe cap "equal to both the ledger's
    # printable rows and the report's finding cap"; that is a stated equality, so
    # these belong in the finding-cap group and nowhere else. Filed under their own
    # meanings they would fall outside every group and be checked by nothing, which
    # is how a declared coupling becomes an unenforced one.
    ("project-tree/shared/deliberate.md", "finding cap", r"Run-wide probe cap \| \*\*(\d+)\*\*"),
    ("project-tree/shared/deliberate.md", "finding cap", r"Capabilities per run \| \*\*(\d+)\*\*"),
    ("project-tree/shared/deliberate.md", "finding cap", r"[Cc]ap (\d+) rows,"),
    # Deliberately NOT the review cap. The evolution path's research phase returns
    # findings about an external target, not about the tree under review: a
    # different act, on a different surface, with a different reader. Registering it
    # is the point -- an unaccounted numeral is one nobody owns, and the first run of
    # this check found exactly that here. Equating it to the review cap would be the
    # bug: a reader told "15" would be misreading a file that says 10.
    ("auditandevolve/deep-research.md", "research cap", r"[Cc]ap at (\d+) findings per run"),
)

# The one coupled group. Splitting these apart would be the more flexible design
# and the wrong one: the ledger's caps are equal to the finding cap *by
# declaration*, so they belong in one equality class or the declaration is
# unenforced.
CONSTANT_GROUPS: tuple[str, ...] = ("finding cap", "research cap")


# Every file in the evolution path is classified, and an unclassified file is an error.
#
# Three classes, and the third is the one that caused the hole: a file that is neither
# writable nor off-limits cannot be reasoned about, because there is no rule that says
# what happens to it. Three of these files were exactly that -- `deep-research.md`,
# `eval-design.md` and `SOURCES.md` appeared in neither the writable set nor the
# boundary -- and an auditor measuring the tree found them by grepping for the word
# "writable" and getting three hits.
#
# `procedure` means: writable between passes, read-only during the pass that uses it.
# `scripts/pass_freeze.py` enforces that mechanically by content hash, so the class is
# a statement about enforcement rather than an intention. `record` means the file is
# generated by a gate and never hand-edited. `instrument` is the measurement boundary
# and is never writable by the loop at all.
EVOLUTION_FILE_CLASSES: dict[str, str] = {
    "auditandevolve/SKILL.md": "procedure",
    "auditandevolve/deep-research.md": "procedure",
    "auditandevolve/research-sources.md": "procedure",
    "auditandevolve/deep-upsert.md": "procedure",
    "auditandevolve/skill-adherence.md": "procedure",
    "auditandevolve/eval-design.md": "procedure",
    "auditandevolve/eval-harness.md": "procedure",
    "auditandevolve/hillclimb.md": "procedure",
    "auditandevolve/SOURCES.md": "procedure",
    "auditandevolve/attempts.jsonl": "record",
    "auditandevolve/research-dispositions.jsonl": "record",
}
EVOLUTION_CLASS_VALUES = ("procedure", "record", "instrument")


def validate_evolution_files(target_dir: Path) -> list[str]:
    """No file in the evolution path may be unclassified."""
    errors: list[str] = []
    root = target_dir / "auditandevolve"
    if not root.is_dir():
        return errors
    present = {
        path.relative_to(target_dir).as_posix()
        for path in root.iterdir()
        if path.is_file() and path.suffix in (".md", ".jsonl") and not path.name.startswith(".")
    }
    for rel in sorted(present - set(EVOLUTION_FILE_CLASSES)):
        errors.append(
            f"{rel} is in the evolution path and is classified nowhere. A file that is neither "
            f"writable nor off-limits has no rule governing it, which is how an unclassified "
            f"file becomes an instruction nobody wrote on purpose. Add it to "
            f"EVOLUTION_FILE_CLASSES with a class."
        )
    for rel, klass in sorted(EVOLUTION_FILE_CLASSES.items()):
        if klass not in EVOLUTION_CLASS_VALUES:
            errors.append(f"{rel} has class {klass!r}, which is not one of {list(EVOLUTION_CLASS_VALUES)}")
    return errors


GAP_STATUSES = ("Open", "Partial", "Closed")
GAP_ROW = re.compile(r"\A\|\s*\*\*(?P<id>[GN]\d+)\*\*\s*\|")
CLOSURE_DATED = re.compile(r"\d{4}-\d{2}-\d{2}")
# Phrases this register uses when a cell is arguing against its own status. Mechanical by
# construction: they are the register's words, not a judgement about prose.
CONTRADICTS_CLOSED = (
    "CLOSURE UNDATED",
    "Partial until",
    "REOPENED",
    "Narrowed, not closed",
    "narrowed, not closed",
    "still open",
    "remains open",
)
# Deliberately absent: "was never open as stated". It reads like a contradiction and is the
# opposite -- it is a justification for closing, and a rule that flagged it would have to be
# loosened the first time a row was closed for the right reason. The rule earns its keep by
# catching prose that argues against its own status, not prose that explains it.
# Lines of a pipe table that are neither the header, the rule, nor a well-formed row are
# fragments -- the residue of a paragraph pasted into a cell, which splits the row across
# physical lines and leaves the register describing a row that no longer parses as one.
TABLE_ALLOWED = re.compile(r"\A\|(?:\s*:?-{2,}:?\s*\|)+\s*\Z|"
                           r"\A\|\s*id\s*\|")


# A machine path in committed evidence names the machine, the run, and -- for a home
# directory -- the operator. All three were committed here: review bodies quoting the
# temporary directory a workspace was staged into, and plumbing `reads` arrays holding the
# operator's home, recorded verbatim by runs that reached into the real tree. The fact of
# the read is the evidence; the prefix it arrived with is not, and it is the prefix that
# travels.
MACHINE_PATH_PATTERNS = (
    (re.compile(r"/Users/[A-Za-z0-9._-]+"), "a home directory, which names the operator"),
    (re.compile(r"/private/var/folders/"), "a per-user temporary directory"),
    (re.compile(r"/var/folders/"), "a per-user temporary directory"),
    (re.compile(r"/private/tmp/[A-Za-z0-9._-]+"), "a temporary directory"),
    # A macOS per-user temporary root also exists without the `/private` prefix, and its
    # `<uid>/<per-user hash>` components identify the machine and the account even after the
    # prefix is stripped. The first version of this rule missed exactly that.
    (re.compile(r"/var/folders/[0-9]+/[A-Za-z0-9]+/"), "a per-user temporary root"),
    (re.compile(r"<tmp>/[0-9]+/[A-Za-z0-9]{8,}"), "a per-user temporary hash behind a rewrite"),
)
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}
# `probe/` holds run workspaces and scratch. It is gitignored and never published, but
# several rules in this file walked the tree without consulting .gitignore, so one
# leftover workspace reported a dozen phantom violations -- duplicate published
# constants, retired codes, a vendor name -- none of which were in the repository. A
# gate that cries wolf over a scratch directory gets switched off, and this one had
# been quietly disagreeing with itself about what it scans.
SCAN_SKIP = SKIP_DIRS | {"probe"}


# A status asserted in prose about a row that exists in the table. The register carried a
# preamble saying one row was closed while the row itself said undated and Partial, and no
# rule looked at prose at all -- the same class as the orphan fragment, one level further
# out. Mechanical by construction: the pattern is the register's own phrasing.
ROW_STATUS_CLAIM = re.compile(r"\*\*(?P<id>[GN]\d+)\*\*\s+is\s+\*\*(?P<status>[A-Za-z]+)\*\*")


def validate_status_claims(register_text: str, statuses: dict) -> list[str]:
    errors: list[str] = []
    for claim in ROW_STATUS_CLAIM.finditer(register_text):
        gid, claimed = claim.group("id"), claim.group("status").capitalize()
        actual = statuses.get(gid)
        if actual is None or claimed == actual:
            continue
        errors.append(
            f"named-gaps.md: prose says {gid} is {claimed} but its row says {actual}. A "
            f"register that contradicts itself in two places is a register nobody can cite."
        )
    return errors


def _ignore_matcher(target_dir: Path):
    """Decide from .gitignore what would actually be published.

    The scan has to match publication, not the filesystem. `evals/**/events.jsonl` and
    most of `docs/` sit on disk and are deliberately not committed, so scanning the tree
    wholesale reported dozens of hits in files that were never going to be public -- noise
    in a gate is how a gate gets ignored. Reading .gitignore rather than hard-coding the
    list keeps the two from drifting apart, and works in a copy with no .git present.
    """
    patterns: list[tuple[bool, str]] = []
    gi = target_dir / ".gitignore"
    if gi.is_file():
        for line in gi.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            negated = line.startswith("!")
            patterns.append((negated, line.lstrip("!")))
    if not patterns:
        return lambda rel: False

    def ignored(rel: str) -> bool:
        # A leading slash anchors at the tree root, so `/docs` means the directory and
        # everything under it -- which a plain fnmatch against `docs` misses entirely.
        # That bug reported three untracked research reports as publication leaks.
        verdict = False
        for negated, pat in patterns:
            p = pat.lstrip("/")
            hit = (rel == p
                   or rel.startswith(p + "/")
                   or fnmatch.fnmatch(rel, p)
                   or fnmatch.fnmatch(rel, p + "/*")
                   or (not pat.startswith("/")
                       and fnmatch.fnmatch(rel, "*/" + p)))
            if hit:
                verdict = not negated
        return verdict

    return ignored


def validate_portable_evidence(target_dir: Path) -> list[str]:
    """No committed file may carry a path that is only true on this machine.

    Scans the whole tree rather than the evidence directory, because the first instance was
    in a review body and the second in a plumbing record, and a rule scoped to one of them
    would have passed the other. Anything skipped is skipped by directory name only, so a
    new evidence format cannot escape by living somewhere unanticipated.
    """
    errors: list[str] = []
    ignored = _ignore_matcher(target_dir)
    for path in sorted(target_dir.rglob("*")):
        if not path.is_file() or set(path.parts) & SCAN_SKIP:
            continue
        rel = path.relative_to(target_dir).as_posix()
        if ignored(rel):
            continue
        # The harness and its tests may name a machine path in order to detect one: the
        # pattern tables, the portable-path helpers and the tests that assert on them all
        # contain the literals by necessity. Flagging a rule for containing its own
        # pattern is how a rule gets switched off, and the first run of this did exactly
        # that -- 6 of its 26 hits were its own source. Code may name the pattern; data
        # may not carry the path.
        if rel.startswith(("scripts/", "tests/")):
            continue
        if path.suffix not in (".json", ".jsonl", ".md", ".py", ".txt", ".yaml", ".yml"):
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(target_dir).as_posix()
        for pattern, why in MACHINE_PATH_PATTERNS:
            hit = pattern.search(body)
            if hit:
                line = body[: hit.start()].count("\n") + 1
                errors.append(
                    f"{rel}:{line} carries {why}: {hit.group(0)!r}. Evidence must be "
                    f"portable -- record ws/, repo/ or outside/ instead of a path that "
                    f"exists on one machine."
                )
    return errors


def validate_named_gaps(target_dir: Path) -> list[str]:
    """The adoption test is only as real as the register it cites.

    An idea lands when it closes a *named, cited* gap. That makes this file the
    citation list for the rule -- and it was ignored by `.gitignore` and referenced by
    nothing in `scripts/` or `tests/`. So every "closes G7" claim in this history cited a
    row present on one machine and in no clone: the test was unverifiable by construction
    while reading as though it were enforced.

    Three checks, each of a failure that actually happened here:

    The register must be tracked. A citation list in an ignored directory is a private
    list, and the adoption test then has nothing a second reader can check.

    Every row must be well formed. A paragraph pasted into a table cell splits it across
    physical lines and the row stops being a row -- which is how the G7 rewrite landed
    as a 3-column fragment before this rule existed.

    A closed row must be dated. G7 was marked CLOSED while its own text said the audit
    "has never itself been audited." This cannot detect that sentence, but requiring a
    date at least forces a closure to claim a day, and a claim about a day is falsifiable
    in a way "CLOSED" is not.
    """
    errors: list[str] = []
    reg = target_dir / "docs" / "named-gaps.md"

    ignores = target_dir / ".gitignore"
    unignored = False
    if ignores.is_file():
        unignored = any(line.strip() == "!/docs/named-gaps.md"
                        for line in ignores.read_text(encoding="utf-8").splitlines())
    if not unignored:
        errors.append(
            "docs/named-gaps.md is not un-ignored in .gitignore. The register is the "
            "citation list for the adoption test; ignored, every claim that a change "
            "closes a named gap cites a row no other reader can see."
        )
    if not reg.is_file():
        errors.append(
            "docs/named-gaps.md is missing. Without it a gap cannot be named, and an "
            "adoption cannot cite one."
        )
        return errors

    statuses: dict = {}
    seen: dict[str, int] = {}
    for n, raw in enumerate(reg.read_text(encoding="utf-8").splitlines(), 1):
        m = GAP_ROW.match(raw)
        if not m:
            if "|" in raw and not TABLE_ALLOWED.match(raw):
                errors.append(
                    f"{reg.name}:{n}: a table line that is not a well-formed row "
                    f"({raw.strip()[:48]!r}). A paragraph pasted into a cell splits the "
                    f"row across physical lines, and a fragment is invisible to every "
                    f"other rule here because it matches no row."
                )
            continue
        gid = m.group("id")
        # Split on unescaped pipes only: a cell may legitimately contain `\|`.
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", raw)][1:-1]
        if len(cells) != 4:
            errors.append(
                f"{reg.name}:{n}: row {gid} has {len(cells)} columns, expected 4. A "
                f"paragraph pasted into a cell splits the row across physical lines and "
                f"it stops being a row."
            )
            continue
        if gid in seen:
            errors.append(f"{reg.name}:{n}: {gid} is already defined at line {seen[gid]}")
        seen[gid] = n
        _, cited, gap, status = cells
        if status not in GAP_STATUSES:
            errors.append(
                f"{reg.name}:{n}: {gid} has status {status!r}; expected one of "
                f"{list(GAP_STATUSES)}"
            )
        statuses[gid] = status
        if not cited:
            errors.append(f"{reg.name}:{n}: {gid} cites no location, so the row is not traceable")
        if status == "Closed":
            if not CLOSURE_DATED.search(gap):
                errors.append(
                    f"{reg.name}:{n}: {gid} is Closed but carries no date. A closure has to "
                    f"claim a day; that is what makes it checkable."
                )
            # A date makes a closure falsifiable; it does not make it true. This register
            # has closed a row on reachability while its own cell said the audit had never
            # happened, so a date alone is not sufficient evidence. The markers below are
            # this register's own vocabulary, which is what makes the check mechanical
            # rather than a judgement: each phrase appears in a cell that is arguing
            # against its own status. A subtler contradiction -- a cell that admits
            # defeat in words this list does not contain -- stays a human's call, and
            # pretending otherwise would be the same overclaim in the other direction.
            for marker in CONTRADICTS_CLOSED:
                if marker in gap:
                    errors.append(
                        f"{reg.name}:{n}: {gid} is Closed but its own text says "
                        f"{marker!r}. A row cannot close itself by arguing that it is not "
                        f"closed."
                    )
                    break
    errors.extend(validate_status_claims(reg.read_text(encoding="utf-8"), statuses))
    return errors


def validate_retired_codes(target_dir: Path) -> list[str]:
    """A retired code may be cited by evidence, and by a tombstone. Nothing else.

    Two classes, because they are different objects. A stored review is a record of what
    a reviewer produced while the code was live -- 40 of them cite `A5`, 65 times, and
    rewriting any of those would be falsifying evidence. A *live* instruction file is a
    claim about what is true now, and a finding that cites a retired number sends the
    reader to an axis the registry no longer defines.

    The axis tables already forbid inventing a code and say a code absent from the file
    does not exist. A *retired* code is a third thing: present, marked retired, and
    uncitable -- so `Never invent a code` does not catch it, and 65 stored citations
    show the pattern is in circulation.

    A live file may still name a retired code, in exactly one way: the tombstone. The
    migration has to be recorded somewhere or a reader cannot tell which of the two
    classes they are in, and `axis-codes.md` is explicit that the number was retired
    rather than renumbered. So a retired code is permitted on a line that says so.

    The set is derived from the table rather than hardcoded, so retiring a code is caught
    without a second edit here.
    """
    codes_file = target_dir / "shared" / "axis-codes.md"
    if not codes_file.is_file():
        return []
    retired = set()
    for line in codes_file.read_text(encoding="utf-8", errors="replace").splitlines():
        row = re.match(r"\|\s*\*([A-Z]\d+)\*\s*\|\s*\*(retired|unassigned)\*\s*\|", line)
        if row and row.group(2) == "retired":
            retired.add(row.group(1))
    if not retired:
        return []

    errors: list[str] = []
    pattern = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(sorted(retired)) + r")(?![A-Za-z0-9])")
    for doc in sorted(target_dir.rglob("*.md")):
        if not doc.is_file():
            continue
        rel = doc.relative_to(target_dir).as_posix()
        if set(doc.parts) & SCAN_SKIP:
            continue
        # Recorded evidence keeps its record. That is what it recorded. `evals/README.md`
        # is in that class -- its fixture matrix says "1 x MAJOR A5" to record what a past
        # eval asserted, which is history, and history is not guidance.
        #
        # `evals/evals.json` is deliberately NOT exempt. It is live: its assertions tell a
        # reviewer what to look for, so a retired code there is a live citation.
        if rel.startswith("evals/iteration-") or rel == "evals/README.md" \
                or rel.startswith("docs/"):
            continue
        # The registry is where a retired code is documented, named and mapped, so it is
        # the one file that must be able to say the word. Exempting it by path is the same
        # shape as exempting this validator and its test from the vendor scan: a blocklist
        # and its registry have to spell out what they forbid.
        if rel == "shared/axis-codes.md":
            continue
        for number, line in enumerate(doc.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if not pattern.search(line):
                continue
            if "retired" in line.lower() or "\u2192" in line or "->" in line:
                continue
            errors.append(
                f"{rel}:{number} cites a retired axis code ({pattern.search(line).group(1)}). "
                f"Retired codes are {sorted(retired)} and exist only as tombstones and as "
                f"what older evidence recorded. Map it to its live code by subject, not "
                f"mechanically -- see axis-codes.md. The retirement table is where this set "
                f"comes from, so retiring a code needs no second edit."
            )

    # evals/evals.json is live and is not markdown, so the scan above never reaches it.
    # Its assertions tell a reviewer what to look for, which is guidance -- so a retired
    # code there is a live citation and needs the same refusal. Checked structurally rather
    # than by grepping the file, so a retired code quoted inside an unrelated field (a
    # finding's recorded text, say) is not mistaken for the assertion itself.
    spec = target_dir / "evals" / "evals.json"
    if spec.is_file():
        try:
            doc = json.loads(spec.read_text(encoding="utf-8"))
        except Exception:
            doc = {}
        for item in doc.get("evals", []) if isinstance(doc, dict) else []:
            live = list(item.get("assertions", []) or [])
            expected = item.get("expected_output")
            live += list(expected) if isinstance(expected, list) else [expected] if isinstance(expected, str) else []
            for text in live:
                hit = pattern.search(str(text))
                if hit:
                    errors.append(
                        f"evals/evals.json: eval {item.get('id')} asserts against retired axis "
                        f"code {hit.group(1)}. Assertions are live guidance -- a reader follows "
                        f"them -- so this is a live citation, unlike the fixture matrix that "
                        f"records what a past eval asserted. Map it by subject; see axis-codes.md."
                    )
    return errors


def validate_published_constants(target_dir: Path) -> list[str]:
    """Every publication of a coupled numeral must state the same number."""
    errors: list[str] = []

    seen: dict[str, list[tuple[str, str]]] = {}
    for rel, meaning, pattern in PUBLISHED_CONSTANTS:
        doc = target_dir / rel
        if not doc.is_file():
            # A site that moved is as much a drift as a site that disagrees. The
            # table is the contract, so a silent move is a failure, not a skip.
            errors.append(
                f"published constant: {rel} is listed as a publication site for the "
                f"{meaning} but the file was not found. The numeral's sites are a "
                f"declared table; if it moved, update the table in the same change."
            )
            continue
        match = re.search(pattern, doc.read_text(encoding="utf-8"), re.IGNORECASE)
        if not match:
            errors.append(
                f"published constant: {rel} no longer states the {meaning} in the form "
                f"the table expects ({pattern!r}). Either the wording moved or the site "
                f"was deleted -- both leave the numeral held to account by fewer files."
            )
            continue
        seen.setdefault(meaning, []).append((rel, match.group(1)))

    for meaning in CONSTANT_GROUPS:
        sites = seen.get(meaning, [])
        values = {v for _, v in sites}
        if len(values) > 1:
            rendered = ", ".join(f"{rel}={v}" for rel, v in sites)
            errors.append(
                f"published constant: the {meaning} is stated as more than one value "
                f"across its publication sites ({rendered}). Every file reads "
                f"correctly alone, which is why only a cross-file comparison can see "
                f"this. Pick one value and correct the rest in the same change."
            )
        elif not sites:
            errors.append(
                f"published constant: no publication site for the {meaning} was found, "
                f"so the numeral is unchecked."
            )

    # The extras clause. Search the tree for a numeral statement the table does not
    # register, so adding a copy is an error rather than a silent second source of
    # truth.
    #
    # A registered pattern that is a *prefix* of a broader one still claims its span:
    # "cap at 10 findings per run" matches both the research-cap pattern and the
    # generic findings-cap pattern, and without span subtraction the registered site
    # would be reported as an unregistered publisher of itself.
    by_path: dict[str, list[tuple[str, re.Pattern[str]]]] = {}
    for rel, meaning, pattern in PUBLISHED_CONSTANTS:
        by_path.setdefault(rel, []).append((meaning, re.compile(pattern, re.IGNORECASE)))

    for path in sorted(target_dir.rglob("*.md")):
        rel = path.relative_to(target_dir).as_posix()
        if rel.startswith("docs/") or set(path.parts) & SCAN_SKIP:
            continue
        body = path.read_text(encoding="utf-8", errors="replace")
        claimed: list[tuple[int, int]] = [
            m.span() for _, rx in by_path.get(rel, []) for m in rx.finditer(body)
        ]
        for meaning, pattern in (
            ("finding cap", r"[Cc]ap (?:at |the report at |reports at )?(\d+) findings"),
            ("research cap", r"[Cc]ap at (\d+) findings per run"),
        ):
            for match in re.finditer(pattern, body):
                if any(s <= match.start() < e for s, e in claimed):
                    continue
                errors.append(
                    f"published constant: {rel} states a {meaning} of {match.group(1)} "
                    f"but is not a registered publication site. An unregistered "
                    f"publisher is a value nothing holds to account -- register it in "
                    f"PUBLISHED_CONSTANTS, or delete the statement."
                )
    return errors


# The harness is the interesting case. It cannot avoid *depending* on a session
# runner -- it has to invoke one -- so the runner is named by the operator
# through an environment variable and no tool appears in the source. That is
# better design as well as a cleaner tree: the harness is no longer welded to
# whichever tool it happened to be written against.
#
# Structured as a suffix test over a token rather than a fixed list, so adding a
# vendor means extending the check, not rewriting it.
# Whole tokens: a vendor, provider, product or harness name. Word-bounded on both
# sides, so an ordinary technical term that merely shares a prefix is untouched.
FORBIDDEN_VENDOR_TOKENS = (
    # agent harnesses and their products
    "opencode", "claude", "codex", "copilot", "cursor-ide", "windsurf",
    "replit-agent", "aider", "continue-dev", "devin", "bolt-new",
    # model providers
    "anthropic", "openai", "google-ai", "mistral-ai", "cohere-labs",
    "aws-bedrock", "azure-openai", "vertex-ai", "deepseek-ai", "moonshot-ai",
)
# Prefixes: a model family, which continues with a version, a dot or a hyphen
# (`<family>-<version>-<variant>`). Matched on the left boundary only. A trailing
# hyphen in the token would make the right boundary see the version's first digit
# and refuse the match, which is how `<family>-<version>` slipped through an
# earlier attempt at this check.
FORBIDDEN_VENDOR_PREFIXES = (
    "gpt", "gemini", "llama", "mistral", "qwen", "deepseek", "kimi", "grok",
    "gpt4", "command-r",
)
VENDOR_SCAN_SUFFIXES = (
    ".md", ".json", ".jsonl", ".py", ".sh", ".txt", ".yaml", ".yml"
)
# Declared once and read by both the validator and its test. Recorded run evidence is a
# transcript of what a runner emitted; a ledger is a record this repository asserts.
# Same shape as the `docs/` exemption: attribution is not disclosure, but only where the
# exemption is written down rather than remembered.
VENDOR_EXEMPT_PREFIXES = ("docs/", "evals/iteration-")

# External references that are permitted to appear as URLs.
#
# The tree names no vendor in prose. It does cite published guidance, and a
# citation is a URL whose host and path happen to contain the vendor's name.
# That is provenance -- the same category as an alignment report's source
# list -- so it is allowed, and only in that form.
#
# The allowance is deliberately narrow, and the narrowness is the whole design:
#
#   * It is a declared prefix list, not a pattern. A generic `https?://\S*`
#     exemption would let anyone launder a vendor name by pasting it into a
#     URL, which is a strictly larger hole than the one being closed.
#   * It is SPAN-scoped, not file-scoped. The token is excused only when it
#     falls inside the characters of a URL beginning with a declared prefix.
#     The same word in the same file, one sentence away, is still a violation.
#     So `auditandevolve/SOURCES.md` may hold the links and may not hold the
#     prose, which is the correct way round: the reference is the citation,
#     the prose would be a disclosure.
#   * Prefixes are full host-and-path, so `github.com/anthropics/skills` is
#     allowed and a lookalike repository one directory over is not.
#
# Adding an entry here is a claim that the source is citable. Do not add one
# to silence a scan; that inverts what the scan is for.
REFERENCE_URL_PREFIXES = (
    "https://github.com/anthropics/skills/",
    "https://platform.claude.com/docs/",
    "https://code.claude.com/docs/",
    "https://docs.claude.com/",
    "https://claude.dev/blog/",
    "https://www.anthropic.com/",
)

def _reference_spans(text: str) -> list[tuple[int, int]]:
    """Character ranges occupied by a permitted reference URL."""
    spans: list[tuple[int, int]] = []
    low = text.lower()
    for prefix in REFERENCE_URL_PREFIXES:
        start = 0
        while (idx := low.find(prefix, start)) != -1:
            end = idx
            while end < len(text) and not text[end].isspace() and text[end] not in ")\"'":
                end += 1
            spans.append((idx, end))
            start = idx + len(prefix)
    return spans

def vendor_hit(text: str) -> str | None:
    low = text.lower()
    spans = _reference_spans(text)
    for token in FORBIDDEN_VENDOR_TOKENS:
        # Word-bounded, so "cursor" in a database call and "aid" in a word do not
        # match; a vendor name is a whole token.
        for match in re.finditer(
            r"(?<![a-z0-9])" + re.escape(token) + r"(?![a-z0-9])", low
        ):
            if any(s <= match.start() < e for s, e in spans):
                continue  # inside a declared reference URL: provenance, not disclosure
            return token
    for prefix in FORBIDDEN_VENDOR_PREFIXES:
        for match in re.finditer(r"(?<![a-z0-9])" + re.escape(prefix), low):
            if any(s <= match.start() < e for s, e in spans):
                continue
            return prefix
    return None


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("Usage: python scripts/validate_skill.py [TARGET_DIR]")
        print("\nValidates se-review against the 3-tier hierarchy (Root -> Domains -> Domain (leaf.md) -> Sub-Domains (sub-leaf.md)):")
        print("Arguments:")
        print("  TARGET_DIR   Root skill dir, specific domain dir, or specific sub-domain dir (default: project root)")
        print("  -h, --help   Show this help message and exit")
        return 0

    target_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent

    print(f"Validating target: {target_dir}")

    all_errors = []

    sh_dir = target_dir / "shared"
    root_md = target_dir / "SKILL.md"
    honesty = {
        "output-format.md": (
            "verified by",          # the evidence axis on every finding
            "always printed",       # fixed slots: Gated by / Covered
            "cut by 15-cap",        # cut disclosed with real composition
            "excluded by --min",    # cap and reader filter are different acts
            "not examined",         # the coverage denominator
        ),
        "severity-and-rules.md": (
            "confidence is a cap on severity",  # not a discount
        ),
        # The evolution wire. Each of these is an injection control on a path
        # that runs from a codebase under review -- often an adversarial one --
        # into something that shapes future behaviour. A control that cannot fail
        # is decoration, so each is checked for presence.
        "evolution-candidates.md": (
            "one-way and inert",       # candidates are notes, never applied
            "never names a file to edit",  # no file, line, or wording in a candidate
            "loaded by the orchestrator",   # not by an agent, brief, or judge
            "capped",                  # three per gap per run
        ),
        "domain-fanout.md": (
            "discovery fans out. severity never does",  # the load-bearing split
            "serial ceiling",           # fan-out is threshold-gated, not default
            "own the score",            # agents never return a score
            "boundaries",               # the trust-boundary primitive is carried, not described
        ),
        "axis-codes.md": (
            # The whole heading, not the bare string: a single cross-reference
            # satisfies "a5 → s" while the migration table itself is gone, which is
            # a weak gate that reads as a strong one.
            "a5 → s: the security migration",
            "was `a5` inside correctness and is now the `s` series",
            # A5 must be marked *retired* in the A-series table, not merely absent.
            # A gap in that table reads as "unassigned, claimable", which is how a
            # retired code gets handed to a new sub-domain and silently changes
            # what every stored verdict citing it means.
            "| *a5* | *retired*",
        ),
    }
    for rel, needles in honesty.items():
        doc = sh_dir / rel
        if not doc.is_file():
            continue
        body = doc.read_text(encoding="utf-8").lower()
        missing = [n for n in needles if n.lower() not in body]
        if missing:
            all_errors.append(
                f"shared/{rel} is missing a load-bearing invariant: {'; '.join(missing)}"
            )

    all_errors.extend(validate_published_constants(target_dir))
    all_errors.extend(validate_portable_evidence(target_dir))
    all_errors.extend(validate_named_gaps(target_dir))
    all_errors.extend(validate_evolution_files(target_dir))
    all_errors.extend(validate_retired_codes(target_dir))

    # A conditionally-printed header field, or a cut note that asserts a
    # composition rather than counting it, are both regressions to a specific
    # known-bad state rather than merely absent rules.
    of = (sh_dir / "output-format.md")
    if of.is_file():
        body = of.read_text(encoding="utf-8")
        if "omit the line" in body.lower():
            all_errors.append(
                "shared/output-format.md conditionally omits a header field; a field "
                "printed only when it binds makes a truncated report read as clean"
            )
        if "all Minor or Info" in body and "false statement" not in body:
            all_errors.append(
                "shared/output-format.md asserts a cut composition it cannot know; "
                "the cut must be counted, not assumed"
            )

    # A candidate that reached a brief or a judge would be an injection sink: the
    # brief decides what an agent looks for, and the judge decides the score.
    # Checked across the whole tree rather than in one file, because the leak
    # would appear wherever the rule was restated.
    if sh_dir.is_dir():
        for doc in sorted(sh_dir.glob("*.md")) + sorted((target_dir / "auditandevolve").glob("*.md")):
            body = doc.read_text(encoding="utf-8").lower()
            for sink in ("brief carries a candidate", "judge reads the candidate",
                         "candidate in the brief", "dispatch the candidate"):
                if sink in body:
                    all_errors.append(
                        f"shared/{doc.name} appears to route a candidate into a brief "
                        f"or a judge ('{sink}'); candidates are read by the orchestrator only"
                    )

    # A committed verdict is evidence about the skill. Recording which model
    # produced it makes the evidence about the harness instead, and publishes a
    # vendor, a version and a tier identifier into a repository whose instruction
    # files deliberately name no vendor at all.
    #
    # Six pattern-based rules were tried for the free-text case and every one of them
    # fired on this repository's own content: `sub-domains/trust-boundaries`,
    # `pattern/anti-pattern`, a MIME type in a fixture, a supply-chain fixture's
    # `actions/setup-node`. A text pattern for "looks like a model id" cannot be made
    # precise here, and a check that fails on legitimate paths is a check that gets
    # ignored -- worse than not having it.
    #
    # So the check is structural, on the thing that actually leaked. Every model id
    # that reached disk did so as the *value* of a `model` or `judge_model` key.
    #
    # Two rules, both exact:
    #   1. evidence JSON carries no identity key
    #   2. a `*_config` key carries a digest, not a name
    # No vendor, provider, product or tool name anywhere in a tracked file. Not a
    # model, not the runner, not a vendor filename convention: this repository names
    # none of them, in instruction files, in prose, in examples or in evidence.
    #
    for path in sorted(target_dir.rglob("*")):
        if not path.is_file() or path.suffix not in VENDOR_SCAN_SUFFIXES:
            continue
        parts = set(path.parts)
        if parts & SCAN_SKIP:
            continue
        # Recorded run evidence is exempt by DIRECTORY, not by filename. It used to be
        # exempt by the single name `events.jsonl`, which was too narrow twice over: a
        # second recorded artefact (`judge_stream.jsonl`) was therefore scanned as if it
        # were an instruction file, and -- the reason this changed -- a `.jsonl` ledger
        # would have held unscanned provenance, because `.jsonl` was not in the suffix
        # list at all. A transcript of a run is evidence of what a runner emitted; a
        # ledger is a record this repository asserts. Same shape as the `docs/` exemption
        # below: attribution is not disclosure, but only where the exemption is declared.
        rel = path.relative_to(target_dir).as_posix()
        # Assigned first, tested second. This was the other way round, so the exemption
        # was applied to whatever `rel` the *previous* iteration left behind -- a gate
        # policed by ordering, using a stale value. It never fired on the file being
        # scanned, and the test that should have caught it re-implements the scan
        # correctly rather than calling this loop, so deleting the loop left the suite
        # green.
        if rel.startswith(VENDOR_EXEMPT_PREFIXES):
            continue
        if rel in ("scripts/validate_skill.py", "tests/test_run_evals.py"):
            # The scanner and its test both spell out the blocklist, because a
            # blocklist has to. Neither is a disclosure of what was used, and
            # exempting exactly these two keeps every other file -- including the
            # rest of this one -- scanned.
            continue
        if rel.startswith("docs/"):
            # Untracked working notes may cite upstream repositories by name; that is
            # attribution, and it is exactly what an alignment report is for.
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        token = vendor_hit(body)
        if token:
            line = body.lower().find(token) 
            all_errors.append(
                f"{rel} names a vendor, provider or product ('{token}'). This repository "
                f"names none: instruction files, examples and evidence must all be "
                f"tool-agnostic. A harness that must invoke a runner takes it from the "
                f"environment instead of hardcoding one."
            )

    FORBIDDEN_EVIDENCE_KEYS = {"model", "judge_model", "model_id", "judge_model_id"}
    CONFIG_DIGEST = re.compile(r"\A(cfg:[0-9a-f]{8,}|unpinned)\Z")

    for path in sorted(target_dir.rglob("evals/**/*.json")):
        if not path.is_file() or set(path.parts) & SCAN_SKIP:
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        rel = path.relative_to(target_dir).as_posix()
        for key in sorted(FORBIDDEN_EVIDENCE_KEYS & set(doc)):
            all_errors.append(
                f"{rel} records '{key}'; use '{key}_config', a digest, so two verdicts "
                f"can be compared for comparability without naming what ran"
            )
        for key, value in sorted(doc.items()):
            if not key.endswith("_config") or not isinstance(value, str):
                continue
            if not CONFIG_DIGEST.match(value):
                all_errors.append(
                    f"{rel}: '{key}' is not a digest (expected 'cfg:<hex>' or 'unpinned'), "
                    f"so it is recording an identity rather than a configuration handle"
                )

    # The arbitration rule must resolve by demonstrated ownership, not by volume.
    # Scoped to root mode: a domain or sub-domain target has no SKILL.md, and a
    # Path is always truthy, so an unguarded read here crashes the validator on a
    # perfectly valid domain directory instead of skipping a root-only rule.
    if root_md.is_file() and "the higher grade stands" in root_md.read_text(encoding="utf-8"):
        all_errors.append(
            "SKILL.md Phase 5 resolves cross-domain grade disagreement by taking the "
            "higher grade, which is arbitrable by escalation; it must resolve by owner"
        )

    # 1. Determine execution mode: Root, Domain, or Sub-domain
    if (target_dir / "SKILL.md").is_file():
        mode = "root"
        entry_file = target_dir / "SKILL.md"
        metadata, body, fm_errors = validate_frontmatter(entry_file)
        skill_name = metadata.get("name", "se-review")
        all_errors.extend(fm_errors)
        all_errors.extend(check_markdown_backticks(entry_file))

        # Validate shared
        all_errors.extend(validate_shared(target_dir / "shared"))

        # Validate references in SKILL.md, including the progressive-disclosure
        # rules (spec: file references, one level deep). One validator only - an
        # earlier inline regex here was a strict subset of this one and reported
        # the same missing path twice in two different formats.
        all_errors.extend(validate_skill_refs(target_dir, entry_file, body))
        # Sibling sub-skills must also satisfy the Agent Skills spec.
        for sub in ("project-tree", "auditandevolve"):
            sub_entry = target_dir / sub / "SKILL.md"
            if sub_entry.is_file():
                _, _, sub_errs = validate_frontmatter(sub_entry)
                all_errors.extend(sub_errs)
                all_errors.extend(check_markdown_backticks(sub_entry))

        # Dynamically discover domains under domains/
        domains_dir = target_dir / "domains"
        if not domains_dir.is_dir():
            all_errors.append(f"Missing domains directory: {domains_dir}")
            discovered_domains = []
        else:
            discovered_domains = sorted([d for d in domains_dir.iterdir() if d.is_dir() and (d / "leaf.md").is_file()])

        if not discovered_domains:
            all_errors.append(f"No valid domain directories with leaf.md found in {domains_dir}")

        total_subdomains = 0
        total_guidelines = 0
        domain_names = []

        for ddir in discovered_domains:
            domain_names.append(ddir.name)
            subs, guides, d_errs = validate_domain(ddir)
            total_subdomains += subs
            total_guidelines += guides
            all_errors.extend(d_errs)

        # Validate evals
        all_errors.extend(validate_evals(target_dir, skill_name))

        # Validate the project-tree conformance sub-skill
        pt_errors = validate_projecttree(target_dir / "project-tree")
        all_errors.extend(pt_errors)
        pt_present = (target_dir / "project-tree").is_dir()

        print("\n--- Validation Results ---")
        print(f"Name:              {skill_name}")
        print(f"Mode:              Dynamic Root Orchestrator (SKILL.md)")
        print(f"Description:       {len(metadata.get('description', ''))} chars")
        print(f"Domains active:    {len(domain_names)} ({', '.join(domain_names)})")
        print(f"Sub-domains:       {total_subdomains} sub-domains across all domains")
        print(f"Guideline files:   {total_guidelines} lean defect guideline documents")

        evals_path = target_dir / "evals" / "evals.json"
        if evals_path.is_file():
            try:
                count = len(json.loads(evals_path.read_text(encoding="utf-8")).get("evals", []))
                print(f"Eval cases:        {count} test fixtures")
            except Exception:
                pass

        if pt_present:
            pt_dir = target_dir / "project-tree"
            profiles = [p for p in (pt_dir / "profiles").glob("*.md")
                        if p.name != "README.md"]
            intents = [p for p in (pt_dir / "intent").glob("*.md")
                       if p.name not in ("README.md", "INDEX.md")]
            print(
                f"Conformance skill: project-tree (3 phases, "
                f"{len(profiles)} technology profiles, {len(intents)} intent artifacts)"
            )

    elif (target_dir / "leaf.md").is_file():
        mode = "domain"
        entry_file = target_dir / "leaf.md"
        metadata, _, fm_errors = validate_frontmatter(entry_file)
        domain_name = metadata.get("name", target_dir.name)
        all_errors.extend(fm_errors)
        subs, guides, d_errs = validate_domain(target_dir)
        all_errors.extend(d_errs)

        print("\n--- Validation Results ---")
        print(f"Name:              {domain_name}")
        print(f"Mode:              Standalone Domain Orchestrator (leaf.md)")
        print(f"Description:       {len(metadata.get('description', ''))} chars")
        print(f"Sub-domains:       {subs}")
        print(f"Guideline files:   {guides}")

    elif (target_dir / "sub-leaf.md").is_file():
        mode = "sub-domain"
        guides, s_errs = validate_subdomain(target_dir)
        all_errors.extend(s_errs)

        print("\n--- Validation Results ---")
        print(f"Name:              {target_dir.name}")
        print(f"Mode:              Standalone Sub-Domain Evaluator (sub-leaf.md)")
        print(f"Guideline files:   {guides}")

    else:
        print(f"Error: Target {target_dir} is neither a skill root, domain, nor sub-domain directory.")
        return 1

    if all_errors:
        print(f"\nFAILED with {len(all_errors)} error(s):")
        for err in all_errors:
            print(f"  [ERROR] {err}")
        return 1

    print("\nPASSED: Skill structure, domains, sub-domains, guidelines, and evals are 100% compliant with the hierarchy specification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
