import os, sys
os.environ["NO_AUTO_APP"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "t"})
    return app.test_client()


def login(c):
    c.post("/register", data={"username": "u1", "password": "pass1"})
    return c.post("/login", json={"username": "u1", "password": "pass1"})


def test_health(client):
    assert client.get("/healthz").json["status"] == "ok"
    assert client.get("/readyz").status_code == 200


def test_requires_auth(client):
    assert client.get("/api/tasks").status_code == 401
    assert client.get("/").status_code == 302


def test_bad_login(client):
    assert client.post("/login", json={"username": "x", "password": "y"}).status_code == 401


def test_crud(client):
    assert login(client).status_code == 200
    r = client.post("/api/tasks", json={"title": "a", "description": "d"})
    assert r.status_code == 201
    tid = r.json["id"]
    assert client.get(f"/api/tasks/{tid}").json["title"] == "a"
    assert client.put(f"/api/tasks/{tid}", json={"done": True}).json["done"] is True
    assert len(client.get("/api/tasks").json) == 1
    assert client.delete(f"/api/tasks/{tid}").status_code == 204
    assert client.get(f"/api/tasks/{tid}").status_code == 404


def test_validation_and_404(client):
    login(client)
    assert client.post("/api/tasks", json={}).status_code == 400
    assert client.get("/api/nope").status_code == 404


def test_ui_flow(client):
    login(client)
    client.post("/tasks/add", data={"title": "ui task"})
    assert b"ui task" in client.get("/").data


def test_metrics(client):
    client.get("/healthz")
    assert b"http_requests_total" in client.get("/metrics").data
