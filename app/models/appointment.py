import uuid
from sqlalchemy import Column, DateTime, Enum, String, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from app.models.enums import AppointmentStatus

class Appointment(Base):
    __tablename__ = "appointments"
    
    __table_args__ = (
        UniqueConstraint('doctor_id', 'start_time', name='uix_doctor_start_time'),
    )

    # UUID Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # UUID Foreign Keys
    doctor_id = Column(UUID(as_uuid=True), ForeignKey('doctors.id'), index=True, nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.id'), index=True, nullable=False)
    
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False)
    cancellation_reason = Column(String, nullable=True)