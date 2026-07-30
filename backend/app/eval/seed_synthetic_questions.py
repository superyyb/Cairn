"""
给 eval_user 名下每篇已经有 ai_summary 的文章生成一条 synthetic 问题。
幂等：已经有 synthetic 问题的文章(source_article_id 命中)会跳过。
"""
import logging

from app.core.database import SessionLocal
from app.eval.seed_corpus import EVAL_USER_EMAIL
from app.models.article import Article
from app.models.eval_question import EvalQuestion
from app.models.user import User
from app.services.eval_service import generate_synthetic_question

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def seed_synthetic_questions():
    db = SessionLocal()
    try:
        eval_user = db.query(User).filter(User.email == EVAL_USER_EMAIL).first()
        if not eval_user:
            logger.error("Eval user not found — run `uv run python -m app.eval.seed_corpus` first.")
            return

        articles = (
            db.query(Article)
            .filter(Article.user_id == eval_user.id, Article.ai_summary.isnot(None))
            .all()
        )

        already_covered = {
            q.source_article_id
            for q in db.query(EvalQuestion)
            .filter(EvalQuestion.category == "synthetic", EvalQuestion.source_article_id.isnot(None))
            .all()
        }

        created, skipped = 0, 0
        for i, article in enumerate(articles, 1):
            if article.id in already_covered:
                skipped += 1
                continue

            question_text = generate_synthetic_question(article.title, article.ai_summary)
            if not question_text:
                logger.warning(f"[{i}/{len(articles)}] failed to generate question for article {article.id}")
                continue

            q = EvalQuestion(category="synthetic", question_text=question_text, source_article_id=article.id)
            q.expected_article_ids = [article.id]
            db.add(q)
            db.commit()
            logger.info(f"[{i}/{len(articles)}] {article.title[:40]} -> {question_text}")
            created += 1

        logger.info(f"\nDone. created={created}, skipped(already had one)={skipped}")

    except Exception as e:
        logger.exception(f"seed_synthetic_questions error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_synthetic_questions()
