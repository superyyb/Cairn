"""一次 eval 跑批中，单条题目的检索结果"""
import json
from datetime import datetime

from sqlalchemy import Text, Float, Boolean, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvalResult(Base):
    """
    一个 (run, question) 组合的检索结果。

    precision_at_k / recall_at_k / reciprocal_rank 对 true_negative 题目没有意义，留 None；
    passed_threshold_check 只对 true_negative 题目有意义（是否正确拒答），其他类型留 None。
    Phase 1 不含任何生成层字段（faithfulness 等），那些留给 Phase 2 单独加一次迁移。
    """
    __tablename__ = "eval_results"
    __table_args__ = (
        UniqueConstraint("eval_run_id", "eval_question_id", name="uk_eval_results_run_question"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    eval_run_id: Mapped[int] = mapped_column(
        ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    eval_question_id: Mapped[int] = mapped_column(
        ForeignKey("eval_questions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    retrieved_article_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    similarities_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    precision_at_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall_at_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    reciprocal_rank: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed_threshold_check: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # ===== Phase 2: 生成层(faithfulness / relevancy)，true_negative 或跳过生成的题目留 None =====
    generated_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 0.0-1.0，在 run_eval.py 里由 claims 的 supported 布尔值算出来，不是让 LLM 直接打一个分
    faithfulness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    unsupported_claims_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # 1-5 的 Likert 分，和 faithfulness 的 0-1 比例不是一个量纲，见 EvalRun.config_snapshot["answer_relevancy_scale"]
    answer_relevancy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    judge_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    judge_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    top_k_used: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    @property
    def retrieved_article_ids(self) -> list[int]:
        return json.loads(self.retrieved_article_ids_json)

    @retrieved_article_ids.setter
    def retrieved_article_ids(self, value: list[int]) -> None:
        self.retrieved_article_ids_json = json.dumps(value)

    @property
    def similarities(self) -> list[float]:
        return json.loads(self.similarities_json)

    @similarities.setter
    def similarities(self, value: list[float]) -> None:
        self.similarities_json = json.dumps(value)

    @property
    def unsupported_claims(self) -> list[dict]:
        return json.loads(self.unsupported_claims_json)

    @unsupported_claims.setter
    def unsupported_claims(self, value: list[dict]) -> None:
        self.unsupported_claims_json = json.dumps(value)

    def __repr__(self):
        return f"<EvalResult run={self.eval_run_id} q={self.eval_question_id}>"
