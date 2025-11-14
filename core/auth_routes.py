"""
Authentication API routes for user registration, login, and logout.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from core.database import get_db
from core.db_models import User, Archetype
from core.models import (
    RegisterRequest,
    LoginRequest,
    Token,
    UserInfo
)
from core.auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    create_user_session,
    invalidate_user_session,
    get_current_user_id,
    security
)
from core.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register new user account.
    
    - **email**: Valid email address (unique)
    - **username**: Username 3-50 chars (unique)
    - **password**: Password minimum 8 characters
    
    Returns JWT access token upon successful registration.
    """
    try:
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if username already exists
        existing_username = db.query(User).filter(User.username == request.username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create new user
        hashed_password = get_password_hash(request.password)
        new_user = User(
            email=request.email,
            username=request.username,
            password_hash=hashed_password
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create JWT token
        token = create_access_token(new_user.id, new_user.email)
        
        # Create session
        create_user_session(db, new_user.id, token)
        
        logger.info(f"New user registered: {new_user.email} (ID: {new_user.id})")
        
        return Token(
            access_token=token,
            token_type="bearer",
            user_id=new_user.id,
            email=new_user.email
        )
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already exists"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    
    - **email**: User email
    - **password**: User password
    
    Returns JWT access token upon successful authentication.
    """
    user = authenticate_user(db, request.email, request.password)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    token = create_access_token(user.id, user.email)
    
    # Create session
    create_user_session(db, user.id, token)
    
    logger.info(f"User logged in: {user.email} (ID: {user.id})")
    
    return Token(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email
    )


@router.post("/logout")
async def logout(
    user_id: int = Depends(get_current_user_id),
    credentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Logout current user by invalidating session token.
    Requires valid JWT token in Authorization header.
    """
    token = credentials.credentials
    success = invalidate_user_session(db, token)
    
    if success:
        logger.info(f"User logged out: ID {user_id}")
        return {"message": "Logged out successfully"}
    else:
        return {"message": "Session not found or already expired"}


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information.
    Requires valid JWT token in Authorization header.
    
    Returns user profile with email, username, archetypes count, etc.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Count user's archetypes
    archetypes_count = db.query(Archetype).filter(Archetype.user_id == user_id).count()
    
    return UserInfo(
        id=user.id,
        email=user.email,
        username=user.username,
        created_at=user.created_at,
        archetypes_count=archetypes_count,
        max_archetypes=2
    )
