import os

os.environ["TOKEN_ENCRYPTION_KEY"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
os.environ["TOKEN_ENCRYPTION_KEY_PREVIOUS"] = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB="

from jobhunt_api.services import crypto  # noqa: E402


def test_encrypt_decrypt_roundtrip():
    ct, kek = crypto.encrypt_token("refresh-token-123")
    assert kek == crypto.PRIMARY_KEK_ID
    assert crypto.decrypt_token(ct, kek) == "refresh-token-123"


def test_rotation_rewraps_with_previous_key():
    old_ct, _ = crypto.encrypt_token("rotate-me", kek_id=crypto.PREVIOUS_KEK_ID)
    rotated = crypto.rotate_ciphertext(old_ct, crypto.PREVIOUS_KEK_ID)
    assert rotated
    new_ct, new_kek = rotated
    assert new_kek == crypto.PRIMARY_KEK_ID
    assert crypto.decrypt_token(new_ct, new_kek) == "rotate-me"
