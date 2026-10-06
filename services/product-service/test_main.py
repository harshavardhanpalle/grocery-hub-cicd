import os, tempfile
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")
from fastapi.testclient import TestClient
from main import app

def test_flow():
    with TestClient(app) as c:
        assert c.get("/health").json()["status"] == "ok"
        items = c.get("/products").json()
        assert len(items) >= 10
        assert c.get("/products/1").json()["name"] == "Bananas"
        assert c.get("/products/9999").status_code == 404
        assert c.post("/products", json={"name": "Honey", "category": "Pantry", "price": 5, "stock": 3}).status_code == 201
        assert c.post("/products/1/reserve?qty=100000").status_code == 409

def test_filter_and_reserve_reduces_stock():
    with TestClient(app) as c:
        fruit = c.get("/products", params={"category": "Fruit"}).json()
        assert fruit and all(p["category"] == "Fruit" for p in fruit)
        before = c.get("/products/2").json()["stock"]
        assert c.post("/products/2/reserve?qty=1").status_code == 200
        assert c.get("/products/2").json()["stock"] == before - 1

def test_simulated_bad_release_makes_health_fail(monkeypatch):
    with TestClient(app) as c:
        monkeypatch.setenv("SIMULATE_UNHEALTHY", "true")
        assert c.get("/health").status_code == 503
        monkeypatch.setenv("SIMULATE_UNHEALTHY", "false")
        assert c.get("/health").status_code == 200
