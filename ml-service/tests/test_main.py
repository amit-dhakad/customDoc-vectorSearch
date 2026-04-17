from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_health():
    """Verify that the ML Service health check endpoint is alive."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "online", "service": "ml-service"}

def test_system_stats():
    """Verify that the system telemetry endpoint returns correct keys."""
    response = client.get("/system/stats")
    assert response.status_code == 200
    data = response.json()
    assert "cpu" in data
    assert "memory" in data
    assert "device" in data
    assert "pipeline_status" in data
