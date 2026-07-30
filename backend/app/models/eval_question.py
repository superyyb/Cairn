"""RAG eval 题库"""
import json
from datetime import datetime

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvalQuestion(Base):
    """
    一条 eval 题目。

    category 取值: synthetic(从摘要自动生成) / paraphrase(措辞故意和摘要不一样) /
                  multi_hop(答案需要综合多篇文章) / true_negative(库里没有相关文章)
    不用 DB CHECK 约束，只在代码里保证，和 Article.status 的做法一致。
    """
    __tablename__ = "eval_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    # 该被检索到的文章 id 列表；true_negative 恒为 []
    expected_article_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    # synthetic 问题的来源文章（单篇），方便溯源；multi_hop/其他类型可以不填，
    # 完整的期望文章列表始终以 expected_article_ids_json 为准
    source_article_id: Mapped[int | None] = mapped_column(
        ForeignKey("articles.id", ondelete="SET NULL"), nullable=True
    )

    # adversarial fixture 里的稳定 key（如 "adv_001"），用于按名字 upsert，不依赖数据库自增 id
    external_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    @property
    def expected_article_ids(self) -> list[int]:
        return json.loads(self.expected_article_ids_json)

    @expected_article_ids.setter
    def expected_article_ids(self, value: list[int]) -> None:
        self.expected_article_ids_json = json.dumps(value)

    def __repr__(self):
        return f"<EvalQuestion {self.id} [{self.category}] {self.question_text[:40]}>"
