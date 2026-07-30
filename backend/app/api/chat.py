"""AI 检索接口"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import chat_rate_limit
from app.core.security import get_current_user
from app.models.chat_session import ChatSession
from app.models.user import User
from app.schemas.chat import (
    AskRequest, AskResponse, ArticleSource, ChatSessionResponse,
    SearchRequest, SearchResponse, SearchResult,
)
from app.services.ai_service import embed_text, generate_answer
from app.services.retrieval_service import retrieve_similar_articles, format_sources_for_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# 相似度低于这个阈值就直接拒答，不调 GPT（也是 eval runner 用来验证阈值本身合不合理的地方）
RAG_SIMILARITY_THRESHOLD = 0.3


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="语义搜索：用自然语言检索相关文章",
)
def semantic_search(
    payload: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. 把用户问题向量化
    query_embedding = embed_text(payload.query)
    if not query_embedding:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service unavailable, please try again.",
        )

    # 2. pgvector 余弦相似度检索（<=> 是余弦距离运算符，1 - distance = 相似度）
    rows = retrieve_similar_articles(db, current_user.id, query_embedding, payload.top_k)

    results = [
        SearchResult(
            id=row.id,
            title=row.title,
            url=row.url,
            ai_summary=row.ai_summary,
            similarity=round(float(row.similarity), 4),
        )
        for row in rows
    ]

    logger.info(
        f"Semantic search: '{payload.query[:50]}' → {len(results)} results "
        f"(top similarity: {results[0].similarity if results else 'N/A'})"
    )

    return SearchResponse(query=payload.query, results=results)


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="RAG 问答：检索相关文章 → GPT 生成答案 + 引用来源",
)
def ask(
    payload: AskRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(chat_rate_limit),
    db: Session = Depends(get_db),
):
    # 1. 向量化问题
    query_embedding = embed_text(payload.question)
    if not query_embedding:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service unavailable, please try again.",
        )

    # 2. 检索最相关的文章（同时拿 content 用于生成）
    rows = retrieve_similar_articles(db, current_user.id, query_embedding, payload.top_k)

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No articles found in your library. Save some articles first.",
        )

    # 3. 相似度过低说明问题与库里文章完全无关，直接返回不调 GPT
    max_similarity = max(float(row.similarity) for row in rows)
    if max_similarity < RAG_SIMILARITY_THRESHOLD:
        logger.info(f"Off-topic question (max similarity {max_similarity:.3f}): '{payload.question[:50]}'")
        off_topic_answer = "Your library doesn't have any articles related to this question.\n\nCairn answers questions based on articles you've saved. Try asking something related to your saved content."
        chat_session = ChatSession(user_id=current_user.id, question=payload.question, answer=off_topic_answer)
        chat_session.sources = []
        db.add(chat_session)
        db.commit()
        return AskResponse(
            question=payload.question,
            answer=off_topic_answer,
            sources=[],
        )

    # 4. 构造传给 GPT 的 sources（带编号）
    sources_for_llm = format_sources_for_llm(rows)

    # 5. GPT 生成回答
    answer = generate_answer(payload.question, sources_for_llm)
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service unavailable, please try again.",
        )

    # 6. 组装引用来源（返回给前端展示）
    sources = [
        ArticleSource(
            index=i + 1,
            id=row.id,
            title=row.title,
            url=row.url,
            saved_at=row.created_at,
            similarity=round(float(row.similarity), 4),
        )
        for i, row in enumerate(rows)
    ]

    # 7. 保存到历史记录
    try:
        chat_session = ChatSession(user_id=current_user.id, question=payload.question, answer=answer)
        chat_session.sources = [s.model_dump(mode="json") for s in sources]
        db.add(chat_session)
        db.commit()
        logger.info(f"Saved chat session id={chat_session.id} for user_id={current_user.id}")
    except Exception as e:
        logger.error(f"Failed to save chat session: {e}", exc_info=True)
        db.rollback()

    logger.info(
        f"RAG ask: '{payload.question[:50]}' → {len(sources)} sources, "
        f"answer {len(answer)} chars"
    )

    return AskResponse(
        question=payload.question,
        answer=answer,
        sources=sources,
    )


@router.get(
    "/history",
    response_model=list[ChatSessionResponse],
    summary="获取聊天历史记录",
)
def get_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        ChatSessionResponse(
            id=s.id,
            question=s.question,
            answer=s.answer,
            sources=[ArticleSource(**src) for src in s.sources],
            created_at=s.created_at,
        )
        for s in sessions
    ]