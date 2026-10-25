import asyncio
import uuid
from datetime import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.core.security import get_password_hash

async def seed():
    engine = create_async_engine(str(settings.DATABASE_URL))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(Doctor))
        if result.scalars().first():
            print("⚠️ Database already seeded. Skipping to prevent duplicates.")
            return

        # Common password for all seeded users
        hashed_pw = get_password_hash("password123")

        # ==========================================
        # 5 DOCTORS (Staggered lunch breaks to satisfy the 25% rule)
        # ==========================================
        doctors_data = [
            {"name": "Dr. Alice Smith", "email": "alice@clinic.com", "phone": "555-0101", "lunch_start": time(10, 0), "lunch_end": time(10, 45)},
            {"name": "Dr. Bob Jones", "email": "bob@clinic.com", "phone": "555-0102", "lunch_start": time(11, 0), "lunch_end": time(11, 45)},
            {"name": "Dr. Charlie Davis", "email": "charlie@clinic.com", "phone": "555-0103", "lunch_start": time(12, 0), "lunch_end": time(12, 45)},
            {"name": "Dr. Diana Prince", "email": "diana@clinic.com", "phone": "555-0104", "lunch_start": time(13, 0), "lunch_end": time(13, 45)},
            {"name": "Dr. Evan Wright", "email": "evan@clinic.com", "phone": "555-0105", "lunch_start": time(14, 0), "lunch_end": time(14, 45)},
        ]

        doctor_ids = []
        for doc in doctors_data:
            doc_id = uuid.uuid4()
            doctor_ids.append(doc_id)
            session.add(Doctor(
                id=doc_id,
                name=doc["name"],
                email=doc["email"],
                phone=doc["phone"],
                hashed_password=hashed_pw,
                working_hours_start=time(9, 0),
                working_hours_end=time(17, 0),
                lunch_start=doc["lunch_start"],
                lunch_end=doc["lunch_end"],
                timezone="UTC"
            ))

        # ==========================================
        # 20 PATIENTS
        # ==========================================
        patients_data = [
            {"name": "John Doe", "email": "john.doe@email.com"},
            {"name": "Jane Smith", "email": "jane.smith@email.com"},
            {"name": "Michael Johnson", "email": "michael.j@email.com"},
            {"name": "Emily Davis", "email": "emily.d@email.com"},
            {"name": "David Wilson", "email": "david.w@email.com"},
            {"name": "Sarah Brown", "email": "sarah.b@email.com"},
            {"name": "James Taylor", "email": "james.t@email.com"},
            {"name": "Olivia Anderson", "email": "olivia.a@email.com"},
            {"name": "Robert Thomas", "email": "robert.t@email.com"},
            {"name": "Sophia Jackson", "email": "sophia.j@email.com"},
            {"name": "William White", "email": "william.w@email.com"},
            {"name": "Isabella Harris", "email": "isabella.h@email.com"},
            {"name": "Richard Martin", "email": "richard.m@email.com"},
            {"name": "Mia Thompson", "email": "mia.t@email.com"},
            {"name": "Joseph Garcia", "email": "joseph.g@email.com"},
            {"name": "Charlotte Martinez", "email": "charlotte.m@email.com"},
            {"name": "Thomas Robinson", "email": "thomas.r@email.com"},
            {"name": "Amelia Clark", "email": "amelia.c@email.com"},
            {"name": "Charles Rodriguez", "email": "charles.r@email.com"},
            {"name": "Harper Lewis", "email": "harper.l@email.com"},
        ]

        patient_ids = []
        for i, pat in enumerate(patients_data):
            pat_id = uuid.uuid4()
            patient_ids.append(pat_id)
            session.add(Patient(
                id=pat_id,
                name=pat["name"],
                email=pat["email"],
                phone=f"555-{1000 + i}",
                hashed_password=hashed_pw
            ))

        await session.commit()

        # Print IDs for easy copy-pasting into Swagger UI
        print("\n" + "="*50)
        print("✅ SEEDING COMPLETE! COPY THESE UUIDs FOR SWAGGER UI:")
        print("="*50)
        for i, doc in enumerate(doctors_data):
            print(f"Doctor {i+1} ({doc['name']}): {doctor_ids[i]}")
        print("-" * 50)
        print(f"Patient 1 (John Doe): {patient_ids[0]}")
        print(f"Patient 2 (Jane Smith): {patient_ids[1]}")
        print(f"Patient 3 (Michael Johnson): {patient_ids[2]}")
        print(f"Patient 4 (Emily Davis): {patient_ids[3]}")
        print(f"Patient 5 (David Wilson): {patient_ids[4]}")
        print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(seed())