import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse,HTMLResponse
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

app.include_router(api_router, prefix=settings.API_V1_STR)

# GLOBAL EXCEPTION HANDLERS

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
    # Log the actual error for debugging
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

# HEALTH CHECK & ROOT ENDPOINTS

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

@app.get("/", tags=["System"], response_class=HTMLResponse)
async def root():
    """
    Root endpoint that renders a simple welcome page with clickable links.
    """
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Clinic Booking API</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: #f8f9fa;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                color: #333;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                text-align: center;
                max-width: 350px;
                width: 100%;
            }
            h1 {
                color: #2c3e50;
                margin-bottom: 10px;
                font-size: 22px;
            }
            p {
                color: #6c757d;
                margin-bottom: 25px;
                font-size: 14px;
            }
            .link-btn {
                display: block;
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                transition: background-color 0.2s;
                box-sizing: border-box;
            }
            .link-btn:hover {
                background-color: #0056b3;
            }
            .link-btn.success {
                background-color: #28a745;
            }
            .link-btn.success:hover {
                background-color: #218838;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/docs" class="link-btn">API Docs (Swagger)</a>
            <a href="/health" class="link-btn success">Health Check</a>
        </div>
    </body>
    </html>
    """