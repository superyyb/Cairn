"""
把 app/eval/fixtures/adversarial_questions.json 里手写的题目导入 eval_questions 表。
按 external_id upsert，改了 JSON 文件之后可以放心重复跑。
source_urls 按 url_hash 解析成当时真实的 article_id —— 不直接在 JSON 里写死数据库自增 id，
因为那个值在重新 seed 语料库之后不是稳定的。
"""
import json
import logging
from pathlib import Path

from app.core.database import SessionLocal
from app.core.utils import hash_url
from app.eval.seed_corpus import EVAL_USER_EMAIL
from app.models.article import Article
from app.models.eval_question import EvalQuestion
from app.models.user import User

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "adversarial_questions.json"


def load_adversarial_questions():
    db = SessionLocal()
    try:
        eval_user = db.query(User).filter(User.email == EVAL_USER_EMAIL).first()
        if not eval_user:
            logger.error("Eval user not found — run `uv run python -m app.eval.seed_corpus` first.")
            return

        entries = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        created, updated = 0, 0

        for entry in entries:
            expected_ids = []
            for url in entry.get("source_urls", []):
                article = (
                    db.query(Article)
                    .filter(Article.user_id == eval_user.id, Article.url_hash == hash_url(url))
                    .first()
                )
                if not article:
                    logger.warning(f"[{entry['external_id']}] source url not found in eval corpus: {url}")
                    continue
                expected_ids.append(article.id)

            existing = (
                db.query(EvalQuestion)
                .filter(EvalQuestion.external_id == entry["external_id"])
                .first()
            )
            if existing:
                existing.category = entry["category"]
                existing.question_text = entry["question"]
                existing.expected_article_ids = expected_ids
                existing.notes = entry.get("notes")
                updated += 1
            else:
                q = EvalQuestion(
                    category=entry["category"],
                    question_text=entry["question"],
                    external_id=entry["external_id"],
                    notes=entry.get("notes"),
                )
                q.expected_article_ids = expected_ids
                db.add(q)
                created += 1

        db.commit()
        logger.info(f"Done. created={created}, updated={updated}, total_in_fixture={len(entries)}")

    except Exception as e:
        logger.exception(f"load_adversarial_questions error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    load_adversarial_questions()
