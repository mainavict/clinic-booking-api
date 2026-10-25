import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from fastapi import HTTPException
from app.core.config import settings 
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.appointment import DoctorCreate, PatientCreate

async def get_all_doctors(db: AsyncSession):
    result = await db.execute(select(Doctor).order_by(Doctor.name.asc()))
    return result.scalars().all()

async def create_doctor(db: AsyncSession, doctor_in: DoctorCreate) -> Doctor:
    count_result = await db.execute(select(func.count(Doctor.id)))
    current_doctor_count = count_result.scalar() or 0
    future_doctor_count = current_doctor_count + 1
    max_allowed_on_lunch = max(1, int(future_doctor_count * 0.25))

    query = select(Doctor).where(
        and_(
            Doctor.lunch_start < doctor_in.lunch_end,
            Doctor.lunch_end > doctor_in.lunch_start
        )
    )
    result = await db.execute(query)
    overlapping_doctors = result.scalars().all()

    if len(overlapping_doctors) >= max_allowed_on_lunch:
        raise HTTPException(
            status_code=400, 
            detail=f"Scheduling conflict: No more than 25% of doctors (max {max_allowed_on_lunch} at this time) can be on lunch break simultaneously."
        )

    new_doctor = Doctor(**doctor_in.model_dump())
    db.add(new_doctor)
    await db.commit()
    await db.refresh(new_doctor)
    return new_doctor

async def create_patient(db: AsyncSession, patient_in: PatientCreate):
    exists = await db.execute(select(Patient).where(Patient.email == patient_in.email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Patient with this email already exists.")
    
    new_patient = Patient(**patient_in.model_dump())
    db.add(new_patient)
    await db.commit()
    await db.refresh(new_patient)
    return new_patient