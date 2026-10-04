# Access control — IDOR, BOLA, and authorization boundaries

Audit authorization checks and tenant boundary isolation.

## What to look for

- **Broken Object-Level Authorization (IDOR / BOLA):** Endpoints accepting record or resource IDs from client input and fetching/mutating database records without verifying that the requesting user owns or has permission to access that specific entity.
- **Client-trusted roles or identity:** Trusting user IDs, roles, or tenant IDs passed in request bodies or query parameters instead of deriving them from verified session tokens.
- **Missing default-deny:** Authorization frameworks that permit access by default when no explicit rule matches.
- **Horizontal privilege escalation:** Authenticated user A accessing or modifying resources belonging to authenticated user B by manipulating identifier parameters.

## Function-level authorization

- **Unguarded privileged function:** An admin or sensitive endpoint — export-all, role assignment, deletion, refund, impersonation — reachable on an ordinary authenticated session because no role or permission check runs on that route.
- **Role inferred from the URL:** Administrative protection applied by route prefix only, so a guard on `/api/admin/*` is bypassed by mounting the same handler under an ordinary prefix.
- **Method-dependent guard:** A check that reads only `GET` and `POST`, or a decorator listing allowed methods, so a `DELETE` or `PUT` on the same path is never evaluated.
- **Nested route without a check:** A controller that enforces the role check while a sub-resource route registered against it inherits authentication alone.
