"""
JWT-based authentication system for production.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Security
security = HTTPBearer()


class Token(BaseModel):
    """JWT Token response model."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT Token data model."""
    username: Optional[str] = None
    exp: Optional[datetime] = None


class User(BaseModel):
    """User model."""
    username: str
    is_active: bool = True
    is_admin: bool = False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Data to encode in token
        secret_key: Secret key for signing
        algorithm: JWT algorithm (default: HS256)
        expires_delta: Token expiration time
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    
    return encoded_jwt


def decode_access_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256"
) -> TokenData:
    """
    Decode and verify JWT token.
    
    Args:
        token: JWT token to decode
        secret_key: Secret key for verification
        algorithm: JWT algorithm
    
    Returns:
        TokenData with username and expiration
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        username: str = payload.get("sub")
        exp: int = payload.get("exp")
        
        if username is None:
            raise credentials_exception
        
        token_data = TokenData(
            username=username,
            exp=datetime.fromtimestamp(exp) if exp else None
        )
        return token_data
        
    except JWTError:
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    secret_key: Optional[str] = None,
    algorithm: str = "HS256"
) -> User:
    """
    Dependency to get current authenticated user.
    
    Args:
        credentials: HTTP Bearer credentials
        secret_key: Secret key for JWT verification
        algorithm: JWT algorithm
    
    Returns:
        Current user
    
    Raises:
        HTTPException: If authentication fails
    """
    if not secret_key:
        from core.settings import settings
        secret_key = settings.secret_key
    
    token = credentials.credentials
    token_data = decode_access_token(token, secret_key, algorithm)
    
    # Here you would normally fetch user from database
    # For now, return a simple user object
    user = User(
        username=token_data.username,
        is_active=True,
        is_admin=True  # In production, fetch from database
    )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to require admin user.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Current user if admin
    
    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


# Simple in-memory user storage (replace with database in production)
fake_users_db = {}


def init_admin_user(username: str, password: str):
    """Initialize admin user."""
    fake_users_db[username] = {
        "username": username,
        "hashed_password": get_password_hash(password),
        "is_active": True,
        "is_admin": True
    }


def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Authenticate user by username and password.
    
    Args:
        username: Username
        password: Plain text password
    
    Returns:
        User object if authenticated, None otherwise
    """
    user_dict = fake_users_db.get(username)
    if not user_dict:
        return None
    
    if not verify_password(password, user_dict["hashed_password"]):
        return None
    
    return User(**user_dict)
