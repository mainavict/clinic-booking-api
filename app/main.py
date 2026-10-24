import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import engine, Base
from app.models import * 
from app.api.v1.endpoints import router as api_router

# ==========================================
# SENTRY INITIALIZATION (Must be before FastAPI app)
# ==========================================
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        traces_sample_rate=1.0, # Captures 100% of transactions (lower this in real prod)
        profiles_sample_rate=1.0,
    )
    print("✅ Sentry initialized for error tracking.")
else:
    print("⚠️ SENTRY_DSN not found in .env. Error tracking is disabled.")

# ==========================================
# APP LIFESPAN & INITIALIZATION
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables verified")
    yield
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    description="Production-ready Clinic Booking API with async PostgreSQL and Sentry monitoring"
)

# Include the API router with the /api/v1 prefix
app.include_router(api_router, prefix=settings.API_V1_STR)

# ==========================================
# GLOBAL EXCEPTION HANDLERS
# ==========================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles Pydantic validation errors with clean, structured responses.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Failed",
            "message": "Request data validation failed",
            "details": exc.errors()
        },
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handles HTTP exceptions (like 404, 400, 409) with consistent formatting.This  is  mainly  for the    front end   error you  do not want to expose raw error messages to the client. Instead, we provide a structured response with the status code and a user-friendly message.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP {exc.status_code}",
            "message": exc.detail
        },
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    Handles database errors gracefully without exposing internal details.
    """
    # Log the actual error for debugging (in production, use a logging service)
    print(f"DATABASE ERROR: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Database Error",
            "message": "An error occurred while accessing the database. Please try again."
        },
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catches all unhandled exceptions to prevent raw stack traces from being exposed.
    """
    # Log the error for debugging 
    print(f"UNHANDLED ERROR: {type(exc).__name__}: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later."
        },
    )

# ==========================================
# HEALTH CHECK & ROOT ENDPOINTS
# ==========================================

@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    """
    return {
        "status": "healthy",
        "message": "Clinic Booking API is running",
        "version": "1.0.0"
    }

@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "Welcome to the Clinic Booking API",
        "For   documentation": "/docs",
        "health": "/health"
    }