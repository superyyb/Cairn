"""共享 fixtures。

关键点:env 变量必须在任何 app.* 模块被 import 之前改好,因为
app.core.config.Settings() 是在 import 的时候就读一次 env,读完就定了。
所以下面这几行必须放在文件最上面,顺序不能挪到 app 的 import 之后。
"""
import os
import re

from dotenv import load_dotenv

load_dotenv()

_db_url = os.environ.get("DATABASE_URL", "")
os.environ["DATABASE_URL"] = re.sub(r"/[^/]+$", "/devvault_test", _db_url)
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — 把所有 ORM 模型注册进 Base.metadata,create_all 才能建全所有表
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.rate_limit import get_redis
from app.core.security import hash_password
from app.models.user import User
from main import app as fastapi_app

engine = create_engine(settings.database_url)
TestSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def _schema():
    """整个测试session建一次表,结束后删掉。"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """
    每个测试一个事务,测试结束整体 rollback —— 测试之间零污染。

    这里用的是 SQLAlchemy 官方推荐的 "SAVEPOINT" 写法:被测代码里散落的
    db.commit() 只会结束当前 SAVEPOINT,不会真的提交外层事务;
    event 监听器在每次 SAVEPOINT 结束后立刻开一个新的,
    所以业务代码可以照常调用 commit(),测试结束时外层 rollback() 会把这次测试的所有改动全部撤销。
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    """
    TestClient,把 get_db 依赖换成上面这个受控的 db_session。

    注意:没有用 `with TestClient(...) as c` —— 那样会触发 main.py 里的
    lifespan(启动 arq 连接池 + 定时清理任务),而 auth/rate-limit 测试都不需要它们,
    不启动能让测试更快、更少额外依赖。
    """
    def _get_db_override():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _get_db_override
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _clean_redis():
    """限流计数器存在 Redis 里,不在 db_session 的事务里,rollback 撤销不到它,要手动清。"""
    r = get_redis()
    r.flushdb()
    yield
    r.flushdb()


@pytest.fixture
def make_user(db_session):
    """make_user() 创建一个真实用户(密码走真实 bcrypt 哈希),返回 User 对象。"""
    def _make(email="test@example.com", password="testpass123", username="Test User"):
        user = User(email=email, username=username, password_hash=hash_password(password))
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture
def make_refresh_token(db_session):
    """make_refresh_token(user_id, expires_at, ...) 直接插入一条 refresh_token 记录,返回 (原始 token, ORM 对象)。"""
    from app.core.security import create_refresh_token
    from app.models.refresh_token import RefreshToken

    def _make(user_id, expires_at, revoked_at=None, client_type="web"):
        raw, token_hash = create_refresh_token()
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            client_type=client_type,
            expires_at=expires_at,
            revoked_at=revoked_at,
        )
        db_session.add(token)
        db_session.commit()
        return raw, token

    return _make
