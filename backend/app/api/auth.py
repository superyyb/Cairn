"""鉴权相关 API"""
import logging
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import login_rate_limit, refresh_rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.utils import utc_now
from app.models.oauth_account import OAuthAccount
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import Token, TokenWithRefresh, RefreshRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "refresh_token"

# 邮箱不存在时也要跑一次 bcrypt 比对,不然"用户不存在"分支比"密码错误"分支快很多,
# 响应时间差本身就能被用来判断一个邮箱是否已注册(timing attack)。
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_hex(32))


def _set_refresh_cookie(response: Response, raw_token: str, expires_days: int) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=expires_days * 86400,
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/api/auth")


def _issue_tokens(
    db: Session,
    response: Response,
    user_id: int,
    client_type: str,
) -> Token | TokenWithRefresh:
    """Issue access token + refresh token for a user. Handles both web and extension."""
    access_token = create_access_token(subject=user_id)
    raw_refresh, token_hash = create_refresh_token()

    expires_days = (
        settings.refresh_token_expire_days_web
        if client_type == "web"
        else settings.refresh_token_expire_days_extension
    )

    db.add(RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        client_type=client_type,
        expires_at=utc_now() + timedelta(days=expires_days),
    ))
    db.commit()

    if client_type == "web":
        _set_refresh_cookie(response, raw_refresh, expires_days)
        return Token(access_token=access_token)
    else:
        return TokenWithRefresh(access_token=access_token, refresh_token=raw_refresh)


@router.post("/login")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    client_type: str = Query(default="web"),
    _: None = Depends(login_rate_limit),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    password_hash = user.password_hash if user else _DUMMY_PASSWORD_HASH
    password_ok = verify_password(form_data.password, password_hash)
    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _issue_tokens(db, response, user.id, client_type)


class GoogleLoginRequest(BaseModel):
    credential: str


@router.post("/google")
def google_login(
    payload: GoogleLoginRequest,
    response: Response,
    client_type: str = Query(default="web"),
    db: Session = Depends(get_db),
):
    try:
        idinfo = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            settings.google_client_id,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")

    if not idinfo.get("email_verified"):
        raise HTTPException(status_code=400, detail="Google email not verified")

    sub = idinfo["sub"]
    email = idinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")
    name = idinfo.get("name") or email.split("@")[0]

    # Look up by Google sub (stable) rather than email
    oauth_account = db.query(OAuthAccount).filter(
        OAuthAccount.provider == "google",
        OAuthAccount.provider_user_id == sub,
    ).first()

    if oauth_account:
        user = oauth_account.user
    else:
        # First Google login — find existing user by email or create new one
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                username=name,
                password_hash=hash_password(secrets.token_hex(32)),
            )
            db.add(user)
            db.flush()

        oauth_account = OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_user_id=sub,
            email=email,
        )
        db.add(oauth_account)
        db.commit()
        db.refresh(user)

    return _issue_tokens(db, response, user.id, client_type)


@router.post("/refresh")
def refresh(
    request: Request,
    response: Response,
    client_type: str = Query(default="web"),
    body: RefreshRequest | None = None,
    _: None = Depends(refresh_rate_limit),
    db: Session = Depends(get_db),
):
    # Get raw token from cookie (web) or request body (extension)
    if client_type == "web":
        raw_token = request.cookies.get(COOKIE_NAME)
    else:
        raw_token = body.refresh_token if body else None

    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    token_hash = hash_token(raw_token)
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if not db_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Token reuse detection: revoked token used again → revoke ALL user sessions
    if db_token.revoked_at is not None:
        logger.warning(f"Refresh token reuse detected for user {db_token.user_id} — revoking all sessions")
        db.query(RefreshToken).filter(
            RefreshToken.user_id == db_token.user_id,
            RefreshToken.revoked_at.is_(None),
        ).update({"revoked_at": utc_now()})
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalidated. Please log in again.")

    if db_token.expires_at < utc_now():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    # Rotate: revoke old token, issue new pair
    db_token.revoked_at = utc_now()
    db.commit()

    return _issue_tokens(db, response, db_token.user_id, client_type)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    client_type: str = Query(default="web"),
    body: RefreshRequest | None = None,
    db: Session = Depends(get_db),
):
    if client_type == "web":
        raw_token = request.cookies.get(COOKIE_NAME)
    else:
        raw_token = body.refresh_token if body else None

    if raw_token:
        token_hash = hash_token(raw_token)
        db_token = db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        ).first()
        if db_token:
            db_token.revoked_at = utc_now()
            db.commit()

    if client_type == "web":
        _clear_refresh_cookie(response)

    return {"message": "Logged out"}
