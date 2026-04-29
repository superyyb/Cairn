"""鉴权相关 API"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
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