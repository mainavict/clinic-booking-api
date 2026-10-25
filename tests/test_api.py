import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.main import app
from app.core.database import get_db

# ==========================================
# MOCK THE DATABASE FOR FAST EXECUTION
# ==========================================
async def override_get_db():
    mock_db = AsyncMock()
    yield mock_db

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# Dummy UUIDs for testing
DUMMY_DOCTOR_ID = str(uuid.uuid4())
DUMMY_PATIENT_ID = str(uuid.uuid4())
DUMMY_APPT_ID = str(uuid.uuid4())

# ==========================================
# 1. SYSTEM & ROUTING TESTS
# ==========================================
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200

def test_invalid_uuid_format():
    """Tests that Pydantic correctly rejects malformed UUIDs."""
    response = client.get("/api/v1/appointments/not-a-uuid")
    assert response.status_code == 422

# ==========================================
# 2. BOOKING ENDPOINT EDGE CASES (POST /appointments)
# ==========================================
@patch('app.api.v1.endpoints.appointment_service.book_appointment')
def test_book_appointment_in_the_past(mock_book):
    mock_book.side_effect = HTTPException(status_code=400, detail="Cannot book appointments in the past.")
    response = client.post("/api/v1/appointments", json={
        "doctor_id": DUMMY_DOCTOR_ID, "patient_id": DUMMY_PATIENT_ID, 
        "start_time": "2020-01-01T10:00:00Z"
    })
    assert response.status_code == 400
    assert "past" in response.json()["message"]

@patch('app.api.v1.endpoints.appointment_service.book_appointment')
def test_book_appointment_less_than_1_hour(mock_book):
    mock_book.side_effect = HTTPException(status_code=400, detail="Appointments must be booked at least 1 hour in advance.")
    future_time = (datetime.utcnow() + timedelta(minutes=30)).isoformat() + "Z"
    response = client.post("/api/v1/appointments", json={
        "doctor_id": DUMMY_DOCTOR_ID, "patient_id": DUMMY_PATIENT_ID, "start_time": future_time
    })
    assert response.status_code == 400
    assert "1 hour" in response.json()["message"]

@patch('app.api.v1.endpoints.appointment_service.book_appointment')
def test_book_appointment_more_than_60_days(mock_book):
    mock_book.side_effect = HTTPException(status_code=400, detail="Appointments cannot be booked more than 60 days in advance.")
    future_time = (datetime.utcnow() + timedelta(days=65)).isoformat() + "Z"
    response = client.post("/api/v1/appointments", json={
        "doctor_id": DUMMY_DOCTOR_ID, "patient_id": DUMMY_PATIENT_ID, "start_time": future_time
    })
    assert response.status_code == 400
    assert "60 days" in response.json()["message"]

@patch('app.api.v1.endpoints.appointment_service.book_appointment')
def test_book_appointment_during_lunch(mock_book):
    mock_book.side_effect = HTTPException(status_code=400, detail="Requested time falls during the doctor's lunch break.")
    response = client.post("/api/v1/appointments", json={
        "doctor_id": DUMMY_DOCTOR_ID, "patient_id": DUMMY_PATIENT_ID, 
        "start_time": "2025-12-01T13:15:00Z"
    })
    assert response.status_code == 400
    assert "lunch" in response.json()["message"].lower()

@patch('app.api.v1.endpoints.appointment_service.book_appointment')
def test_book_appointment_double_booking(mock_book):
    mock_book.side_effect = HTTPException(status_code=409, detail="This slot is already booked.")
    response = client.post("/api/v1/appointments", json={
        "doctor_id": DUMMY_DOCTOR_ID, "patient_id": DUMMY_PATIENT_ID, 
        "start_time": "2025-12-01T10:00:00Z"
    })
    assert response.status_code == 409
    assert "already booked" in response.json()["message"]

@patch('app.api.v1.endpoints.appointment_service.book_appointment')
def test_book_appointment_success(mock_book):
    # FIX: Provide a complete mock response that matches the AppointmentResponse schema
    mock_book.return_value = {
        "id": DUMMY_APPT_ID,
        "doctor_id": DUMMY_DOCTOR_ID,
        "patient_id": DUMMY_PATIENT_ID,
        "start_time": "2025-12-01T10:00:00Z",
        "end_time": "2025-12-01T10:30:00Z",
        "status": "BOOKED"
    }
    response = client.post("/api/v1/appointments", json={
        "doctor_id": DUMMY_DOCTOR_ID, "patient_id": DUMMY_PATIENT_ID, 
        "start_time": "2025-12-01T10:00:00Z"
    })
    assert response.status_code == 201

# ==========================================
# 3. AVAILABILITY ENDPOINT EDGE CASES (GET /availability)
# ==========================================
def test_get_availability_invalid_date_format():
    response = client.get(f"/api/v1/doctors/{DUMMY_DOCTOR_ID}/availability?date=2025/12/01")
    assert response.status_code == 400
    assert "Invalid date format" in response.json()["message"]

@patch('app.api.v1.endpoints.availability_service.get_doctor_availability')
def test_get_availability_doctor_not_found(mock_avail):
    mock_avail.side_effect = HTTPException(status_code=404, detail="Doctor not found")
    response = client.get(f"/api/v1/doctors/{DUMMY_DOCTOR_ID}/availability?date=2025-12-01")
    assert response.status_code == 404

# ==========================================
# 4. CANCEL & RESCHEDULE EDGE CASES
# ==========================================
@patch('app.api.v1.endpoints.appointment_service.cancel_appointment')
def test_cancel_already_cancelled(mock_cancel):
    mock_cancel.side_effect = HTTPException(status_code=400, detail="Appointment is already cancelled")
    response = client.patch(f"/api/v1/appointments/{DUMMY_APPT_ID}/cancel", json={"reason": "Changed my mind"})
    assert response.status_code == 400

@patch('app.api.v1.endpoints.appointment_service.reschedule_appointment')
def test_reschedule_cancelled_appointment(mock_reschedule):
    mock_reschedule.side_effect = HTTPException(status_code=400, detail="Cannot reschedule a cancelled appointment")
    response = client.patch(f"/api/v1/appointments/{DUMMY_APPT_ID}/reschedule", json={
        "new_start_time": "2025-12-02T10:00:00Z"
    })
    assert response.status_code == 400

# ==========================================
# 5. DOCTOR & PATIENT CREATION EDGE CASES
# ==========================================
# FIX: Patch the function where it is USED (in endpoints), not where it is defined
@patch('app.api.v1.endpoints.create_patient')
def test_create_patient_duplicate_email(mock_create):
    mock_create.side_effect = HTTPException(status_code=409, detail="Patient with this email already exists.")
    response = client.post("/api/v1/patients", json={
        "name": "John Doe", "email": "john@example.com", "password": "password123"
    })
    assert response.status_code == 409

@patch('app.api.v1.endpoints.create_doctor')
def test_create_doctor_violates_25_percent_lunch_rule(mock_create):
    mock_create.side_effect = HTTPException(status_code=400, detail="Scheduling conflict: No more than 25% of doctors...")
    response = client.post("/api/v1/doctors", json={
        "name": "Dr. Evil", "email": "evil@clinic.com", "password": "password123",
        "working_hours_start": "09:00:00", "working_hours_end": "17:00:00",
        "lunch_start": "13:00:00", "lunch_end": "13:45:00"
    })
    assert response.status_code == 400
    assert "25%" in response.json()["message"]
    