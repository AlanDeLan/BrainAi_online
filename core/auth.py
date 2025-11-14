"""
JWT-based authentication system for multi-user production.
Integrated with PostgreSQL database models.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.db_models import User as DBUser, UserSession
from core.database import get_db
from core.logger import get_logger

logger = get_logger()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Security
security = HTTPBearer(auto_error=False)  # auto_error=False allows optional auth

# JWT Settings
SECRET_KEY = os.environ.get("SECRET_KEY", "default-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7


class Token(BaseModel):
    """JWT Token response model."""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str


class TokenData(BaseModel):
    """JWT Token data model."""
    user_id: Optional[int] = None
    email: Optional[str] = None
    exp: Optional[datetime] = None


class UserAuth(BaseModel):
    """User model for authentication."""
    user_id: int
    email: str
    username: str
    is_active: bool = True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


def create_access_token(user_id: int, email: str) -> str:
    """
    Create JWT access token for user.
    
    Args:
        user_id: User ID
        email: User email
    
    Returns:
        Encoded JWT token
    """
    expires_delta = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": str(user_id),  # Subject = user_id
        "email": email,
        "exp": expire
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """
    Decode and verify JWT token.
    
    Args:
        token: JWT token to decode
    
    Returns:
        TokenData with user_id, email and expiration
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        email: str = payload.get("email")
        exp: int = payload.get("exp")
        
        if user_id_str is None or email is None:
            raise credentials_exception
        
        token_data = TokenData(
            user_id=int(user_id_str),
            email=email,
            exp=datetime.fromtimestamp(exp) if exp else None
        )
        return token_data
        
    except (JWTError, ValueError) as e:
        logger.warning(f"Token decode error: {e}")
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserAuth:
    """
    Dependency to get current authenticated user from database.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
    
    Returns:
        Current user
    
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    token_data = decode_access_token(token)
    
    # Fetch user from database
    user = db.query(DBUser).filter(DBUser.id == token_data.user_id).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return UserAuth(
        user_id=user.id,
        email=user.email,
        username=user.username,
        is_active=True
    )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    """
    Lightweight dependency to get just user_id without DB lookup.
    Use when you only need user_id for filtering.
    
    Args:
        credentials: HTTP Bearer credentials
    
    Returns:
        User ID
    
    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    token_data = decode_access_token(token)
    return token_data.user_id


async def get_current_user_id_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[int]:
    """
    Optional user_id extraction - returns None if no token provided.
    Use for backwards compatibility during migration period.
    
    Args:
        credentials: HTTP Bearer credentials (optional)
    
    Returns:
        User ID if token valid, None otherwise
    """
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        token_data = decode_access_token(token)
        return token_data.user_id
    except Exception:
        return None


def authenticate_user(db: Session, email: str, password: str) -> Optional[DBUser]:
    """
    Authenticate user by email and password.
    
    Args:
        db: Database session
        email: User email
        password: Plain text password
    
    Returns:
        User object if authenticated, None otherwise
    """
    try:
        user = db.query(DBUser).filter(DBUser.email == email).first()
        if user is None:
            logger.warning(f"User not found: {email}")
            return None
        
        if not verify_password(password, user.password_hash):
            logger.warning(f"Invalid password for user: {email}")
            return None
        
        return user
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None


def create_user_session(db: Session, user_id: int, token: str) -> UserSession:
    """
    Create user session in database.
    
    Args:
        db: Database session
        user_id: User ID
        token: JWT token
    
    Returns:
        Created UserSession object
    """
    expires_at = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    session = UserSession(
        user_id=user_id,
        session_token=token,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def invalidate_user_session(db: Session, token: str) -> bool:
    """
    Invalidate user session by token.
    
    Args:
        db: Database session
        token: JWT token to invalidate
    
    Returns:
        True if session was invalidated, False otherwise
    """
    try:
        session = db.query(UserSession).filter(
            UserSession.session_token == token
        ).first()
        
        if session:
            db.delete(session)
            db.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error invalidating session: {e}")
        return False


def init_admin_user(username: str, password: str):
    """
    Initialize admin user if doesn't exist.
    Creates admin user in database on first startup.
    
    Args:
        username: Admin username
        password: Admin password
    """
    from core.database import get_db
    
    try:
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Check if admin user exists
            existing_user = db.query(DBUser).filter(
                DBUser.username == username
            ).first()
            
            if existing_user:
                logger.info(f"Admin user '{username}' already exists")
                return
            
            # Create admin user
            admin_user = DBUser(
                email=f"{username}@brainai.local",
                username=username,
                password_hash=DBUser.hash_password(password),
                is_admin=True,
                is_active=True
            )
            
            db.add(admin_user)
            db.commit()
            logger.info(f"✅ Created admin user: {username}")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to initialize admin user: {e}", exc_info=True)
