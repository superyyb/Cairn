"""覆盖 /api/articles/* —— 重点是保存去重和跨用户越权访问(IDOR)。"""


# ---------- save / duplicate ----------

def test_save_article_creates_new(client, make_user, auth_header):
    user = make_user(email="saver@example.com")
    resp = client.post(
        "/api/articles",
        json={"url": "https://example.com/post-1", "title": "A Post", "content": "body text"},
        headers=auth_header(user),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_new"] is True
    assert body["article"]["title"] == "A Post"


def test_save_article_duplicate_returns_existing_without_creating_a_second_row(client, make_user, auth_header, db_session):
    user = make_user(email="dupsaver@example.com")
    payload = {"url": "https://example.com/post-2", "title": "Another Post"}

    first = client.post("/api/articles", json=payload, headers=auth_header(user))
    second = client.post("/api/articles", json=payload, headers=auth_header(user))

    assert first.json()["is_new"] is True
    assert second.json()["is_new"] is False
    assert second.json()["article"]["id"] == first.json()["article"]["id"]

    from app.models.article import Article
    count = db_session.query(Article).filter(Article.user_id == user.id).count()
    assert count == 1


# ---------- ownership / IDOR ----------

def test_get_article_not_owned_returns_404(client, make_user, make_article, auth_header):
    owner = make_user(email="owner1@example.com")
    intruder = make_user(email="intruder1@example.com")
    article = make_article(owner.id, title="Owner's article")

    resp = client.get(f"/api/articles/{article.id}", headers=auth_header(intruder))
    assert resp.status_code == 404


def test_get_own_article_succeeds(client, make_user, make_article, auth_header):
    owner = make_user(email="owner2@example.com")
    article = make_article(owner.id, title="Owner's article")

    resp = client.get(f"/api/articles/{article.id}", headers=auth_header(owner))
    assert resp.status_code == 200
    assert resp.json()["title"] == "Owner's article"


def test_star_article_not_owned_returns_404(client, make_user, make_article, auth_header):
    owner = make_user(email="owner3@example.com")
    intruder = make_user(email="intruder3@example.com")
    article = make_article(owner.id, title="Owner's article")

    resp = client.patch(
        f"/api/articles/{article.id}/star",
        json={"is_starred": True},
        headers=auth_header(intruder),
    )
    assert resp.status_code == 404


def test_delete_article_not_owned_returns_404_and_leaves_it_intact(client, make_user, make_article, auth_header):
    owner = make_user(email="owner4@example.com")
    intruder = make_user(email="intruder4@example.com")
    article = make_article(owner.id, title="Owner's article")

    resp = client.delete(f"/api/articles/{article.id}", headers=auth_header(intruder))
    assert resp.status_code == 404

    # 确认真的没被删掉——用 owner 自己的身份还能拿到
    still_there = client.get(f"/api/articles/{article.id}", headers=auth_header(owner))
    assert still_there.status_code == 200


def test_delete_own_article_succeeds(client, make_user, make_article, auth_header):
    owner = make_user(email="owner5@example.com")
    article = make_article(owner.id, title="Owner's article")

    resp = client.delete(f"/api/articles/{article.id}", headers=auth_header(owner))
    assert resp.status_code == 204

    gone = client.get(f"/api/articles/{article.id}", headers=auth_header(owner))
    assert gone.status_code == 404


def test_list_articles_only_returns_current_users_articles(client, make_user, make_article, auth_header):
    user_a = make_user(email="lista@example.com")
    user_b = make_user(email="listb@example.com")
    make_article(user_a.id, title="A1")
    make_article(user_a.id, title="A2")
    make_article(user_b.id, title="B1")

    resp = client.get("/api/articles", headers=auth_header(user_a))
    assert resp.status_code == 200
    titles = {a["title"] for a in resp.json()}
    assert titles == {"A1", "A2"}
