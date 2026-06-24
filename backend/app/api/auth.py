"""鉴权相关 API"""
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import Token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    User login. Returns a JWT access token on success.

    OAuth2 standard: credentials are sent as form-data with username and password fields.
    Note: the "username" field should contain the user's email address.
    """
    # 1. 根据邮箱查用户(form_data.username 实际填的是邮箱)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # 2. 用户不存在 OR 密码错 → 统一返回 401
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},  # OAuth2 规范要求
        )
    
    # 3. 生成 JWT
    access_token = create_access_token(subject=user.id)

    return Token(access_token=access_token)


class GoogleLoginRequest(BaseModel):
    credential: str  # Google 返回的 id_token


@router.post("/google", response_model=Token)
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Google OAuth 登录：验证 id_token，找到或创建用户，返回 JWT。"""
    # 1. 验证 Google id_token
    try:
        idinfo = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            settings.google_client_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    email = idinfo.get("email")
    name = idinfo.get("name") or email.split("@")[0]

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    # 2. 找已有用户，没有就创建
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            username=name,
            password_hash=hash_password(secrets.token_hex(32)),  # Google 用户无密码
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 3. 返回 JWT
    return Token(access_token=create_access_token(subject=user.id))