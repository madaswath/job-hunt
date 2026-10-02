import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from jobhunt_api.settings import settings

PRIMARY_KEK_ID = "local-dev-kek"
PREVIOUS_KEK_ID = "local-dev-kek-previous"


def _materialize(raw: str) -> bytes:
    try:
        key = base64.b64decode(raw)
    except Exception:
        key = raw.encode()
    if len(key) < 32:
        key = (key + b"0" * 32)[:32]
    return key[:32]


def _keys_by_id() -> dict[str, bytes]:
    keys = {PRIMARY_KEK_ID: _materialize(settings.token_encryption_key)}
    prev = settings.token_encryption_key_previous
    if prev:
        keys[PREVIOUS_KEK_ID] = _materialize(prev)
    return keys


def _key_for(kek_id: str | None) -> bytes:
    keys = _keys_by_id()
    if kek_id and kek_id in keys:
        return keys[kek_id]
    return keys[PRIMARY_KEK_ID]


def encrypt_token(plaintext: str, *, kek_id: str = PRIMARY_KEK_ID) -> tuple[str, str]:
    aes = AESGCM(_key_for(kek_id))
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode(), kek_id


def decrypt_token(ciphertext: str, kek_id: str | None = None) -> str:
    blob = base64.b64decode(ciphertext)
    nonce, ct = blob[:12], blob[12:]
    order = []
    if kek_id:
        order.append(kek_id)
    order.extend([PRIMARY_KEK_ID, PREVIOUS_KEK_ID])
    seen: set[str] = set()
    keys = _keys_by_id()
    last_err: Exception | None = None
    for kid in order:
        if kid in seen or kid not in keys:
            continue
        seen.add(kid)
        try:
            return AESGCM(keys[kid]).decrypt(nonce, ct, None).decode()
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    raise ValueError("token decrypt failed") from last_err


def rotate_ciphertext(ciphertext: str, kek_id: str | None) -> tuple[str, str] | None:
    try:
        plain = decrypt_token(ciphertext, kek_id)
    except ValueError:
        return None
    return encrypt_token(plain, kek_id=PRIMARY_KEK_ID)
