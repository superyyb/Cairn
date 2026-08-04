"""
把线上真实用户的 👎 反馈接回 LLM 裁判，测"裁判和真人是否一致" —— compare_calibration.py
是拿人工标注的 CSV 去校准裁判，这里是拿真实用户的即时反馈做同样的事，只是标注来源换了。

为什么不是把这些问题直接灌进 eval_questions：eval_questions/eval_runs/eval_results 那套
围着一个固定的 eval_user + 种子语料库转，retrieve_similar_articles 按 user_id 强制 scope，
真实用户的文章库和 eval 语料库是两套完全不同的数据，直接插一条 EvalQuestion 进去，
expected_article_ids 在 eval 语料库里根本不存在，precision/recall 全是噪声。
但 judge_generation 只需要 question + sources + answer，不依赖固定语料库，可以拿真实
user_id 重放，所以这里只测生成层一致性，不碰 eval_questions/eval_results。

时间旅行问题：用户 T1 点踩时看到的是某几篇文章的内容，T2 回放时这些文章可能已经被删、
文章库也可能变了。这里不重新 retrieve_similar_articles（那样检索出来的可能是完全不同的
文章，测的就不是"那次回答"了），而是按 chat_session.sources 里存的文章 id 精确拉取
——锁定"当时给模型看的是哪几篇"，排除检索层漂移，但文章的 content/ai_summary 用的是
当前版本，文章本身如果被重新处理过，这里测不出来。id 已经不存在（文章被删）的直接跳过。

用法:
    uv run python -m app.eval.replay_feedback
    uv run python -m app.eval.replay_feedback --limit 10 --csv out.csv
"""
import argparse
import csv as csv_module
import logging
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.models.article import Article
from app.models.chat_feedback import ChatFeedback
from app.models.chat_session import ChatSession
from app.services.ai_service import generate_answer
from app.services.eval_service import judge_generation
from app.services.retrieval_service import format_sources_for_llm

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger(__name__)

FULLY_FAITHFUL_THRESHOLD = 1.0


def replay_one(db, feedback: ChatFeedback, session: ChatSession) -> dict | None:
    """返回一条处理结果 dict，或 None 表示这条被跳过（原文章已被删）。"""
    article_ids = [s["id"] for s in session.sources]
    if not article_ids:
        return {"status": "skipped_no_sources"}

    articles_by_id = {
        a.id: a for a in db.query(Article).filter(Article.id.in_(article_ids))
    }
    if len(articles_by_id) != len(article_ids):
        return {"status": "skipped_article_deleted"}

    # 按原始引用顺序重排，不能直接用 SQL 查询返回的顺序——顺序错了裁判判断"claim 对应第几篇
    # 来源"会直接判错
    ordered_articles = [articles_by_id[aid] for aid in article_ids]
    sources_for_llm = format_sources_for_llm(ordered_articles)

    answer = generate_answer(session.question, sources_for_llm)
    if not answer:
        return {"status": "generation_failed"}

    judgment = judge_generation(session.question, sources_for_llm, answer)
    if not judgment:
        return {"status": "judge_failed"}

    faithfulness_score = None
    if judgment.claims:
        supported = [c for c in judgment.claims if c.supported]
        faithfulness_score = len(supported) / len(judgment.claims)

    return {
        "status": "ok",
        "faithfulness_score": faithfulness_score,
        "answer_relevancy": judgment.answer_relevancy,
        "dangerous_miss": faithfulness_score is not None and faithfulness_score >= FULLY_FAITHFUL_THRESHOLD,
    }


def replay_feedback(limit: int, since_days: int | None, csv_path: str | None):
    db = SessionLocal()
    csv_rows = []
    try:
        query = db.query(ChatFeedback).filter(
            ChatFeedback.rating == False,  # noqa: E712 — SQLAlchemy 列比较必须用 ==
            ChatFeedback.reviewed == False,  # noqa: E712
        )
        if since_days is not None:
            query = query.filter(ChatFeedback.created_at >= datetime.utcnow() - timedelta(days=since_days))
        pending = query.order_by(ChatFeedback.created_at.desc()).limit(limit).all()

        print(f"=== Replaying {len(pending)} unreviewed \U0001f44e (real OpenAI calls, non-zero cost) ===")
        print("Note: replay pins the original retrieved article set by id, but uses their current "
              "content — retrieval-layer drift between feedback time and replay time is avoided, "
              "per-article content drift is not.\n")

        by_reason: dict[str | None, list[dict]] = {}
        skipped_deleted = 0

        for fb in pending:
            session = db.query(ChatSession).filter(ChatSession.id == fb.chat_session_id).first()
            if not session:
                skipped_deleted += 1
                fb.reviewed = True
                continue

            result = replay_one(db, fb, session)
            if result is None or result["status"] != "ok":
                status = result["status"] if result else "unknown_error"
                if status == "skipped_article_deleted":
                    skipped_deleted += 1
                    fb.reviewed = True
                # generation_failed / judge_failed 不标 reviewed，留给下次重跑（可能是临时性 API 问题）
                if csv_path:
                    csv_rows.append({
                        "chat_session_id": fb.chat_session_id, "reason": fb.reason or "",
                        "comment": fb.comment or "", "status": status,
                        "faithfulness_score": "", "answer_relevancy": "", "dangerous_miss": "",
                    })
                continue

            by_reason.setdefault(fb.reason, []).append(result)
            fb.reviewed = True
            if csv_path:
                csv_rows.append({
                    "chat_session_id": fb.chat_session_id, "reason": fb.reason or "",
                    "comment": fb.comment or "", "status": "ok",
                    "faithfulness_score": f"{result['faithfulness_score']:.2f}" if result["faithfulness_score"] is not None else "",
                    "answer_relevancy": result["answer_relevancy"],
                    "dangerous_miss": result["dangerous_miss"],
                })

        db.commit()

        if skipped_deleted:
            print(f"Skipped {skipped_deleted} (source article(s) since deleted, or session missing) — not counted below.\n")

        if not by_reason:
            print("No feedback successfully replayed.")
            return

        print(f"{'Reason':<20}{'N':<6}{'Avg faithfulness':<20}{'Avg relevancy':<16}{'Dangerous misses':<18}")
        for reason, results in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
            label = reason if reason else "(no reason given)"
            scored = [r for r in results if r["faithfulness_score"] is not None]
            avg_f = sum(r["faithfulness_score"] for r in scored) / len(scored) if scored else None
            avg_rel = sum(r["answer_relevancy"] for r in results) / len(results)
            n_dangerous = sum(1 for r in results if r["dangerous_miss"])
            avg_f_str = f"{avg_f:.2f}" if avg_f is not None else "n/a"
            print(f"{label:<20}{len(results):<6}{avg_f_str:<20}{avg_rel:<16.2f}{n_dangerous:<18}")

        print(
            "\nA 'dangerous miss' = judge said the answer was fully faithful, but the real user still "
            "clicked \U0001f44e. Low agreement specifically in the 'wrong_info' row is ambiguous: it can mean "
            "the judge is too lenient (a real generation-faithfulness problem), OR it can mean users "
            "tagging wrong_info were actually complaining about retrieval quality — which judge_generation "
            "never tests, since it only grades faithfulness/relevancy of the given sources. Don't conclude "
            "'judge needs recalibrating' from this table alone — pull a few transcripts for the low-agreement "
            "reason buckets and read them before deciding whether it's a judge problem or a retrieval problem."
        )

        if csv_path:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv_module.DictWriter(f, fieldnames=[
                    "chat_session_id", "reason", "comment", "status",
                    "faithfulness_score", "answer_relevancy", "dangerous_miss",
                ])
                writer.writeheader()
                writer.writerows(csv_rows)
            print(f"\nWrote {len(csv_rows)} rows to {csv_path}")
    except Exception as e:
        logger.exception(f"replay_feedback error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Max number of \U0001f44e to replay (real OpenAI calls)")
    parser.add_argument("--since", type=int, default=None, help="Only replay feedback from the last N days")
    parser.add_argument("--csv", type=str, default=None, help="Optional path to export per-row results for manual triage")
    args = parser.parse_args()
    replay_feedback(limit=args.limit, since_days=args.since, csv_path=args.csv)
