import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta, time
import pytz
from fastapi import HTTPException
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.enums import AppointmentStatus
from app.schemas.appointment import AvailableSlot

async def get_doctor_availability(db: AsyncSession, doctor_id: uuid.UUID, date: str):
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    start_of_day = datetime.combine(target_date, time.min, tzinfo=pytz.utc)
    end_of_day = datetime.combine(target_date, time.max, tzinfo=pytz.utc)
    
    booked_query = select(Appointment).where(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.start_time >= start_of_day,
            Appointment.start_time <= end_of_day
        )
    )
    booked_appts = (await db.execute(booked_query)).scalars().all()

    work_start = datetime.combine(target_date, doctor.working_hours_start, tzinfo=pytz.utc)
    work_end = datetime.combine(target_date, doctor.working_hours_end, tzinfo=pytz.utc)
    
    available_slots = []
    current_time = work_start
    now = datetime.now(pytz.utc)
    buffer_time = now + timedelta(hours=1)

    while current_time + timedelta(minutes=30) <= work_end:
        slot_end = current_time + timedelta(minutes=30)
        
        if current_time < buffer_time:
            current_time += timedelta(minutes=30)
            continue

        is_booked = any(
            (appt.start_time < slot_end and appt.end_time > current_time)
            for appt in booked_appts
        )
        
        if not is_booked:
            available_slots.append(AvailableSlot(start_time=current_time, end_time=slot_end))
            
        current_time += timedelta(minutes=30)

    return available_slots