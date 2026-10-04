# Build integrity — what the build executes, from where, and on whose word

Audit everything the build runs or consumes outside the repository's own reviewed source.

## Install-time execution

- **Ungated install hooks:** `preinstall`, `install`, or `postinstall` in any resolved dependency, or a `binding.gyp` that triggers an implicit `node-gyp rebuild` — code that runs at install time with the developer's or CI runner's credentials, before a reviewer reads the lockfile diff.
- **No allowlist by resolved identity:** Scripts permitted by package *name* rather than by the lockfile's `resolved` coordinate, so an alias (`trusted@npm:naughty`) binds a malicious artifact to a trusted name.
- **Scripts enabled everywhere:** No `ignore-scripts`/allow-scripts policy in CI, so approval is neither required nor recorded.
- **Script reaches outside the package:** A lifecycle hook that fetches a remote URL or writes outside its own directory, making the executed payload independent of the pinned tarball.

## Mutable build references

- **Floating action references:** `uses: owner/repo@v1` or `@main` instead of a commit SHA, so a moved tag silently changes what the pipeline executes.
- **Floating image references:** `FROM image:latest` or a bare tag in a Dockerfile or deployment manifest, where a re-push replaces the artifact a verified build produced.
- **Unversioned or latest installs in the build:** `pip install <pkg>` with no version, `npm install x@latest`, or a base image with no digest, making the build non-reproducible.
- **Remote code piped to a shell:** `curl … | sh` or `wget … | bash` in a Dockerfile, workflow, or setup script — an unpinned download executed as part of the build.

## Absent provenance verification

- **Hash-only trust:** The pipeline verifies checksums and stops there, so a checksum proves the bytes match the lockfile but says nothing about who produced them.
- **No attestation check:** Nothing in the publish or deploy path verifies a signature or provenance (`slsa-verifier`, `cosign verify`, Sigstore), leaving the origin of a release unattested.
- **No bill of materials:** No SBOM generated or retained per release, so a newly disclosed CVE cannot be answered with "are we affected".
