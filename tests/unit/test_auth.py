import os

os.environ.setdefault("APP_AUTH_SIGNING_KEY", "test-signing-key-not-for-prod")

from shared.auth.passwords import hash_password, verify_password
from shared.auth.tokens import create_access_token, decode_access_token


def test_password_hash_roundtrip():
    hashed = hash_password("Test@12345")
    assert verify_password("Test@12345", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip():
    token = create_access_token(user_id=1, username="requestor1", roles=["REQUESTOR"])
    payload = decode_access_token(token)
    assert payload["sub"] == "1"
    assert payload["username"] == "requestor1"
    assert payload["roles"] == ["REQUESTOR"]
