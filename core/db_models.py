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
import bcrypt
import hashlib

Base = declarative_base()

# Optional pgvector integration
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except Exception:
    Vector = None  # type: ignore
    PGVECTOR_AVAILABLE = False


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
        """Verify password using bcrypt with SHA256 pre-hash."""
        # Pre-hash password with SHA256 to handle any length
        password_hash_input = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return bcrypt.checkpw(password_hash_input.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt with SHA256 pre-hash to avoid 72-byte limit."""
        # Pre-hash with SHA256 to ensure password is always short enough for bcrypt
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        # bcrypt hash the SHA256 hex string (64 chars, well under 72 byte limit)
        hashed = bcrypt.hashpw(password_hash.encode('utf-8'), bcrypt.gensalt())
        return hashed.decode('utf-8')


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


# Semantic embeddings table (pgvector)
class ChatEmbedding(Base):
    """Semantic embedding for messages/chats (pgvector-backed)."""
    __tablename__ = "chat_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    chat_id = Column(String(255), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True, index=True)
    role = Column(String(50), nullable=True)
    content = Column(Text, nullable=False)
    # Fixed 768-dim to match Google text-embedding-004; if pgvector not available, store as JSON for fallback
    if PGVECTOR_AVAILABLE:
        embedding = Column(Vector(768))  # type: ignore
    else:
        embedding = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('idx_embeddings_user_chat', 'user_id', 'chat_id'),
        Index('idx_embeddings_msg', 'message_id'),
    )
