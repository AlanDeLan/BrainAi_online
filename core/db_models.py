"""
Enhanced database models for multi-user system.
Includes User, Archetype models with constraints.
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, Boolean, 
    JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from passlib.context import CryptContext

Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    archetypes = relationship("Archetype", back_populates="owner", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    
    def verify_password(self, password: str) -> bool:
        """Verify password."""
        return pwd_context.verify(password, self.password_hash)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password. Truncate to 72 bytes for bcrypt compatibility."""
        # Bcrypt has 72 byte limit
        password_bytes = password.encode('utf-8')[:72]
        return pwd_context.hash(password_bytes.decode('utf-8', errors='ignore'))


class Archetype(Base):
    """Archetype model with user ownership and sharing."""
    __tablename__ = "archetypes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    system_prompt = Column(Text, nullable=False)
    model_name = Column(String(100), default="gemini-1.5-flash")
    temperature = Column(Integer, default=0.7)  # Stored as int * 100
    max_tokens = Column(Integer, default=2048)
    is_public = Column(Boolean, default=False, index=True)  # For sharing
    uses_count = Column(Integer, default=0)  # Track popularity
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="archetypes")
    chat_messages = relationship("ChatMessage", back_populates="archetype")
    
    # Constraints
    __table_args__ = (
        # Each user can have max 2 archetypes
        Index('idx_user_archetypes', 'user_id'),
        # Unique archetype name per user
        UniqueConstraint('user_id', 'name', name='uq_user_archetype_name'),
    )


class ChatMessage(Base):
    """Chat message model with user and archetype relationships."""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String(255), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    archetype_id = Column(Integer, ForeignKey("archetypes.id"), nullable=True)
    message_index = Column(Integer, nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    msg_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata' (reserved)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="chat_messages")
    archetype = relationship("Archetype", back_populates="chat_messages")
    
    # Indexes for fast queries
    __table_args__ = (
        Index('idx_user_chat', 'user_id', 'chat_id'),
        Index('idx_user_created', 'user_id', 'created_at'),
    )


class UserSession(Base):
    """User session model for tracking active sessions."""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
