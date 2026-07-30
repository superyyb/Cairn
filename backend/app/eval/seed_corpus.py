"""
建立 eval 专用语料库：一个固定的 eval_user + 复用 seed_articles.py 里现成的 30 篇文章。

跟 backend/seed_articles.py 的关键区别：
- 只作用于专门的 eval_user，不碰任何真实用户的数据
- 幂等：article 的 url_hash 已存在就跳过，可以放心重复跑
- 绝不执行 "DELETE FROM articles" 这种不限定 user_id 的操作
"""
import logging
import sys
from pathlib import Path

# seed_articles.py 在 backend/ 根目录，不在 app 包里，直接加到 sys.path 里导入，
# 这样两边共用同一份文章内容，不用维护两份重复的测试数据。
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from seed_articles import ARTICLES  # noqa: E402

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.core.utils import hash_url
from app.models.article import Article
from app.models.tag import Tag
from app.models.user import User
from app.services.ai_service import analyze_article, embed_article

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

EVAL_USER_EMAIL = "eval@cairn.local"
EVAL_USER_USERNAME = "eval_bot"


def get_or_create_eval_user(db) -> User:
    user = db.query(User).filter(User.email == EVAL_USER_EMAIL).first()
    if user:
        return user
    user = User(
        email=EVAL_USER_EMAIL,
        username=EVAL_USER_USERNAME,
        password_hash=hash_password("not-a-real-login-eval-user"),  # 没人会用这个账号登录
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"Created eval user id={user.id} ({EVAL_USER_EMAIL})")
    return user


def seed_corpus():
    db = SessionLocal()
    try:
        eval_user = get_or_create_eval_user(db)

        existing_hashes = {
            row[0]
            for row in db.query(Article.url_hash).filter(Article.user_id == eval_user.id).all()
        }

        logger.info(f"Seeding eval corpus for user_id={eval_user.id} ({len(ARTICLES)} candidate articles)...\n")
        created, skipped = 0, 0

        for i, data in enumerate(ARTICLES, 1):
            url_hash = hash_url(data["url"])
            if url_hash in existing_hashes:
                skipped += 1
                continue

            article = Article(
                user_id=eval_user.id,
                url=data["url"],
                url_hash=url_hash,
                title=data["title"],
                content=data["content"],
                excerpt=data.get("excerpt"),
                site_name=data.get("site_name"),
            )
            db.add(article)
            db.flush()  # 拿 id

            existing_tag_names = [t.name for t in db.query(Tag).all()]
            analysis = analyze_article(article.title, article.content, existing_tag_names)
            if analysis:
                article.ai_summary = analysis.summary
                for tag_name in analysis.tags:
                    tag = db.query(Tag).filter(Tag.name == tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.add(tag)
                        db.flush()
                    article.tags.append(tag)

            embedding = embed_article(article)
            if embedding:
                article.embedding = embedding

            article.status = "done" if analysis else "skipped"
            db.commit()
            logger.info(f"[{i:02d}/{len(ARTICLES)}] created: {article.title[:55]}")
            created += 1

        logger.info(
            f"\nDone. created={created}, skipped(already existed)={skipped}, eval_user_id={eval_user.id}"
        )

    except Exception as e:
        logger.exception(f"seed_corpus error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_corpus()
