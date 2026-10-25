import uuid
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, time
from typing import Optional
from app.models.enums import AppointmentStatus
from app.core.config import settings  


# Appointment Schemas

class AppointmentCreate(BaseModel):
    doctor_id: uuid.UUID
    patient_id: uuid.UUID
    start_time: datetime = Field(..., description="ISO 8601 format, e.g., 2024-10-25T10:00:00Z")

class AppointmentResponse(BaseModel):
    id: uuid.UUID
    doctor_id: uuid.UUID
    patient_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus
    cancellation_reason: Optional[str] = None

    class Config:
        from_attributes = True

class CancelRequest(BaseModel):
    reason: str = Field(..., min_length=5)

class RescheduleRequest(BaseModel):
    new_start_time: datetime = Field(..., description="New ISO 8601 start time")

class AvailableSlot(BaseModel):
    start_time: datetime
    end_time: datetime

# Doctor Schemas
class DoctorCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=6)
    working_hours_start: time = settings.DEFAULT_WORK_HOURS_START
    working_hours_end: time = settings.DEFAULT_WORK_HOURS_END
    lunch_start: time = time(13, 0)
    lunch_end: time = time(13, 45)
    timezone: str = "UTC"

class DoctorResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    phone: Optional[str] = None
    working_hours_start: time
    working_hours_end: time
    lunch_start: time
    lunch_end: time
    timezone: str

    class Config:
        from_attributes = True

# ==========================================
# Patient Schemas
# ==========================================
class PatientCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=6)

class PatientResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    phone: Optional[str] = None

    class Config:
        from_attributes = True