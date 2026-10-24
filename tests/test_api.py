import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_booking_within_1_hour_fails():
    from datetime import datetime, timedelta
    import pytz
    import uuid
    
    now = datetime.now(pytz.utc)
    soon = now + timedelta(minutes=30)
    
    payload = {
        "doctor_id": str(uuid.uuid4()), # Random UUID
        "patient_id": str(uuid.uuid4()),
        "start_time": soon.isoformat()
    }
    response = client.post("/api/v1/appointments", json=payload)
    assert response.status_code == 400
    assert "1 hour in advance" in response.json()["detail"]