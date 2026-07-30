"""
从最近一次 --with-generation 跑批里，抽一个分层样本(全部 multi_hop + 全部 paraphrase +
随机抽 8 条 synthetic)，导出成一份纯文本 markdown，方便人工逐条打分。

为什么这么分层：multi_hop/paraphrase 是最容易出现幻觉的两类(跨文章综合、措辞被故意
带偏)，值得全部人工看一遍；synthetic 是"简单模式"对照组(问题就是从摘要反推出来的)，
抽 8 条够验证裁判有没有对着简单案例也乱挑刺就行，不需要全量看。

用法:
    uv run python -m app.eval.export_calibration_sample
"""
import logging
import random
from datetime import datetime
from pathlib import Path

from app.core.database import SessionLocal
from app.models.article import Article
from app.models.eval_question import EvalQuestion
from app.models.eval_result import EvalResult
from app.models.eval_run import EvalRun
from app.services.ai_service import build_source_context
from app.services.retrieval_service import format_sources_for_llm

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

SYNTHETIC_SAMPLE_SIZE = 8
OUTPUT_DIR = Path(__file__).resolve().parents[3] / "backend" / "eval_calibration"


def _rows_from_article_ids(db, article_ids: list[int]):
    """伪造出跟 retrieve_similar_articles 返回结构兼容的最简 row 对象，
    只是为了复用 format_sources_for_llm/build_source_context，不重新查相似度。"""
    class _Row:
        def __init__(self, article):
            self.id = article.id
            self.title = article.title
            self.ai_summary = article.ai_summary
            self.content = article.content

    articles = db.query(Article).filter(Article.id.in_(article_ids)).all()
    by_id = {a.id: a for a in articles}
    return [_Row(by_id[aid]) for aid in article_ids if aid in by_id]


def export_calibration_sample():
    db = SessionLocal()
    try:
        run = (
            db.query(EvalRun)
            .filter(EvalRun.finished_at.isnot(None))
            .order_by(EvalRun.id.desc())
            .first()
        )
        # 找最近一次真的开了 --with-generation 的 run
        candidate = run
        while candidate and not candidate.config_snapshot.get("with_generation"):
            candidate = (
                db.query(EvalRun)
                .filter(EvalRun.id < candidate.id, EvalRun.finished_at.isnot(None))
                .order_by(EvalRun.id.desc())
                .first()
            )
        run = candidate

        if not run:
            print("No --with-generation eval run found — run `uv run python -m app.eval.run_eval --with-generation` first.")
            return

        results = (
            db.query(EvalResult)
            .filter(EvalResult.eval_run_id == run.id, EvalResult.generated_answer.isnot(None))
            .all()
        )
        by_id = {r.id: r for r in results}
        questions_by_result_id = {
            r.id: db.query(EvalQuestion).filter(EvalQuestion.id == r.eval_question_id).first()
            for r in results
        }

        def cat(result_id):
            return questions_by_result_id[result_id].category

        multi_hop = [r for r in results if cat(r.id) == "multi_hop"]
        paraphrase = [r for r in results if cat(r.id) == "paraphrase"]
        synthetic = [r for r in results if cat(r.id) == "synthetic"]
        random.shuffle(synthetic)
        sample = multi_hop + paraphrase + synthetic[:SYNTHETIC_SAMPLE_SIZE]

        OUTPUT_DIR.mkdir(exist_ok=True)
        out_path = OUTPUT_DIR / f"calibration_sample_run{run.id}.md"

        lines = [
            f"# Calibration sample — EvalRun #{run.id} ({run.started_at:%Y-%m-%d %H:%M})",
            f"Stratified sample: {len(multi_hop)} multi_hop + {len(paraphrase)} paraphrase + "
            f"{len(sample) - len(multi_hop) - len(paraphrase)} synthetic (of {len(synthetic)} available) = {len(sample)} total",
            "",
            "For each question below, read the sources + generated answer, then fill in **Your score:**",
            "faithfulness: 1.0 if every claim is supported, otherwise the fraction you'd judge supported (e.g. 0.67 for 2/3).",
            "relevancy: 1-5, same scale the judge used (1=doesn't address the question, 5=fully addresses it).",
            "",
            "---",
            "",
        ]

        for result in sample:
            q = questions_by_result_id[result.id]
            rows = _rows_from_article_ids(db, result.retrieved_article_ids)
            context = build_source_context(format_sources_for_llm(rows))

            lines.append(f"## [{q.external_id or q.id}] category: {q.category}")
            lines.append(f"**Question:** {q.question_text}")
            lines.append("")
            lines.append("**Sources shown to the model:**")
            lines.append("```")
            lines.append(context)
            lines.append("```")
            lines.append("")
            lines.append("**Generated answer:**")
            lines.append(result.generated_answer)
            lines.append("")
            lines.append(
                f"**Judge verdict:** faithfulness={result.faithfulness_score}, "
                f"relevancy={result.answer_relevancy_score}"
            )
            lines.append(f"**Judge's unsupported claims:** {result.unsupported_claims}")
            lines.append(f"**Judge reasoning (relevancy):** {result.judge_reasoning}")
            lines.append("")
            lines.append(f"**Your score:** faithfulness=___  relevancy=___  notes=___")
            lines.append("")
            lines.append("---")
            lines.append("")

        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote {len(sample)} questions to {out_path}")
        print("Hand-score each one, then fill in the same values into a companion CSV")
        print("(question_external_id, human_faithfulness, human_relevancy, human_notes) for compare_calibration.py.")

    finally:
        db.close()


if __name__ == "__main__":
    export_calibration_sample()
