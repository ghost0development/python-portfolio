def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "modules" in data


def test_register(client):
    r = client.post("/auth/register", json={
        "email": "reg@test.pl",
        "username": "reguser",
        "password": "Test1234!"
    })
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data


def test_login(client):
    client.post("/auth/register", json={
        "email": "login@test.pl",
        "username": "loginuser",
        "password": "Test1234!"
    })
    r = client.post("/auth/login", json={
        "email": "login@test.pl",
        "password": "Test1234!"
    })
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data


def test_me(auth_client):
    r = auth_client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "auth@test.pl"


def test_shorten_and_redirect(auth_client, client):
    r = auth_client.post("/api/shortener/shorten?target_url=https://example.com")
    assert r.status_code == 200
    code = r.json()["short_code"]
    r2 = client.get(f"/api/shortener/r/{code}", follow_redirects=False)
    assert r2.status_code == 302
    assert r2.headers["location"] == "https://example.com"


def test_blog_graphql(client):
    q = {"query": "{ posts { id title } }"}
    r = client.post("/api/blog", json=q)
    assert r.status_code == 200
    data = r.json()
    assert "data" in data


def test_chat(client):
    r = client.post("/api/chat/message", json={
        "message": "Hello",
        "model": "gpt-3.5-turbo"
    })
    assert r.status_code in (200, 401, 502)


def test_queue_create(auth_client):
    r = auth_client.post("/api/queue/tasks", json={
        "task_type": "generic",
        "name": "test task"
    })
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["status"] in ("pending", "running")
