"""
Production-ready startup script with security and monitoring.
Integrates authentication, rate limiting, and database.
"""
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

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
            try:
                logger.info("📊 Initializing PostgreSQL database...")
                # Log database URL (masked password)
                masked_url = settings.database_url.split('@')[1] if '@' in settings.database_url else 'invalid URL'
                logger.info(f"Database host: {masked_url}")
                init_database(settings.database_url)
                logger.info("✅ Database initialized")
                
                # Initialize admin user (re-enabled with native bcrypt)
                if settings.admin_password != "admin123":
                    logger.info("👤 Initializing admin user...")
                    init_admin_user(settings.admin_username, settings.admin_password)
                    logger.info("✅ Admin user initialized")
                else:
                    logger.warning("⚠️ Using default admin password - CHANGE IN PRODUCTION!")
            except Exception as db_error:
                logger.warning(f"⚠️ Database initialization skipped: {db_error}")
                logger.info("💡 Run migration script: railway run python migrate_db.py")
        else:
            logger.info("⚠️ Skipping database initialization (not production PostgreSQL)")
        
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

# === HEALTH CHECK (must be BEFORE middleware) ===

from starlette.responses import PlainTextResponse

@app.get("/health", response_class=PlainTextResponse)
async def health_check():
    """Simple health check for Railway."""
    logger.info("Health check endpoint called")
    return "ok"

# === MIDDLEWARE CONFIGURATION ===

# 1. Trusted Host (security) - Disabled for Railway
# Railway health checks come from internal hosts, so we can't restrict by hostname
# if settings.is_production:
#     allowed_hosts = [origin.replace("https://", "").replace("http://", "") for origin in settings.cors_origins]
#     app.add_middleware(
#         TrustedHostMiddleware,
#         allowed_hosts=allowed_hosts + ["*.onrender.com"]
#     )

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
from core.utils import resource_path

# Mount static files BEFORE copying routes
static_dir = resource_path("static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Copy all routes from original app (except static mount and health check)
for route in original_app.routes:
    # Skip the static files mount from original app to avoid conflicts
    if hasattr(route, 'path') and route.path == "/static":
        continue
    # Skip health check - we have our own simple version below
    if hasattr(route, 'path') and route.path == "/health":
        continue
    app.router.routes.append(route)

# === AUTHENTICATION ENDPOINTS ===

from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.auth import authenticate_user, create_access_token, get_current_user
from core.models import LoginRequest, Token, UserInfo
from core.database import get_db


@app.post("/api/auth/login", response_model=Token)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login endpoint - получить JWT токен.
    
    Используйте логин и пароль из Environment Variables:
    - Email: ADMIN_USERNAME (or any registered email)
    - Password: ADMIN_PASSWORD
    """
    user = authenticate_user(db, request.email, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(user.id, user.email)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email
    )


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


@app.post("/api/auth/register", response_model=Token)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register new user endpoint.
    """
    from core.db_models import User
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == request.email) | (User.username == request.username)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email or username already exists"
            )
        
        # Create new user
        new_user = User(
            username=request.username,
            email=request.email,
            password_hash=User.hash_password(request.password)
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create access token
        access_token = create_access_token(new_user.id, new_user.email)
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=new_user.id,
            email=new_user.email
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


# === ERROR HANDLERS ===

from fastapi import Request
from fastapi.responses import JSONResponse
from core.models import ErrorResponse


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    logger.info(f"Request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        logger.info(f"Response: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        raise


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
