import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta, time
import pytz
from fastapi import HTTPException

from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.enums import AppointmentStatus
from app.schemas.appointment import AppointmentCreate, RescheduleRequest

async def get_doctor(db: AsyncSession, doctor_id: uuid.UUID) -> Doctor:
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor

async def book_appointment(db: AsyncSession, appt_in: AppointmentCreate) -> Appointment:
    now = datetime.now(pytz.utc)
    
    if appt_in.start_time < now + timedelta(hours=1):
        raise HTTPException(status_code=400, detail="Appointments must be booked at least 1 hour in advance.")
    
    if appt_in.start_time < now:
        raise HTTPException(status_code=400, detail="Cannot book appointments in the past.")

    end_time = appt_in.start_time + timedelta(minutes=30)
    doctor = await get_doctor(db, appt_in.doctor_id)
    
    work_start = datetime.combine(appt_in.start_time.date(), doctor.working_hours_start, tzinfo=pytz.utc)
    work_end = datetime.combine(appt_in.start_time.date(), doctor.working_hours_end, tzinfo=pytz.utc)

    if appt_in.start_time < work_start or end_time > work_end:
        raise HTTPException(status_code=400, detail="Requested time is outside doctor's working hours.")

    query = select(Appointment).where(
        and_(
            Appointment.doctor_id == appt_in.doctor_id,
            Appointment.status == AppointmentStatus.BOOKED,
            or_(and_(Appointment.start_time < end_time, Appointment.end_time > appt_in.start_time))
        )
    ).with_for_update()
    
    result = await db.execute(query)
    if result.scalars().all():
        raise HTTPException(status_code=409, detail="This slot is already booked.")

    new_appt = Appointment(
        doctor_id=appt_in.doctor_id,
        patient_id=appt_in.patient_id,
        start_time=appt_in.start_time,
        end_time=end_time,
        status=AppointmentStatus.BOOKED
    )
    db.add(new_appt)
    await db.commit()
    await db.refresh(new_appt)
    return new_appt

async def cancel_appointment(db: AsyncSession, appointment_id: uuid.UUID, reason: str) -> Appointment:
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id).with_for_update())
    appt = result.scalar_one_or_none()
    
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.status == AppointmentStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Appointment is already cancelled")

    appt.status = AppointmentStatus.CANCELLED
    appt.cancellation_reason = reason
    await db.commit()
    await db.refresh(appt)
    return appt

async def reschedule_appointment(db: AsyncSession, appointment_id: uuid.UUID, req: RescheduleRequest) -> Appointment:
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id).with_for_update())
    appt = result.scalar_one_or_none()
    
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.status == AppointmentStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot reschedule a cancelled appointment")

    new_end_time = req.new_start_time + timedelta(minutes=30)
    now = datetime.now(pytz.utc)

    if req.new_start_time < now + timedelta(hours=1):
        raise HTTPException(status_code=400, detail="New slot must be at least 1 hour in advance.")

    query = select(Appointment).where(
        and_(
            Appointment.doctor_id == appt.doctor_id,
            Appointment.id != appointment_id,
            Appointment.status == AppointmentStatus.BOOKED,
            or_(and_(Appointment.start_time < new_end_time, Appointment.end_time > req.new_start_time))
        )
    ).with_for_update()
    
    if (await db.execute(query)).scalars().all():
        raise HTTPException(status_code=409, detail="New requested slot is already booked.")

    appt.start_time = req.new_start_time
    appt.end_time = new_end_time
    appt.status = AppointmentStatus.RESCHEDULED
    
    await db.commit()
    await db.refresh(appt)
    return appt

async def get_patient_appointments(db: AsyncSession, patient_id: uuid.UUID):
    now = datetime.now(pytz.utc)
    query = select(Appointment).where(
        and_(
            Appointment.patient_id == patient_id,
            Appointment.start_time >= now,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED])
        )
    ).order_by(Appointment.start_time.asc())
    
    result = await db.execute(query)
    return result.scalars().all()