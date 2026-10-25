import uuid
from sqlalchemy import Column, String, Time
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False, index=True)
    
    # NEW: Contact Information
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False) 
    working_hours_start = Column(Time, nullable=False)
    working_hours_end = Column(Time, nullable=False)
    lunch_start = Column(Time, nullable=False)
    lunch_end = Column(Time, nullable=False)
    timezone = Column(String, default="UTC", nullable=False)