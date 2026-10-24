import uuid
from sqlalchemy import Column, String, Time
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Doctor(Base):
    __tablename__ = "doctors"

    # UUID Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False, index=True)
    
    working_hours_start = Column(Time, nullable=False)
    working_hours_end = Column(Time, nullable=False)
    timezone = Column(String, default="UTC", nullable=False)