"""覆盖 /api/auth/* 和 /api/users/register —— 重点是登录时序防护、
refresh token 轮换 + 复用检测这类有状态、错了很隐蔽的逻辑。"""
from datetime import timedelta

import app.api.auth as auth_module
from app.core.utils import utc_now


# ---------- register ----------

def test_register_success(client):
    resp = client.post("/api/users/register", json={
        "email": "new@example.com",
        "username": "New User",
        "password": "supersecret123",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email_conflicts(client, make_user):
    make_user(email="dup@example.com")
    resp = client.post("/api/users/register", json={
        "email": "dup@example.com",
        "username": "Someone Else",
        "password": "supersecret123",
    })
    assert resp.status_code == 409


def test_register_rate_limited_after_five_per_15min(client):
    for i in range(5):
        resp = client.post("/api/users/register", json={
            "email": f"user{i}@example.com",
            "username": "U",
            "password": "supersecret123",
        })
        assert resp.status_code == 201

    resp = client.post("/api/users/register", json={
        "email": "one-too-many@example.com",
        "username": "U",
        "password": "supersecret123",
    })
    assert resp.status_code == 429


# ---------- login ----------

def test_login_web_sets_httponly_cookie(client, make_user):
    make_user(email="web@example.com", password="mypassword1")
    resp = client.post("/api/auth/login", data={"username": "web@example.com", "password": "mypassword1"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert "refresh_token" not in resp.json()
    assert resp.cookies.get("refresh_token") is not None


def test_login_extension_returns_refresh_token_in_body(client, make_user):
    make_user(email="ext@example.com", password="mypassword1")
    resp = client.post(
        "/api/auth/login?client_type=extension",
        data={"username": "ext@example.com", "password": "mypassword1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "refresh_token" in body
    assert resp.cookies.get("refresh_token") is None


def test_login_wrong_password_rejected(client, make_user):
    make_user(email="wrong@example.com", password="correctpass1")
    resp = client.post("/api/auth/login", data={"username": "wrong@example.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_unknown_email_still_runs_password_check(client):
    """
    邮箱不存在时必须也走一次 bcrypt 比对(对着 dummy hash),否则"用户不存在"分支
    比"密码错误"分支快很多,响应耗时差就能被用来判断邮箱是否已注册。
    这里不测真实耗时(在 CI/本机噪声下不稳定),改成断言 verify_password 确实被调用、
    且传入的是 dummy hash —— 这才是保护生效的直接证据。
    """
    from unittest.mock import patch

    with patch("app.api.auth.verify_password", wraps=auth_module.verify_password) as spy:
        resp = client.post(
            "/api/auth/login",
            data={"username": "does-not-exist@example.com", "password": "whatever123"},
        )

    assert resp.status_code == 401
    spy.assert_called_once()
    assert spy.call_args.args[1] == auth_module._DUMMY_PASSWORD_HASH


def test_login_rate_limited_after_ten_per_15min(client, make_user):
    make_user(email="ratelimited@example.com", password="correctpass1")
    for _ in range(10):
        resp = client.post(
            "/api/auth/login",
            data={"username": "ratelimited@example.com", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    resp = client.post(
        "/api/auth/login",
        data={"username": "ratelimited@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 429


# ---------- refresh ----------

def test_refresh_rotates_token(client, make_user):
    make_user(email="rotate@example.com", password="mypassword1")
    login_resp = client.post("/api/auth/login", data={"username": "rotate@example.com", "password": "mypassword1"})
    old_token = login_resp.cookies.get("refresh_token")

    refresh_resp = client.post("/api/auth/refresh")
    assert refresh_resp.status_code == 200
    new_token = refresh_resp.cookies.get("refresh_token")
    assert new_token is not None
    assert new_token != old_token


def test_refresh_reuse_of_revoked_token_kills_all_sessions(client, make_user):
    make_user(email="reuse@example.com", password="mypassword1")
    login_resp = client.post("/api/auth/login", data={"username": "reuse@example.com", "password": "mypassword1"})
    old_token = login_resp.cookies.get("refresh_token")

    # 正常轮转一次:old_token 被标记 revoked,拿到一个新 token
    first_refresh = client.post("/api/auth/refresh")
    assert first_refresh.status_code == 200
    new_token = first_refresh.cookies.get("refresh_token")

    # 攻击者/旧标签页拿着已经被撤销的 old_token 再刷一次
    replay = client.post("/api/auth/refresh", headers={"Cookie": f"refresh_token={old_token}"})
    assert replay.status_code == 401
    assert "invalidated" in replay.json()["detail"].lower()

    # 连坐:这次刷新拿到的、本来还有效的 new_token 也必须被牵连撤销
    legit_retry = client.post("/api/auth/refresh", headers={"Cookie": f"refresh_token={new_token}"})
    assert legit_retry.status_code == 401


def test_refresh_expired_token_rejected(client, make_user, make_refresh_token):
    user = make_user(email="expired@example.com")
    raw, _ = make_refresh_token(user.id, expires_at=utc_now() - timedelta(days=1))

    resp = client.post("/api/auth/refresh", headers={"Cookie": f"refresh_token={raw}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_refresh_missing_token_rejected(client):
    resp = client.post("/api/auth/refresh")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "No refresh token"


def test_refresh_unknown_token_rejected(client):
    resp = client.post("/api/auth/refresh", headers={"Cookie": "refresh_token=not-a-real-token"})
    assert resp.status_code == 401


# ---------- logout ----------

def test_logout_revokes_token_and_clears_cookie(client, make_user):
    make_user(email="logout@example.com", password="mypassword1")
    login_resp = client.post("/api/auth/login", data={"username": "logout@example.com", "password": "mypassword1"})
    token = login_resp.cookies.get("refresh_token")

    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200
    assert not logout_resp.cookies.get("refresh_token")

    reuse = client.post("/api/auth/refresh", headers={"Cookie": f"refresh_token={token}"})
    assert reuse.status_code == 401


def test_logout_without_token_is_a_noop(client):
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
