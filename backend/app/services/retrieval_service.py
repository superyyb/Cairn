"""共享的检索逻辑 —— /chat/search、/chat/ask、eval runner 都用这一个函数。"""
from sqlalchemy import text


def retrieve_similar_articles(db, user_id: int, query_embedding: list[float], top_k: int):
    """按余弦相似度检索用户名下的文章，返回 id/title/url/content/ai_summary/created_at/similarity。"""
    sql = text("""
        SELECT
            id, title, url, content, ai_summary, created_at,
            1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM articles
        WHERE
            user_id = :user_id
            AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """)
    return db.execute(sql, {
        "embedding": str(query_embedding),
        "user_id": user_id,
        "top_k": top_k,
    }).fetchall()


def format_sources_for_llm(rows) -> list[dict]:
    """
    把检索结果整理成 generate_answer / eval 裁判都要用的统一格式。
    共用这一份，避免 chat.py 和 eval runner 各自拼一份稍微不一样的 sources 结构。
    """
    return [
        {
            "index": i + 1,
            "title": row.title,
            "ai_summary": row.ai_summary,
            "content": row.content,
        }
        for i, row in enumerate(rows)
    ]
