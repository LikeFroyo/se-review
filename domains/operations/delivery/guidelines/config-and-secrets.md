# Configuration & secrets — required settings that cannot fail open

Audit how a deployment learns its configuration, and what the process does when a value is missing.

## Fail-open defaults

- **Permissive default on a required secret:** `os.environ.get("API_KEY", "")` or an equivalent default that lets the process start and serve traffic with the credential absent or empty.
- **Security control behind a default-off flag:** TLS verification, signature validation, authentication, or authorization gated on a configuration value that defaults to disabled, so a missing setting silently removes the control.
- **Insecure default in the production profile:** A `DEBUG`, `ALLOW_INSECURE`, or `DISABLE_AUTH` default that ships because the deploy manifest does not set it — verified against the production profile, not the developer's.
- **Degraded mode on configuration loss:** A service that keeps serving on stale configuration after its config source is unreachable, instead of refusing to start.

## Rotation and provenance

- **No rotation path for a shipped secret:** A credential committed to a manifest or image with no documented way to replace it, so it is never rotated because rotating it is a release.
- **Secret in the release artifact:** A key, password, or token baked into a container image or build output rather than injected at runtime, so it is readable by anyone who can pull the image.
- **No validation of required settings at startup:** The process reads configuration lazily, so a missing required value surfaces as a `None` dereference in production rather than as a failed deploy.
