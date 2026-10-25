import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from app.main import app
from app.core.database import get_db

# ==========================================
# SENIOR TECHNIQUE: Mock the Database
# ==========================================
# This overrides the real database connection during tests.
# It ensures our tests pass in the CI/CD pipeline without needing a live Neon DB.
async def override_get_db():
    mock_db = AsyncMock()
    yield mock_db

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# ==========================================
# TESTS
# ==========================================

def test_health_check():
    """Test that the API is running and healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_root_endpoint():
    """Test that the root endpoint returns HTML or JSON successfully."""
    response = client.get("/")
    assert response.status_code == 200

def test_book_appointment_missing_fields():
    """
    Test that the API rejects incomplete booking requests with a 422 error.
    This validates our Pydantic schema enforcement.
    """
    response = client.post("/api/v1/appointments", json={})
    assert response.status_code == 422
    assert "Validation Failed" in response.json()["error"]

def test_book_appointment_invalid_uuid():
    """
    Test that the API rejects invalid UUID formats for doctor/patient IDs.
    """
    response = client.post("/api/v1/appointments", json={
        "doctor_id": "not-a-uuid",
        "patient_id": "not-a-uuid",
        "start_time": "2025-10-25T10:00:00Z"
    })
    assert response.status_code == 422

def test_get_availability_invalid_date_format():
    """
    Test that the availability endpoint rejects invalid date formats.
    This validates our business logic validation before it hits the DB.
    """
    # Using a dummy UUID, the date format should fail before the DB lookup
    response = client.get("/api/v1/doctors/00000000-0000-0000-0000-000000000000/availability?date=2024/10/10")
    assert response.status_code == 400
    assert "Invalid date format" in response.json()["message"]

def test_get_appointment_details_invalid_uuid():
    """
    Test that fetching an appointment with an invalid UUID returns a 422 error.
    """
    response = client.get("/api/v1/appointments/invalid-uuid")
    assert response.status_code == 422