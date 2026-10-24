from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# 1. Create the async engine
# pool_pre_ping=True is highly recommended for Neon (serverless Postgres) 
# to automatically reconnect if the database drops idle connections.
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=True, # Set to True if you want to see raw SQL queries in the console
    pool_pre_ping=True, 
    pool_size=5,
    max_overflow=10
)

# 2. Create async session factory
# expire_on_commit=False is crucial for async SQLAlchemy to prevent 
# "DetachedInstanceError" when accessing model attributes after the session closes.
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False 
)

# 3. Base class for all SQLAlchemy models
class Base(DeclarativeBase):
    pass

# 4. FastAPI Dependency to get the database session
async def get_db():
    """
    Dependency that provides a database session to API endpoints.
    Automatically closes the session when the request finishes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()