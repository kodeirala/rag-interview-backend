"""Symmetric encryption helpers for booking PII."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings


class PIICipher:
    """Encrypts and decrypts booking fields at rest."""

    def __init__(self, settings: Settings) -> None:
        if not settings.booking_encryption_key:
            raise RuntimeError(
                "BOOKING_ENCRYPTION_KEY is required. Generate one with: "
                'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        self._fernet = Fernet(settings.booking_encryption_key.encode("utf-8"))

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def decrypt(self, token: bytes) -> str:
        try:
            return self._fernet.decrypt(token).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Unable to decrypt stored booking data") from exc
