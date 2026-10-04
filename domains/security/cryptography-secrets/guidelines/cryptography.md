# Cryptography — transport verification and cipher construction

Audit how cryptographic protection is established: whether the channel is authenticated, and whether the primitive and mode chosen still hold.

## Transport verification

- **Certificate validation disabled:** `verify=False`, `InsecureSkipVerify: true`, `rejectUnauthorized: false`, or a custom trust manager that accepts every certificate, leaving the channel encrypted but unauthenticated to anyone in the network path.
- **Cleartext credential transport:** An `http://` endpoint, webhook, or broker URI carrying a bearer token, session cookie, or password, readable in transit and in any proxy log.

## Primitive and mode

- **Deprecated primitive:** MD5, SHA-1, DES, three-key TDEA, or RC4 used for protection rather than as a non-security identifier.
- **ECB mode:** Block-cipher mode `"ECB"` named explicitly, or reached by a call that supplies no mode, leaking plaintext block structure and which records are equal.
- **Repeated or fixed nonce:** A hardcoded, zero, or counter-rolled IV/nonce under one key, so a GCM authentication key becomes recoverable and ciphertexts forgeable, or a counter that is not unique per key.
- **Unauthenticated or custom construction:** CBC or CTR with no MAC, a padding oracle exposed through error text, or a hand-rolled cipher, PRNG, or comparison loop instead of a vetted library.
- **Key derivation without a KDF:** A key, IV, or "salt" derived by a single pass of a fast hash over a password.
