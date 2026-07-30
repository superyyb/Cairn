"""一次 eval 跑批的记录"""
import json
from datetime import datetime

from sqlalchemy import Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvalRun(Base):
    """
    一次 run_eval.py 的调用。

    config_snapshot_json 是无 schema 的 dict（阈值、embedding 模型、top_k、题目数量等），
    故意不建成具体列——以后 Phase 2 加裁判模型相关的配置，不需要再加迁移。
    聚合指标（平均 precision、MRR 等）不存在这张表上，跑汇总时从 EvalResult 现算，
    避免"存的值"和"当场算出来的值"对不上。
    """
    __tablename__ = "eval_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    eval_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    config_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    @property
    def config_snapshot(self) -> dict:
        return json.loads(self.config_snapshot_json)

    @config_snapshot.setter
    def config_snapshot(self, value: dict) -> None:
        self.config_snapshot_json = json.dumps(value)

    def __repr__(self):
        return f"<EvalRun {self.id} started={self.started_at}>"
