import uuid
from fastapi import APIRouter, Depends, status, Query, HTTPException 
from sqlalchemy import select 
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.services.clinic_service import get_all_doctors,get_all_patients, create_patient,create_doctor
from app.schemas.appointment import (
    AppointmentCreate, AppointmentResponse, CancelRequest, 
    RescheduleRequest, AvailableSlot, DoctorCreate, DoctorResponse, PatientCreate, PatientResponse
)
from app.services import appointment_service, availability_service
from app.models.appointment import Appointment

router = APIRouter()

@router.post("/appointments", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def book_appointment(appt_in: AppointmentCreate, db: AsyncSession = Depends(get_db)):
    return await appointment_service.book_appointment(db, appt_in)

@router.get("/doctors/{doctor_id}/availability", response_model=List[AvailableSlot])
async def get_availability(doctor_id: uuid.UUID, date: str, db: AsyncSession = Depends(get_db)):
    return await availability_service.get_doctor_availability(db, doctor_id, date)

@router.patch("/appointments/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(appointment_id: uuid.UUID, req: CancelRequest, db: AsyncSession = Depends(get_db)):
    return await appointment_service.cancel_appointment(db, appointment_id, req.reason)

@router.patch("/appointments/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(appointment_id: uuid.UUID, req: RescheduleRequest, db: AsyncSession = Depends(get_db)):
    return await appointment_service.reschedule_appointment(db, appointment_id, req)

@router.get("/patients/{patient_id}/appointments", response_model=List[AppointmentResponse])
async def get_patient_appointments(
    patient_id: uuid.UUID, 
    skip: int = Query(0, ge=0, description="Number of records to skip (for pagination)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db)
):
    """Fetches upcoming appointments with basic pagination to ensure performance at scale."""
    return await appointment_service.get_patient_appointments(db, patient_id, skip=skip, limit=limit)

# Additional endpoints for doctor and patient management

@router.get("/doctors", response_model=list[DoctorResponse])
async def list_doctors(db: AsyncSession = Depends(get_db)):
    """Returns all doctors in the clinic. Useful for frontend dropdowns."""
    return await get_all_doctors(db)

@router.post("/patients", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def register_patient(patient_in: PatientCreate, db: AsyncSession = Depends(get_db)):
    """Registers a new patient dynamically."""
    return await create_patient(db, patient_in)

@router.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment_details(appointment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Fetches details of a specific appointment."""
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt

@router.post("/doctors", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def register_doctor(doctor_in: DoctorCreate, db: AsyncSession = Depends(get_db)):
    """
    Registers a new doctor. Dynamically enforces the constraint that no more 
    than 25% of doctors can be on lunch break at the same time.
    """
    return await create_doctor(db, doctor_in)


@router.get("/doctors/{doctor_id}/appointments", response_model=List[AppointmentResponse])
async def get_doctor_appointments_endpoint(
    doctor_id: uuid.UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db)
):
    """Fetches upcoming appointments for a specific doctor with pagination."""
    return await appointment_service.get_doctor_appointments(db, doctor_id, skip=skip, limit=limit)

@router.get("/patients", response_model=List[PatientResponse])
async def list_patients(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db)
):
    """Returns a paginated list of all patients. Useful for admin dashboards."""
    return await get_all_patients(db, skip=skip, limit=limit)