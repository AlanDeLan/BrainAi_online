"""
Production-ready startup script with security and monitoring.
Integrates authentication, rate limiting, and database.

TODO: Refactor to modular router structure
See REFACTORING_GUIDE.md for migration plan
Priority: MEDIUM (after test coverage reaches 80%)
"""
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Import core modules
from core.logger import logger
from core.settings import settings
from core.rate_limit import RateLimitMiddleware

# Import authentication
from core.auth import init_admin_user, get_current_user_id_optional

# Import database
from core.database import init_database

# Import original app (includes MAX_FILE_SIZE and ALLOWED_MIME_TYPES)
from main import app as original_app, MAX_FILE_SIZE, ALLOWED_MIME_TYPES


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # === STARTUP ===
    logger.info("=" * 60)
    logger.info(f"[START] Starting BrainAi in {settings.environment.upper()} mode")
    logger.info("=" * 60)
    
    try:
        # Initialize database (PostgreSQL in production, SQLite in development)
        logger.info("[DB] Initializing database...")
        
        if settings.database_url and settings.database_url.startswith("postgresql"):
            # Production: PostgreSQL
            masked_url = settings.database_url.split('@')[1] if '@' in settings.database_url else 'invalid URL'
            logger.info(f"Database: PostgreSQL at {masked_url}")
            init_database(settings.database_url)
        else:
            # Development: SQLite
            logger.info("Database: SQLite (development mode)")
            init_database("sqlite:///brainai.db")
        
        logger.info("[OK] Database initialized")
        
        # Initialize admin user (re-enabled with native bcrypt)
        logger.info("[USER] Initializing admin user...")
        init_admin_user(settings.admin_username, settings.admin_password)
        logger.info("[OK] Admin user initialized")
        
        if settings.admin_password == "admin123":
            logger.warning("[WARNING] Using default admin password - CHANGE IN PRODUCTION!")
        
        # Log configuration
        logger.info("[CONFIG] Configuration:")
        logger.info(f"  - Environment: {settings.environment}")
        logger.info(f"  - Debug: {settings.debug}")
        logger.info(f"  - AI Provider: {settings.ai_provider}")
        logger.info(f"  - CORS Origins: {settings.cors_origins}")
        logger.info(f"  - Rate Limit: {settings.rate_limit_per_minute}/min, {settings.rate_limit_per_hour}/hour")
        
        logger.info("=" * 60)
        logger.info("[OK] Application started successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"[ERROR] Failed to start application: {e}", exc_info=True)
        raise
    
    yield
    
    # === SHUTDOWN ===
    logger.info("=" * 60)
    logger.info("[STOP] Shutting down BrainAi...")
    logger.info("=" * 60)
    logger.info("[OK] Application shutdown complete")


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


@app.post("/api/auth/reset-admin")
async def reset_admin_password(db: Session = Depends(get_db)):
    """
    Reset admin user password. 
    Deletes old admin and creates new one with correct bcrypt hash.
    """
    from core.db_models import User
    
    try:
        # Delete old admin user
        old_admin = db.query(User).filter(User.email == "admin@brainai.local").first()
        if old_admin:
            db.delete(old_admin)
            db.commit()
            logger.info("Deleted old admin user")
        
        # Create new admin with native bcrypt hash
        new_admin = User(
            username="admin",
            email="admin@brainai.local",
            password_hash=User.hash_password("SecureAdmin2024!"),
            is_admin=True,
            is_active=True
        )
        
        db.add(new_admin)
        db.commit()
        logger.info("✅ Created new admin user with native bcrypt")
        
        return {"message": "Admin password reset successfully", "email": "admin@brainai.local"}
    except Exception as e:
        db.rollback()
        logger.error(f"Reset admin error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reset failed: {str(e)}"
        )


@app.get("/api/debug/vector-db")
async def debug_vector_db(db: Session = Depends(get_db)):
    """Debug endpoint to check vector DB status."""
    from vector_db.client import is_vector_db_available, get_vector_db_type, get_user_collection
    from core.db_models import User
    
    try:
        # Check vector DB availability
        vdb_available = is_vector_db_available()
        vdb_type = get_vector_db_type()
        
        # Get current user count
        user_count = db.query(User).count()
        
        # Get admin user
        admin = db.query(User).filter(User.email == "admin@brainai.local").first()
        
        debug_info = {
            "vector_db_available": vdb_available,
            "vector_db_type": vdb_type,
            "total_users": user_count,
            "admin_exists": admin is not None,
            "admin_id": admin.id if admin else None
        }
        
        # Try to get admin's collection
        if admin and vdb_available:
            try:
                collection = get_user_collection(admin.id)
                if collection:
                    count = collection.count()
                    debug_info["admin_collection_count"] = count
                else:
                    debug_info["admin_collection_count"] = "collection_not_created"
            except Exception as e:
                debug_info["admin_collection_error"] = str(e)
        
        return debug_info
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/history/db")
async def get_history_from_db(db: Session = Depends(get_db), user_id: Optional[int] = Depends(get_current_user_id_optional)):
    """
    Get chat history from PostgreSQL database (persists across deploys).
    Groups messages by chat_id.
    """
    from core.db_models import ChatMessage
    from sqlalchemy import func
    
    if user_id is None:
        return {"chats": [], "message": "Authentication required"}
    
    try:
        # Get distinct chat_ids for this user with metadata
        chats_query = db.query(
            ChatMessage.chat_id,
            func.min(ChatMessage.created_at).label('first_message'),
            func.max(ChatMessage.created_at).label('last_message'),
            func.count(ChatMessage.id).label('message_count')
        ).filter(
            ChatMessage.user_id == user_id
        ).group_by(
            ChatMessage.chat_id
        ).order_by(
            func.max(ChatMessage.created_at).desc()
        ).all()
        
        chats = []
        for chat in chats_query:
            # Get first user message for preview
            first_user_msg = db.query(ChatMessage).filter(
                ChatMessage.chat_id == chat.chat_id,
                ChatMessage.user_id == user_id,
                ChatMessage.role == 'user'
            ).order_by(ChatMessage.message_index).first()
            
            preview = first_user_msg.content[:100] if first_user_msg else "..."
            
            chats.append({
                "chat_id": chat.chat_id,
                "first_message_at": chat.first_message.isoformat(),
                "last_message_at": chat.last_message.isoformat(),
                "message_count": chat.message_count,
                "preview": preview
            })
        
        return {"chats": chats, "total": len(chats)}
    except Exception as e:
        logger.error(f"Error fetching history from DB: {e}", exc_info=True)
        return {"error": str(e), "chats": []}


@app.get("/api/history/db/{chat_id}")
async def get_chat_from_db(chat_id: str, db: Session = Depends(get_db), user_id: Optional[int] = Depends(get_current_user_id_optional)):
    """Get specific chat messages from database."""
    from core.db_models import ChatMessage
    
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        messages = db.query(ChatMessage).filter(
            ChatMessage.chat_id == chat_id,
            ChatMessage.user_id == user_id
        ).order_by(ChatMessage.message_index).all()
        
        if not messages:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        return {
            "chat_id": chat_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat(),
                    "message_index": msg.message_index
                }
                for msg in messages
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat from DB: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
