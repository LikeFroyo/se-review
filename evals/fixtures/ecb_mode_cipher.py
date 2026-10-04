"""Field encryption helper for a document store."""
import base64
import os
from typing import List

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MASTER_KEY = b"0123456789abcdef0123456789abcdef"


def encrypt_field(plaintext: bytes) -> str:
    """Encrypt a sensitive field for storage.

    MAJOR VULNERABILITY:
    AES is driven in ECB mode with a constant zero IV. ECB encrypts identical
    plaintext blocks to identical ciphertext blocks, so field structure and
    repeated values (states, amounts, SSNs) leak straight out of the stored
    ciphertext, and a stored block can be replayed into another record.
    """
    cipher = Cipher(algorithms.AES(MASTER_KEY), modes.ECB())
    encryptor = cipher.encryptor()
    return base64.b64encode(encryptor.update(plaintext) + encryptor.finalize()).decode("ascii")


def decrypt_field(ciphertext_b64: str) -> bytes:
    cipher = Cipher(algorithms.AES(MASTER_KEY), modes.ECB())
    decryptor = cipher.decryptor()
    return decryptor.update(base64.b64decode(ciphertext_b64)) + decryptor.finalize()


def encrypt_with_random_iv(plaintext: bytes) -> str:
    """Reference: AES-CBC with a fresh random IV prefixed to the ciphertext."""
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(MASTER_KEY), modes.CBC(iv))
    encryptor = cipher.encryptor()
    return base64.b64encode(iv + encryptor.update(plaintext) + encryptor.finalize()).decode("ascii")
