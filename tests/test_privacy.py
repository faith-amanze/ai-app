import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.cache import cache

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    cache.clear()
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def signup_and_login(client, email, password="correct-horse"):
    assert client.post("/auth/register", json={"email": email, "password": password}).status_code == 201
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_user_b_cannot_read_or_modify_user_a_conversation(client):
    a = signup_and_login(client, "a@example.com")
    b = signup_and_login(client, "b@example.com")

    convo = client.post("/conversations", json={"title": "A secret"}, headers=a).json()
    cid = convo["id"]
    r = client.post(f"/conversations/{cid}/messages", json={"content": "my private note"}, headers=a)
    assert r.status_code == 201

    # B cannot read, write, or see it in a list
    assert client.get(f"/conversations/{cid}", headers=b).status_code == 404
    assert client.post(f"/conversations/{cid}/messages", json={"content": "hi"}, headers=b).status_code == 404
    assert client.get("/conversations", headers=b).json() == []

    # A still has full access and exactly 2 messages (B's write left no trace)
    detail = client.get(f"/conversations/{cid}", headers=a).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]


def test_endpoints_require_authentication(client):
    assert client.get("/conversations").status_code == 401
    assert client.post("/conversations", json={}).status_code == 401
    assert client.get("/conversations", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_password_is_stored_hashed_and_bad_login_fails(client):
    signup_and_login(client, "c@example.com", "my-plain-password")
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT password_hash FROM users WHERE email='c@example.com'")).scalar()
    assert stored != "my-plain-password" and stored.startswith("$2")
    assert client.post("/auth/login", data={"username": "c@example.com", "password": "wrong"}).status_code == 401


def test_cache_is_used_on_repeat_call(client):
    h = signup_and_login(client, "d@example.com")
    assert client.get("/ai/define?term=jwt", headers=h).json()["cached"] is False
    assert client.get("/ai/define?term=jwt", headers=h).json()["cached"] is True
