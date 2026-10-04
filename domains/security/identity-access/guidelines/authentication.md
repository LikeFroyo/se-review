# Authentication — credential storage, session lifecycle, and login throttling

Audit how credentials are stored, how sessions are created and destroyed, and what stands between an attacker and unlimited login attempts.

## Credential storage

- **Fast hash for a password:** `md5`, `sha1`, or `sha256` used to store a credential, or a slow KDF absent, so a stolen table is cracked at commodity-GPU speed.
- **No per-credential salt:** One salt for the whole table, a salt derived from the username, or a hand-rolled digest in place of a library that manages salts.
- **Weak or absent work factor:** Iteration counts left at a library default, a bcrypt cost below 10, or an algorithm chosen because it is fast rather than memory-hard.
- **Predictable secret material:** Session IDs, reset codes, or activation codes drawn from `random`/`Math.random` instead of a CSPRNG, or tokens carrying under 128 bits of entropy.

## Session lifecycle

- **Session not regenerated at login:** An identifier that exists before authentication and survives it, so a session ID planted beforehand is authenticated by the victim's own login.
- **Termination that only clears the client:** Logout or "sign out everywhere" that drops the cookie or the access token while the server-side session or an outstanding refresh token stays valid.
- **No invalidation on credential change:** A password change, MFA enrolment, or account disable that leaves existing sessions and refresh tokens alive.
- **No re-authentication gate on sensitive attributes:** Email, phone, MFA factor, or recovery method changed on the strength of a long-lived session alone.
- **Missing lifetime bounds:** A session with neither an idle timeout nor an absolute maximum, so a stolen token stays valid indefinitely.

## Login throttling

- **No rate limit or anti-automation:** Login, password-reset, and OTP-verification paths with no per-account or per-IP throttle, no lockout, and no backoff, so credential stuffing runs at line rate.
- **User enumeration:** Distinct messages, status codes, or response latency for "no such account" versus "wrong password", confirming which usernames are real.
