import os, tempfile
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")
from fastapi.testclient import TestClient
from main import app

def test_health_and_validation():
    with TestClient(app) as c:
        assert c.get("/health").json()["status"] == "ok"
        assert c.post("/orders", json={"customer": "A", "address": "B", "items": []}).status_code == 422
        assert c.get("/orders/999").status_code == 404
