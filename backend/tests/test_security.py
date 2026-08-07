"""JWT 签发/解析 + get_current_user 的边界分支。"""
from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core.security import create_access_token, decode_access_token, get_current_user


def test_access_token_round_trip():
    token = create_access_token(subject=42)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"


def test_expired_access_token_fails_to_decode():
    token = create_access_token(subject=1, expires_delta=timedelta(seconds=-1))
    assert decode_access_token(token) is None


def test_garbage_token_fails_to_decode():
    assert decode_access_token("not.a.valid.token") is None


def test_get_current_user_returns_matching_user(db_session, make_user):
    user = make_user(email="valid@example.com")
    token = create_access_token(subject=user.id)

    result = get_current_user(token=token, db=db_session)
    assert result.id == user.id


def test_get_current_user_rejects_garbage_token(db_session):
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="garbage", db=db_session)
    assert exc_info.value.status_code == 401


def test_get_current_user_rejects_token_for_deleted_user(db_session, make_user):
    user = make_user(email="deleted@example.com")
    token = create_access_token(subject=user.id)

    db_session.delete(user)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token, db=db_session)
    assert exc_info.value.status_code == 401
