"""
Production-ready startup script with security and monitoring.
Integrates authentication, rate limiting, and database.
"""
import os
import sys
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Import core modules
from core.logger import logger
from core.settings import settings
from core.rate_limit import RateLimitMiddleware

# Import authentication
from core.auth import init_admin_user

# Import database (only in production)
if settings.is_production:
    from core.database import init_database

# Import original app
from main import app as original_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # === STARTUP ===
    logger.info("=" * 60)
    logger.info(f"🚀 Starting BrainAi in {settings.environment.upper()} mode")
    logger.info("=" * 60)
    
    try:
        # Initialize database (production only with valid PostgreSQL URL)
        if settings.is_production and settings.database_url.startswith("postgresql"):
            logger.info("📊 Initializing PostgreSQL database...")
            init_database(settings.database_url)
            logger.info("✅ Database initialized")
        else:
            logger.info("⚠️ Skipping database initialization (not production PostgreSQL)")
        
        # Initialize admin user (only if password is not default)
        if settings.admin_password != "admin123":
            logger.info("👤 Initializing admin user...")
            init_admin_user(settings.admin_username, settings.admin_password)
            logger.info("✅ Admin user initialized")
        else:
            logger.warning("⚠️ Using default admin password - CHANGE IN PRODUCTION!")
        
        # Log configuration
        logger.info(f"🔧 Configuration:")
        logger.info(f"  - Environment: {settings.environment}")
        logger.info(f"  - Debug: {settings.debug}")
        logger.info(f"  - AI Provider: {settings.ai_provider}")
        logger.info(f"  - CORS Origins: {settings.cors_origins}")
        logger.info(f"  - Rate Limit: {settings.rate_limit_per_minute}/min, {settings.rate_limit_per_hour}/hour")
        
        logger.info("=" * 60)
        logger.info("✅ Application started successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}", exc_info=True)
        raise
    
    yield
    
    # === SHUTDOWN ===
    logger.info("=" * 60)
    logger.info("🛑 Shutting down BrainAi...")
    logger.info("=" * 60)
    logger.info("✅ Application shutdown complete")


# Create production app with lifespan
app = FastAPI(
    title="BrainAi Production",
    description="Production-ready AI assistant with security and monitoring",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,  # Disable docs in production
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan
)

# === MIDDLEWARE CONFIGURATION ===

# 1. Trusted Host (security)
if settings.is_production:
    allowed_hosts = [origin.replace("https://", "").replace("http://", "") for origin in settings.cors_origins]
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts + ["*.onrender.com"]
    )

# 2. CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit-Minute", "X-RateLimit-Remaining-Minute"]
)

# 3. Rate Limiting
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_per_minute,
    requests_per_hour=settings.rate_limit_per_hour
)

# 4. GZip Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# === IMPORT ROUTES AND STATIC FILES FROM ORIGINAL APP ===

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from core.utils import resource_path

# Mount static files
static_dir = resource_path("static")
templates_dir = resource_path("templates")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Copy all routes from original app
for route in original_app.routes:
    app.router.routes.append(route)

# === AUTHENTICATION ENDPOINTS ===

from datetime import timedelta
from fastapi import HTTPException, status
from pydantic import BaseModel
from core.auth import authenticate_user, create_access_token, get_current_user, User
from core.models import LoginRequest, TokenResponse, UserInfo


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Login endpoint - получить JWT токен.
    
    Используйте логин и пароль из Environment Variables:
    - Username: ADMIN_USERNAME
    - Password: ADMIN_PASSWORD
    """
    user = authenticate_user(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(hours=settings.jwt_expiration_hours)
    access_token = create_access_token(
        data={"sub": user.username},
        secret_key=settings.secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds())
    )


@app.get("/api/auth/me", response_model=UserInfo)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserInfo(
        username=current_user.username,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin
    )


# === SIMPLE HEALTH CHECK (for Railway) ===

from datetime import datetime


@app.get("/health")
async def health_check():
    """
    Simple health check endpoint for Railway.
    Returns 200 OK if the app is running.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat()
    }


# === ERROR HANDLERS ===

from fastapi import Request
from fastapi.responses import JSONResponse
from core.models import ErrorResponse


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            status_code=exc.status_code
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    # Don't expose internal errors in production
    if settings.is_production:
        detail = "Internal server error"
    else:
        detail = str(exc)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=detail,
            status_code=500
        ).model_dump()
    )


# === STARTUP MESSAGE ===

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main_production:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
