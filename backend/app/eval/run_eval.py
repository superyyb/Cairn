"""
跑一次 eval：对 eval_user 名下所有题目做检索，按类别算 precision/recall/MRR，
true_negative 题目单独检查"相似度是否真的低于阈值、该不该拒答"。

加 --with-generation 之后，还会对通过阈值检查的题目真的调用 generate_answer +
LLM 裁判，测 faithfulness(有没有编)和 answer_relevancy(答没答到点子上)。
默认关闭 —— 这部分要真调用 OpenAI 生成+裁判两次，不是 Phase 1 那种近乎免费的
embedding-only 检查，不该是每次跑都默认要花的钱。

用法:
    uv run python -m app.eval.run_eval
    uv run python -m app.eval.run_eval --top-k 5 --similarity-threshold 0.3 --notes "baseline"
    uv run python -m app.eval.run_eval --with-generation --notes "phase2 baseline"
"""
import argparse
import logging
from collections import defaultdict
from datetime import datetime

from app.api.chat import RAG_SIMILARITY_THRESHOLD
from app.core.config import settings
from app.core.database import SessionLocal
from app.eval.seed_corpus import EVAL_USER_EMAIL
from app.models.eval_question import EvalQuestion
from app.models.eval_result import EvalResult
from app.models.eval_run import EvalRun
from app.models.user import User
from app.services.ai_service import embed_text, generate_answer
from app.services.eval_service import judge_generation
from app.services.retrieval_service import format_sources_for_llm, retrieve_similar_articles

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger(__name__)

CATEGORY_ORDER = ["synthetic", "paraphrase", "multi_hop", "true_negative"]


def compute_metrics(retrieved_ids: list[int], expected_ids: set[int]) -> dict:
    """expected_ids 为空(true_negative)不适用这几个指标，全部返回 None。"""
    if not expected_ids:
        return {"precision_at_k": None, "recall_at_k": None, "reciprocal_rank": None}

    hits = [rid for rid in retrieved_ids if rid in expected_ids]
    precision = len(hits) / len(retrieved_ids) if retrieved_ids else 0.0
    recall = len(set(hits)) / len(expected_ids)

    reciprocal_rank = 0.0
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in expected_ids:
            reciprocal_rank = 1.0 / rank
            break

    return {"precision_at_k": precision, "recall_at_k": recall, "reciprocal_rank": reciprocal_rank}


def run_eval(top_k: int, similarity_threshold: float, notes: str | None, with_generation: bool = False):
    db = SessionLocal()
    try:
        eval_user = db.query(User).filter(User.email == EVAL_USER_EMAIL).first()
        if not eval_user:
            print("Eval user not found — run `uv run python -m app.eval.seed_corpus` first.")
            return

        questions = db.query(EvalQuestion).all()
        if not questions:
            print("No eval questions found — run seed_synthetic_questions / load_adversarial_questions first.")
            return

        run = EvalRun(eval_user_id=eval_user.id, started_at=datetime.utcnow(), notes=notes)
        run.config_snapshot = {
            "similarity_threshold": similarity_threshold,
            "embedding_model": settings.embedding_model,
            "openai_model": settings.openai_model,
            "top_k": top_k,
            "question_count": len(questions),
            "with_generation": with_generation,
            **({"answer_relevancy_scale": "1-5"} if with_generation else {}),
        }
        db.add(run)
        db.commit()
        db.refresh(run)

        by_category = defaultdict(list)
        failures = []
        generation_failures = []

        for q in questions:
            embedding = embed_text(q.question_text)
            if not embedding:
                print(f"WARNING: embedding failed for question {q.id}, skipping")
                continue

            rows = retrieve_similar_articles(db, eval_user.id, embedding, top_k)
            retrieved_ids = [r.id for r in rows]
            similarities = [float(r.similarity) for r in rows]
            expected_ids = set(q.expected_article_ids)

            result = EvalResult(eval_run_id=run.id, eval_question_id=q.id, top_k_used=top_k)
            result.retrieved_article_ids = retrieved_ids
            result.similarities = similarities

            if q.category == "true_negative":
                top1 = similarities[0] if similarities else 0.0
                passed = top1 < similarity_threshold
                result.passed_threshold_check = passed
                if not passed:
                    failures.append(
                        f"[{q.external_id or q.id}] true_negative: "
                        f"top1_similarity={top1:.3f} >= {similarity_threshold} -> WOULD HAVE ANSWERED (regression)"
                    )
            else:
                metrics = compute_metrics(retrieved_ids, expected_ids)
                result.precision_at_k = metrics["precision_at_k"]
                result.recall_at_k = metrics["recall_at_k"]
                result.reciprocal_rank = metrics["reciprocal_rank"]
                if metrics["reciprocal_rank"] == 0.0:
                    failures.append(
                        f"[{q.external_id or q.id}] {q.category}: "
                        f"expected={sorted(expected_ids)} retrieved={retrieved_ids} -> not found in top-{top_k}"
                    )

            if with_generation:
                # 跟 chat.py 的 ask() 用同一个阈值判断，不是按 category 分支 ——
                # 这样如果阈值被调得太松，true_negative 题目也会像生产环境一样真的走一遍生成+裁判。
                max_similarity = max(similarities) if similarities else 0.0
                if max_similarity >= similarity_threshold:
                    sources_for_llm = format_sources_for_llm(rows)
                    generated = generate_answer(q.question_text, sources_for_llm)
                    if generated:
                        result.generated_answer = generated.answer
                        judgment = judge_generation(q.question_text, sources_for_llm, generated.answer)
                        if judgment:
                            if judgment.claims:
                                supported = [c for c in judgment.claims if c.supported]
                                unsupported = [c for c in judgment.claims if not c.supported]
                                result.faithfulness_score = len(supported) / len(judgment.claims)
                                result.unsupported_claims = [
                                    {"claim": c.claim, "reason": c.reason} for c in unsupported
                                ]
                                if unsupported:
                                    generation_failures.append(
                                        f"[{q.external_id or q.id}] {q.category}: "
                                        f"faithfulness={result.faithfulness_score:.2f}, "
                                        f"unsupported={[c.claim for c in unsupported]}"
                                    )
                            # claims 为空(比如答案本身就是"没有相关信息"这种没有实质声明的内容)
                            # 就不打分 —— 没有真的核对任何东西，打 1.0 反而是误导
                            result.answer_relevancy_score = float(judgment.answer_relevancy)
                            result.judge_model = settings.openai_model
                            result.judge_reasoning = judgment.relevancy_reasoning

            db.add(result)
            by_category[q.category].append(result)

        db.commit()
        run.finished_at = datetime.utcnow()
        db.commit()

        print(
            f"\n=== Eval Run #{run.id} "
            f"({run.started_at:%Y-%m-%d %H:%M:%S}, similarity_threshold={similarity_threshold}, top_k={top_k}) ==="
        )
        print(f"{'Category':<15}{'Count':<8}{'Precision@k':<14}{'Recall@k':<12}{'MRR':<8}")
        for category in CATEGORY_ORDER:
            results = by_category.get(category, [])
            if not results:
                continue
            if category == "true_negative":
                passed = sum(1 for r in results if r.passed_threshold_check)
                pct = passed / len(results) * 100
                print(
                    f"{category:<15}{len(results):<8}{'-':<14}{'-':<12}{'-':<8}"
                    f"   (abstain accuracy: {passed}/{len(results)} = {pct:.0f}%)"
                )
            else:
                precisions = [r.precision_at_k for r in results if r.precision_at_k is not None]
                recalls = [r.recall_at_k for r in results if r.recall_at_k is not None]
                rrs = [r.reciprocal_rank for r in results if r.reciprocal_rank is not None]
                avg_p = sum(precisions) / len(precisions) if precisions else 0.0
                avg_r = sum(recalls) / len(recalls) if recalls else 0.0
                avg_rr = sum(rrs) / len(rrs) if rrs else 0.0
                print(f"{category:<15}{len(results):<8}{avg_p:<14.2f}{avg_r:<12.2f}{avg_rr:<8.2f}")

        if failures:
            print("\nFailures:")
            for f in failures:
                print(f"  {f}")
        else:
            print("\nNo failures.")

        if with_generation:
            print(f"\n--- Generation (faithfulness / relevancy, scale 1-5 for relevancy) ---")
            print(f"{'Category':<15}{'N judged':<10}{'Avg Faithfulness':<20}{'Avg Relevancy':<15}")
            for category in CATEGORY_ORDER:
                results = [r for r in by_category.get(category, []) if r.faithfulness_score is not None]
                if not results:
                    continue
                avg_f = sum(r.faithfulness_score for r in results) / len(results)
                relevancies = [r.answer_relevancy_score for r in results if r.answer_relevancy_score is not None]
                avg_rel = sum(relevancies) / len(relevancies) if relevancies else 0.0
                print(f"{category:<15}{len(results):<10}{avg_f:<20.2f}{avg_rel:<15.2f}")

            if generation_failures:
                print("\nGeneration failures (unsupported claims found):")
                for f in generation_failures:
                    print(f"  {f}")
            else:
                print("\nNo generation failures.")

    except Exception as e:
        logger.exception(f"run_eval error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--similarity-threshold", type=float, default=RAG_SIMILARITY_THRESHOLD)
    parser.add_argument("--notes", type=str, default=None)
    parser.add_argument(
        "--with-generation",
        action="store_true",
        help="Also run generate_answer + LLM judge for questions that pass the threshold check "
        "(real OpenAI calls, non-zero cost — off by default).",
    )
    args = parser.parse_args()
    run_eval(
        top_k=args.top_k,
        similarity_threshold=args.similarity_threshold,
        notes=args.notes,
        with_generation=args.with_generation,
    )
