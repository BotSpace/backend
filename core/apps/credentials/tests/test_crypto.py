"""Crypto service round-trip tests."""
import pytest

from core.apps.credentials.services.crypto import decrypt, encrypt


def test_encrypt_returns_string():
    token = encrypt({"token": "secret123", "param": "value"})
    assert isinstance(token, str)
    assert len(token) > 10


def test_round_trip():
    data = {"token": "my-secret", "placement": "header", "param_name": "X-API-Key"}
    token = encrypt(data)
    recovered = decrypt(token)
    assert recovered == data


def test_round_trip_unicode():
    data = {"username": "Dilshod", "password": "O'zbek123"}
    assert decrypt(encrypt(data)) == data


def test_different_calls_different_tokens():
    """Fernet uses random IV — two encryptions of same data differ."""
    data = {"token": "abc"}
    t1 = encrypt(data)
    t2 = encrypt(data)
    assert t1 != t2
    assert decrypt(t1) == decrypt(t2) == data
