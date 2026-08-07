"""
retrieve_similar_articles 是手写的原生 SQL(str(embedding) 拼成 vector 字面量,
用 pgvector 的 <=> 算 cosine distance)。这种写法对不对,只能靠真实 Postgres + pgvector
跑一遍才能验证——读代码看不出向量字面量语法对不对、ORDER BY 是否真的按最近排序,
mock 掉数据库更是直接测不出来。所以这里全部用真实的 devvault_test 数据库,不 mock。
"""
from app.services.retrieval_service import retrieve_similar_articles

DIM = 1536


def _vec(nonzero: dict[int, float]) -> list[float]:
    """按位置给几个维度赋非零值,其余补 0,拼出一个 1536 维向量。"""
    v = [0.0] * DIM
    for pos, val in nonzero.items():
        v[pos] = val
    return v


# 三个方向:e0(纯 0 号维度)、e0 和 e1 各半(方向在 e0/e1 之间)、e1(纯 1 号维度)
E0 = _vec({0: 1.0})
E0_E1_MIX = _vec({0: 0.7, 1: 0.7})
E1 = _vec({1: 1.0})


def test_ranks_by_cosine_similarity_to_query(db_session, make_user, make_article):
    user = make_user(email="retrieval@example.com")
    close = make_article(user.id, title="Closest", embedding=E0)
    partial = make_article(user.id, title="Partial", embedding=E0_E1_MIX)
    unrelated = make_article(user.id, title="Unrelated", embedding=E1)

    rows = retrieve_similar_articles(db_session, user.id, query_embedding=E0, top_k=10)

    assert [row.id for row in rows] == [close.id, partial.id, unrelated.id]
    assert rows[0].similarity == 1.0  # 同方向,cosine distance = 0
    assert 0 < rows[1].similarity < 1  # 介于中间
    assert rows[2].similarity == 0.0  # 正交,完全不相关


def test_scoped_to_current_user_only(db_session, make_user, make_article):
    user_a = make_user(email="scope-a@example.com")
    user_b = make_user(email="scope-b@example.com")

    # user_b 存了一篇跟 query 完全匹配的文章,但 user_a 查询时不该看到它
    make_article(user_b.id, title="Not yours", embedding=E0)
    mine = make_article(user_a.id, title="Mine", embedding=E0_E1_MIX)

    rows = retrieve_similar_articles(db_session, user_a.id, query_embedding=E0, top_k=10)

    assert [row.id for row in rows] == [mine.id]


def test_empty_library_returns_no_rows(db_session, make_user):
    user = make_user(email="empty-lib@example.com")

    rows = retrieve_similar_articles(db_session, user.id, query_embedding=E0, top_k=10)

    assert rows == []


def test_articles_without_embedding_are_excluded(db_session, make_user, make_article):
    user = make_user(email="no-embedding@example.com")
    make_article(user.id, title="Not processed yet", embedding=None, status="pending")
    matching = make_article(user.id, title="Processed", embedding=E0)

    rows = retrieve_similar_articles(db_session, user.id, query_embedding=E0, top_k=10)

    assert [row.id for row in rows] == [matching.id]


def test_top_k_limits_result_count(db_session, make_user, make_article):
    user = make_user(email="topk@example.com")
    for i in range(5):
        make_article(user.id, title=f"Article {i}", embedding=E0)

    rows = retrieve_similar_articles(db_session, user.id, query_embedding=E0, top_k=2)

    assert len(rows) == 2
