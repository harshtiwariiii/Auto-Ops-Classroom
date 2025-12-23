# utils/password_hash.py

import hashlib
import hmac

# ============================================================
# SHA-256 PASSWORD HASHING (Simple & Fast)
# ============================================================

def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256.
    Returns a hex string.
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a stored SHA-256 hash.
    Uses HMAC compare to prevent timing attacks.
    """
    return hmac.compare_digest(
        hashlib.sha256(plain_password.encode()).hexdigest(),
        hashed_password
    )
