from cryptography.fernet import Fernet

from app.core.config import Settings
from app.core.security import PIICipher


def test_round_trip_encryption() -> None:
    key = Fernet.generate_key().decode()
    cipher = PIICipher(Settings(booking_encryption_key=key))
    token = cipher.encrypt("Ada Lovelace")
    assert cipher.decrypt(token) == "Ada Lovelace"
    assert token != b"Ada Lovelace"
