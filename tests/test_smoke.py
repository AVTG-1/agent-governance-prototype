from fastapi.testclient import TestClient

from app.main import app


def test_index_served():
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert "Kaiyo Securities" in r.text
    assert client.get("/tokens.css").status_code == 200
    assert client.get("/fonts/instrument-sans-400.woff").status_code == 200
