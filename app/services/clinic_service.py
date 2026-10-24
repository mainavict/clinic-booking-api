import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.appointment import DoctorCreate, PatientCreate

async def get_all_doctors(db: AsyncSession):
    result = await db.execute(select(Doctor).order_by(Doctor.name.asc()))
    return result.scalars().all()

async def create_patient(db: AsyncSession, patient_in: PatientCreate):
    # Check if email already exists
    exists = await db.execute(select(Patient).where(Patient.email == patient_in.email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Patient with this email already exists.")
    
    new_patient = Patient(**patient_in.model_dump())
    db.add(new_patient)
    await db.commit()
    await db.refresh(new_patient)
    return new_patient