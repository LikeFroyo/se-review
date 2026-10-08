Reviewing the ECB fixture — inspecting code for leakage patterns.
Found the ECB flaw documented — now mapping the full evaluation context.
I've got the scoring rubric — now verifying the findings before finalizing.
# Review: `evals/fixtures/ecb_mode_cipher.py`

`4 findings · C:2 M:2 m:0 i:1 · Mean 73/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/ecb_mode_cipher.py` · Not examined: 0 — none
Paths: 2 resolved open · Unmapped: 0 — none
Unclassified: 0 findings fit no axis code
Domain Scores: Security: 40/100 · Correctness: 80/100 · Maintainability: 100/100
Gated by: `ECB deterministic encryption leaks block equality` — **always printed.**

## Findings

### [CRITICAL] ECB deterministic encryption leaks block equality and enables cut-and-paste
- **Domain:** Security (S4)
- **Verified by:** DERIVED — `encrypt_field()` → `Cipher(AES, modes.ECB())` → identical plaintext blocks yield identical ciphertext blocks; stored `base64` compared across records.
- **Evidence:** `ecb_mode_cipher.py:20` — `cipher = Cipher(algorithms.AES(MASTER_KEY), modes.ECB())` in `encrypt_field()`; same construction repeated in `decrypt_field()` at `ecb_mode_cipher.py:26`.
- **Path:** Source: repeated field values across records (states, amounts, SSNs), observable via stored ciphertext → Boundary: field-encryption layer that should hide equality/structure → Sink: identical ciphertext blocks + block splicing into another record.
- **Failure scenario:** Attacker with read access to the document store clusters records by value without the key, detects which fields repeat, and replays a ciphertext block from one record into another; decrypted by the legitimate `decrypt_field()` path.
- **Fix:** Replace with an authenticated mode: AES-GCM with fresh 96-bit nonce, or AES-CBC + HMAC with fresh IV and constant-time verify. Scope: module (`encrypt_field`/`decrypt_field` + stored-value migration / re-encryption).
- **Trade-off:** Adds nonce/IV storage per value (~12–16 B) and a re-encryption migration for existing ECB ciphertexts; GCM adds ~16 B tag and nonce-misuse sensitivity, CBC+HMAC adds two passes and separate MAC key management.

### [CRITICAL] Hardcoded static master key in source
- **Domain:** Security (S4)
- **Verified by:** DERIVED — `MASTER_KEY` literal → used directly in all three `Cipher()` constructions; rotation requires a release.
- **Evidence:** `ecb_mode_cipher.py:8` — `MASTER_KEY = b"0123456789abcdef0123456789abcdef"`.
- **Path:** Source: anyone with repo/fixture/checkout read → Boundary: source-code boundary that should never carry key material → Sink: `encrypt_field` / `decrypt_field` / `encrypt_with_random_iv` all decryptable with the committed value.
- **Failure scenario:** Key exposure is permanent and total: all past and future field ciphertexts decrypt; rotation is a code change + full re-encryption, so suspected exposure has no fast remedy.
- **Fix:** Load key from KMS / env / secret manager, add key-id + rotation path with re-encryption job. Scope: boundary (callers + deploy config + migration).
- **Trade-off:** Adds secret-distribution and versioning complexity; multi-key decrypt path needed during rotation window.

### [MAJOR] Unauthenticated encryption — malleable ciphertext, no integrity
- **Domain:** Security (S4)
- **Verified by:** DERIVED — neither `encrypt_field()` (ECB) nor reference `encrypt_with_random_iv()` (CBC, `ecb_mode_cipher.py:31-36`) computes/verifies a MAC/tag; `decrypt_field()` accepts any bit-flipped block.
- **Evidence:** `ecb_mode_cipher.py:11-28` and `ecb_mode_cipher.py:31-36` — no `HMAC`, `GCM` tag, or `compare_digest` anywhere in file.
- **Failure scenario:** Storage-layer attacker flips bits / splices blocks; tampered value decrypts to attacker-influenced plaintext with no error, consumed downstream as trusted field data.
- **Fix:** Use AES-GCM (or CBC + Encrypt-then-MAC with independent MAC key). Scope: module, same migration as ECB fix.
- **Trade-off:** Same storage overhead as above; requires constant-time tag check on decrypt and error handling that does not oracle validity.

### [MAJOR] No padding — arbitrary-length plaintext raises instead of encrypting
- **Domain:** Correctness (A8)
- **Verified by:** DERIVED — `encryptor.update(plaintext)` with raw ECB/CBC and no `PKCS7` padder; `cryptography` requires `len % 16 == 0`, so `encrypt_field(b"short")` raises `ValueError`.
- **Evidence:** `ecb_mode_cipher.py:11-22` — no `padding.PKCS7` import or `padder` use; contract claims `plaintext: bytes` with no length precondition.
- **Failure scenario:** Any field value not block-aligned crashes the write path; callers must pre-pad ad hoc, producing inconsistent stored values that fail cross-record comparison and `decrypt_field()`.
- **Fix:** Add `PKCS7(128)` pad/unpad inside encrypt/decrypt, or switch to a streaming/AEAD mode that needs none. Scope: local (this file).
- **Trade-off:** Adds one pad/unpad step per call; existing unpadded ciphertexts need versioning to stay readable.

### [INFO / SUGGESTION] Reference CBC correctly uses fresh random IV
- **Domain:** Security (S4)
- **Verified by:** READ
- **Evidence:** `ecb_mode_cipher.py:33` — `iv = os.urandom(16)` prefixed to ciphertext.
- **Fix:** Keep as the pattern for per-message randomness; promote it to the default by adding authentication per finding #3.

## Aligns well
- Docstring at `ecb_mode_cipher.py:14-19` honestly labels ECB as a vulnerability rather than presenting it as safe.