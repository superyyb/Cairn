"""用户相关 API接口"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
#status_code=201 —— HTTP 规范:创建资源成功返回 201(Created)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    注册新用户。
    
    - email: 合法的邮箱地址
    - password: 至少 8 位
    - username: 用户名
    """
    # 1. 检查邮箱是否已被注册
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email address has been used",
        )
    
    # 2. 创建新用户,密码哈希后存
    new_user = User(
        email=user_in.email,
        username=user_in.username,
        password_hash=hash_password(user_in.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.get("/count")
def count_users(db: Session = Depends(get_db)):
    """返回数据库里有多少用户(管理用)"""
    count = db.query(User).count()
    return {"total_users": count}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户的信息。
    需要在 Header 里带 Authorization: Bearer <token>
    """
    return current_user