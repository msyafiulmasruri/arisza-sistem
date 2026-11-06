"""Password hashing and stateless session-token helpers for Arisza Backend."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

PASSWORD_ITERATIONS = 600_000
PASSWORD_SCHEME = "pbkdf2_sha256"


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("Kata sandi harus terdiri atas minimal 12 karakter.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations_text, salt_text, digest_text = encoded.split("$", 3)
        iterations = int(iterations_text)
        if scheme != PASSWORD_SCHEME or not 100_000 <= iterations <= 1_000_000:
            return False
        salt = _b64decode(salt_text)
        expected = _b64decode(digest_text)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (AttributeError, TypeError, ValueError, UnicodeError):
        return False


def create_access_token(user_id: int, email: str, secret: str, expires_in: int = 43_200) -> str:
    if not secret or len(secret) < 32:
        raise ValueError("SESSION_SECRET harus berisi minimal 32 karakter.")
    now = int(time.time())
    payload = {"sub": int(user_id), "email": email, "iat": now, "exp": now + int(expires_in)}
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signed_part = f"v1.{encoded_payload}"
    signature = hmac.new(secret.encode("utf-8"), signed_part.encode("ascii"), hashlib.sha256).digest()
    return f"{signed_part}.{_b64encode(signature)}"


def verify_access_token(token: str, secret: str) -> dict[str, Any] | None:
    if not secret or len(secret) < 32 or not isinstance(token, str):
        return None
    try:
        version, encoded_payload, encoded_signature = token.split(".", 2)
        if version != "v1":
            return None
        signed_part = f"{version}.{encoded_payload}"
        expected = hmac.new(secret.encode("utf-8"), signed_part.encode("ascii"), hashlib.sha256).digest()
        supplied = _b64decode(encoded_signature)
        if not hmac.compare_digest(expected, supplied):
            return None
        payload = json.loads(_b64decode(encoded_payload).decode("utf-8"))
        if not isinstance(payload, dict) or int(payload.get("exp", 0)) <= int(time.time()):
            return None
        if int(payload.get("sub", 0)) <= 0 or not isinstance(payload.get("email"), str):
            return None
        return payload
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        return None
