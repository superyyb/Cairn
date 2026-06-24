"""聊天/检索相关 schemas"""
from datetime import datetime
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
    question: str
    answer: str
    sources: list[ArticleSource]

class ChatSessionResponse(BaseModel):
    id: int
    question: str
    answer: str
    sources: list[ArticleSource]
    created_at: datetime

    model_config = {"from_attributes": True}