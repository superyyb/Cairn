"""
补跑脚本：给所有没有 embedding 的文章生成向量。
运行一次即可，之后新文章由后台任务自动处理。
"""
import logging
from app.core.database import SessionLocal
from app.models.article import Article
from app.services.ai_service import embed_article

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backfill():
    db = SessionLocal()
    try:
        articles = (
            db.query(Article)
            .filter(Article.embedding == None)  # noqa: E711
            .all()
        )

        logger.info(f"Found {len(articles)} articles without embeddings")

        success, failed = 0, 0
        for article in articles:
            embedding = embed_article(article)
            if embedding:
                article.embedding = embedding
                success += 1
                logger.info(f"✅ [{article.id}] {article.title[:50]}")
            else:
                failed += 1
                logger.warning(f"❌ [{article.id}] {article.title[:50]}")

        db.commit()
        logger.info(f"Done. {success} succeeded, {failed} failed.")

    except Exception as e:
        logger.exception(f"Backfill error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    backfill()
