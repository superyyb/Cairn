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
    用户登录,成功返回 JWT access token。
    
    OAuth2 标准:用 form-data 传 username 和 password。
    注意:这里的 "username" 实际填邮箱地址。
    """
    # 1. 根据邮箱查用户(form_data.username 实际填的是邮箱)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # 2. 用户不存在 OR 密码错 → 统一返回 401
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},  # OAuth2 规范要求
        )
    
    # 3. 生成 JWT
    access_token = create_access_token(subject=user.id)
    
    return Token(access_token=access_token)