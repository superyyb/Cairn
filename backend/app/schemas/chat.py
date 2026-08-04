"""聊天/检索相关 schemas"""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    id: int
    title: str
    url: str
    ai_summary: str | None
    similarity: float

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


# ===== RAG Ask =====

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=10)


class ArticleSource(BaseModel):
    """回答中引用的文章来源"""
    index: int          # 引用编号，对应答案里的 [1][2]
    id: int
    title: str
    url: str
    saved_at: datetime
    similarity: float


class AskResponse(BaseModel):
    # 保存 chat_session 失败时(见 chat.py 里那段吞异常的 try/except)老实返回 None，
    # 不假装一定有 id 能挂反馈
    id: int | None
    question: str
    answer: str
    sources: list[ArticleSource]


# ===== Feedback =====

FeedbackReason = Literal["wrong_info", "not_relevant", "missing_sources", "other"]


class FeedbackRequest(BaseModel):
    rating: Literal["up", "down"]
    reason: FeedbackReason | None = None
    comment: str | None = Field(default=None, max_length=500)


class FeedbackResponse(BaseModel):
    rating: Literal["up", "down"]
    reason: str | None
    comment: str | None

    @classmethod
    def from_model(cls, feedback) -> "FeedbackResponse":
        # ChatFeedback.rating 是 bool，跟这里的 "up"/"down" 不是一个类型，
        # 不能靠 from_attributes 自动转，必须手动映射
        return cls(rating="up" if feedback.rating else "down", reason=feedback.reason, comment=feedback.comment)


class ChatSessionResponse(BaseModel):
    id: int
    question: str
    answer: str
    sources: list[ArticleSource]
    created_at: datetime
    feedback: FeedbackResponse | None = None

    model_config = {"from_attributes": True}