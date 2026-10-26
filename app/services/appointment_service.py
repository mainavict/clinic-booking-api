import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta, time, timezone  # <-- Added timezone, removed pytz
from fastapi import HTTPException

from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.enums import AppointmentStatus
from app.schemas.appointment import AppointmentCreate, RescheduleRequest
from app.core.config import settings


async def get_doctor(db: AsyncSession, doctor_id: uuid.UUID) -> Doctor:
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


async def get_doctor_appointments(db: AsyncSession, doctor_id: uuid.UUID, skip: int = 0, limit: int = 20):
    now = datetime.now(timezone.utc)  # <-- Changed to timezone.utc
    query = select(Appointment).where(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.start_time >= now,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED])
        )
    ).order_by(Appointment.start_time.asc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


async def book_appointment(db: AsyncSession, appt_in: AppointmentCreate) -> Appointment:
    now = datetime.now(timezone.utc)  # <-- Changed to timezone.utc
    end_time = appt_in.start_time + timedelta(minutes=30)
    
    # 1. Fetch doctor once
    doctor = await get_doctor(db, appt_in.doctor_id)
    
    # 2. Check Working Hours (using timezone.utc to ensure they are offset-aware)
    work_start = datetime.combine(appt_in.start_time.date(), doctor.working_hours_start, tzinfo=timezone.utc)
    work_end = datetime.combine(appt_in.start_time.date(), doctor.working_hours_end, tzinfo=timezone.utc)

    if appt_in.start_time < work_start or end_time > work_end:
        raise HTTPException(status_code=400, detail="Requested time is outside doctor's working hours.")

    # 3. Check Lunch Break (also using timezone.utc)
    lunch_start_dt = datetime.combine(appt_in.start_time.date(), doctor.lunch_start, tzinfo=timezone.utc)
    lunch_end_dt = datetime.combine(appt_in.start_time.date(), doctor.lunch_end, tzinfo=timezone.utc)

    if (lunch_start_dt < end_time) and (lunch_end_dt > appt_in.start_time):
        raise HTTPException(
            status_code=400, 
            detail="The requested time falls during the doctor's scheduled lunch break. Please select a different time slot."
        )

    # 4. Check Time Constraints
    if appt_in.start_time < now:
        raise HTTPException(status_code=400, detail="Cannot book appointments in the past.")
        
    if appt_in.start_time < now + timedelta(hours=settings.MIN_HOURS_IN_ADVANCE):
        raise HTTPException(
            status_code=400, 
            detail=f"Appointments must be booked at least {settings.MIN_HOURS_IN_ADVANCE} hour(s) in advance."
        )
        
    if appt_in.start_time > now + timedelta(days=settings.MAX_DAYS_IN_ADVANCE):
        raise HTTPException(
            status_code=400, 
            detail=f"Appointments cannot be booked more than {settings.MAX_DAYS_IN_ADVANCE} days in advance."
        )

    # 5. Check for Double Bookings (Concurrency safe with pessimistic locking)
        # 5. Check for Double Bookings (Concurrency safe with pessimistic locking)
    query = select(Appointment).where(
        and_(
            Appointment.doctor_id == appt_in.doctor_id,
            # FIX: Block the slot if it is BOOKED *or* RESCHEDULED. 
            # Only CANCELLED slots will pass this check and be available.
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED]),
            Appointment.start_time < end_time, 
            Appointment.end_time > appt_in.start_time
        )
    ).with_for_update()
    
    result = await db.execute(query)
    if result.scalars().all():
        raise HTTPException(status_code=409, detail="This slot is already booked.")

    # 6. Create and Save
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
    now = datetime.now(timezone.utc)  # <-- Changed to timezone.utc

    # UPDATED: Uses the configurable setting instead of hardcoded 1
    if req.new_start_time < now + timedelta(hours=settings.MIN_HOURS_IN_ADVANCE):
        raise HTTPException(
            status_code=400, 
            detail=f"New slot must be at least {settings.MIN_HOURS_IN_ADVANCE} hour(s) in advance."
        )

    # Simplified overlap logic (removed redundant or_(and_(...)))
    query = select(Appointment).where(
        and_(
            Appointment.doctor_id == appt.doctor_id,
            Appointment.id != appointment_id,
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.start_time < new_end_time,
            Appointment.end_time > req.new_start_time
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


async def get_patient_appointments(db: AsyncSession, patient_id: uuid.UUID, skip: int = 0, limit: int = 20):
    """Fetches upcoming appointments with pagination to prevent memory exhaustion at scale."""
    now = datetime.now(timezone.utc)  # <-- Changed to timezone.utc
    
    query = select(Appointment).where(
        and_(
            Appointment.patient_id == patient_id,
            Appointment.start_time >= now,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED])
        )
    ).order_by(Appointment.start_time.asc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()