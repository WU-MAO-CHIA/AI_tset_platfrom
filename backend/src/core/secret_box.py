"""加密存在 DB 的機密（例如執行環境的 runner token）。

金鑰由 JWT_SECRET_KEY 以 HKDF 衍生，不另外多一個要保管的設定；更換 JWT_SECRET_KEY 後
舊的密文無法解開，需要重新輸入。
"""
import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from src.core.config import get_settings


class SecretDecryptError(ValueError):
    """密文無法解開（多半是 JWT_SECRET_KEY 已更換）。"""


def _fernet() -> Fernet:
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"autotest-secret-box").derive(
        get_settings().jwt_secret_key.encode("utf-8")
    )
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise SecretDecryptError("secret cannot be decrypted") from exc
