from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass

PBKDF2_ITERATIONS = 390_000
SALT_BYTES = 16


@dataclass(frozen=True, slots=True)
class PasswordHash:
    algorithm: str
    iterations: int
    salt_b64: str
    digest_b64: str

    def to_storable_string(self) -> str:
        return f"{self.algorithm}${self.iterations}${self.salt_b64}${self.digest_b64}"

    @staticmethod
    def from_storable_string(value: str) -> "PasswordHash":
        algorithm, iterations, salt_b64, digest_b64 = value.split("$", maxsplit=3)
        return PasswordHash(
            algorithm=algorithm,
            iterations=int(iterations),
            salt_b64=salt_b64,
            digest_b64=digest_b64,
        )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    data = PasswordHash(
        algorithm="pbkdf2_sha256",
        iterations=PBKDF2_ITERATIONS,
        salt_b64=base64.b64encode(salt).decode("ascii"),
        digest_b64=base64.b64encode(digest).decode("ascii"),
    )
    return data.to_storable_string()


def verify_password(password: str, stored: str) -> bool:
    parsed = PasswordHash.from_storable_string(stored)
    if parsed.algorithm != "pbkdf2_sha256":
        return False

    salt = base64.b64decode(parsed.salt_b64.encode("ascii"))
    expected = base64.b64decode(parsed.digest_b64.encode("ascii"))
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, parsed.iterations)
    return hmac.compare_digest(actual, expected)
