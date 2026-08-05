"""
Eval 专用的 AI 调用 —— 和 ai_service.py 分开放，因为这里的函数从来不会被真实用户请求
调用到，只在跑 eval 语料库/题库的脚本里用。ai_service.py 保持"这些都是生产路径会调用
的函数"这个边界清晰。
"""
import logging

from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.ai_service import build_source_context, client

logger = logging.getLogger(__name__)


class SyntheticQuestion(BaseModel):
    question: str = Field(
        description="A natural-language question a user might ask, answerable using only the "
        "summary below. Never mention 'the article' or 'the summary' explicitly."
    )


def generate_synthetic_question(article_title: str, article_summary: str) -> str | None:
    """
    Phase 1 eval 题目生成器：每篇 eval 文章生成一条问题，问题内容完全来自它自己的摘要。
    成本低、可规模化，但故意"太容易"——措辞会偏向和摘要本身相似，
    这个偏差由人工写的 adversarial 题目集来弥补，不指望这批题目单独测出真实短板。
    """
    system_prompt = (
        "You write evaluation questions for a RAG system test suite. Given an article's title "
        "and summary, write ONE natural-language question whose answer is fully contained in "
        "the summary. Ask about the core idea, not trivia."
    )
    user_prompt = f"Title: {article_title}\n\nSummary: {article_summary}\n\nWrite one question."

    try:
        response = client.beta.chat.completions.parse(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=SyntheticQuestion,
            temperature=0.5,
        )
        result = response.choices[0].message.parsed
        return result.question if result else None
    except Exception as e:
        logger.error(f"generate_synthetic_question error: {e}")
        return None


# ===== Phase 2: LLM-as-judge，测生成层有没有瞎编 =====

class ClaimVerdict(BaseModel):
    claim: str = Field(
        description="A single discrete factual claim stated in the answer, phrased standalone."
    )
    supported: bool = Field(
        description="True only if this exact claim is directly stated or clearly implied by the "
        "provided sources. False if it adds specifics, numbers, names, or conclusions not present "
        "in them — even if the claim happens to be true in general/real-world knowledge."
    )
    reason: str = Field(description="One sentence: which source (by [n]) supports it, or why not.")


class GenerationJudgment(BaseModel):
    claims: list[ClaimVerdict] = Field(
        description="Break the ANSWER's '## Answer' section into its discrete factual claims "
        "(usually 2-6). Skip citation brackets, headers, and the '## Coverage gaps' section "
        "itself — only judge substantive claims about the subject matter."
    )
    answer_relevancy: int = Field(
        ge=1,
        le=5,
        description="1=does not address the question at all, 3=partially/tangentially addresses "
        "it, 5=directly and completely addresses it. Score this independent of faithfulness — an "
        "answer can be fully relevant but unfaithful, or faithful but irrelevant.",
    )
    relevancy_reasoning: str = Field(description="One or two sentences justifying the relevancy score.")


def judge_generation(question: str, sources: list[dict], answer: str) -> GenerationJudgment | None:
    """
    评委不直接被问"这个回答忠实度打几分"——那样它完全可以不做任何真实核对，
    直接编一个听起来合理的数字。这里强制它先把回答拆成一条条可核查的声明，
    每条单独判断有没有依据，faithfulness_score 由调用方(run_eval.py)用这些
    布尔值算出来，不是模型自己吐一个分。

    对照的上下文用 build_source_context（跟 generate_answer 用的是同一份——
    检查"有没有依据"必须对照模型当时实际看到的文本，不能是 sources 里更完整的 content）。
    """
    context = build_source_context(sources)

    system_prompt = """You are grading a RAG (retrieval-augmented generation) answer for faithfulness and relevancy.

Faithfulness: judge ONLY against the sources given below — not general knowledge, not what you know
to be true from elsewhere. If the answer states something not present in the sources, mark that
claim unsupported even if it is factually correct in the real world.

Relevancy: judge whether the answer actually addresses the question asked, independent of whether
it's faithful."""

    user_prompt = f"Sources:\n{context}\n\nQuestion: {question}\n\nAnswer:\n{answer}\n\nExtract claims and score."

    try:
        response = client.beta.chat.completions.parse(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=GenerationJudgment,
            temperature=0.0,  # 裁判要尽量稳定，不像生成那边用 0.3
        )
        return response.choices[0].message.parsed
    except Exception as e:
        logger.error(f"judge_generation error: {e}")
        return None
