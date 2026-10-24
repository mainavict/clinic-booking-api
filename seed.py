import asyncio
import uuid
from datetime import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.doctor import Doctor
from app.models.patient import Patient

async def seed():
    engine = create_async_engine(str(settings.DATABASE_URL))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(Doctor))
        if result.scalars().first():
            print("Database already seeded.")
            return

        doc_id = uuid.uuid4()
        pat_id = uuid.uuid4()

        doctor = Doctor(id=doc_id, name="Dr. Alice Smith", working_hours_start=time(9,0), working_hours_end=time(17,0), timezone="UTC")
        patient = Patient(id=pat_id, name="John Doe", email="john@example.com", phone="1234567890")

        session.add_all([doctor, patient])
        await session.commit()
        print(f" Seeded Doctor ID: {doc_id}")
        print(f"Seeded Patient ID: {pat_id}")

if __name__ == "__main__":
    asyncio.run(seed())