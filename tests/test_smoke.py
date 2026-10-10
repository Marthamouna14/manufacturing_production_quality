from fastapi.testclient import TestClient
from app.main import app
def test_health():
    c=TestClient(app)
    assert c.get("/health").json()=={"status":"ok"}
def test_openapi():
    c=TestClient(app)
    r=c.get("/openapi.json")
    assert r.status_code==200
    assert "/api/v1/auth/register" in r.json()["paths"]
