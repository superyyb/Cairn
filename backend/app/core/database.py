"""数据库连接 - SQLAlchemy Engine 和 Session"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


# 1. 创建数据库引擎(整个应用共享一个)
engine = create_engine(
    settings.database_url,
    echo=True,  # 开发时打印 SQL 语句,上线时改 False
    pool_pre_ping=True,  # 避免连接失效
)

# 2. Session 工厂(每次请求调用它生成一个 session)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# 3. 所有 Model 的基类(model 都要继承它)
class Base(DeclarativeBase):
    pass


# 4. FastAPI 依赖注入用的函数
def get_db():
    """每次请求进来,生成一个 session;请求结束自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()