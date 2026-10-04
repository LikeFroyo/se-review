# Token validation — signature, claim, and algorithm checks

Audit how bearer tokens and signed claims are verified on the trusting side.

## What to look for

- **Unverified decode:** Decoding a token with signature verification off (`verify=False`, `options={"verify_signature": False}`, an unverified decode middleware) and trusting the claims it returns.
- **Algorithm taken from the token:** Passing the header's `alg` into the verifier's allowed-algorithm list, or letting the header select the key, instead of pinning one algorithm at the call site.
- **Algorithm confusion:** A single verifier handling both symmetric and asymmetric tokens, so an `HS256` token is validated using the RSA public key as the HMAC shared secret.
- **`alg: none` accepted:** A denylist rather than an allowlist, a case-sensitive comparison, or an allowlist assembled at runtime that an unexpected value such as `noNE` slips past.
- **Unvalidated claims:** Accepting a token with no `exp` check, or without validating `iss` and `aud` against the values this service expects.
- **Key not bound to algorithm:** Selecting a verification key from an attacker-controlled `kid`, or one signing key reused across token kinds with no distinguishing claim or `typ` check.
- **Static secret used as a signing key:** A long-lived API key or shared secret standing in for per-session tokens.
