"""
PostgreSQL database module for production.
Replaces file-based history with database storage.
"""
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from core.logger import logger

# Import Base and models from db_models (avoid duplicate definitions)
from core.db_models import Base, ChatMessage, UserSession


class DatabaseManager:
    """Database manager for PostgreSQL operations."""
    
    def __init__(self, database_url: str):
        """
        Initialize database manager.
        
        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def init_db(self):
        """Initialize database connection and create tables."""
        try:
            # Create engine
            self.engine = create_engine(
                self.database_url,
                pool_pre_ping=True,  # Verify connections before using
                pool_size=5,
                max_overflow=10,
                echo=False  # Set to True for SQL query debugging
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            
            self._initialized = True
            logger.info("✅ Database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
            raise
    
    def get_session(self) -> Session:
        """
        Get database session.
        
        Returns:
            SQLAlchemy session
        """
        if not self._initialized:
            self.init_db()
        
        return self.SessionLocal()
    
    def save_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        archetype: Optional[str] = None,
        user_id: Optional[str] = None,
        msg_metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """
        Save chat message to database.
        
        Args:
            chat_id: Unique chat identifier
            role: Message role (user/assistant/system)
            content: Message content
            archetype: Archetype used
            user_id: User identifier
            msg_metadata: Additional metadata
        
        Returns:
            Saved ChatMessage object
        """
        session = self.get_session()
        try:
            # Get next message index for this chat
            last_message = (
                session.query(ChatMessage)
                .filter(ChatMessage.chat_id == chat_id)
                .order_by(ChatMessage.message_index.desc())
                .first()
            )
            next_index = (last_message.message_index + 1) if last_message else 0
            
            # Create message
            message = ChatMessage(
                chat_id=chat_id,
                user_id=user_id,
                message_index=next_index,
                role=role,
                content=content,
                archetype=archetype,
                msg_metadata=msg_metadata
            )
            
            session.add(message)
            session.commit()
            session.refresh(message)
            
            logger.debug(f"Saved message to DB: chat_id={chat_id}, role={role}")
            return message
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving message: {e}", exc_info=True)
            raise
        finally:
            session.close()
    
    def get_chat_history(
        self,
        chat_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get chat history from database.
        
        Args:
            chat_id: Unique chat identifier
            limit: Maximum number of messages to return
        
        Returns:
            List of message dictionaries
        """
        session = self.get_session()
        try:
            query = (
                session.query(ChatMessage)
                .filter(ChatMessage.chat_id == chat_id)
                .order_by(ChatMessage.message_index.asc())
            )
            
            if limit:
                query = query.limit(limit)
            
            messages = query.all()
            
            return [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "archetype": msg.archetype,
                    "metadata": msg.msg_metadata,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                }
                for msg in messages
            ]
            
        except Exception as e:
            logger.error(f"Error getting chat history: {e}", exc_info=True)
            return []
        finally:
            session.close()
    
    def search_chats(
        self,
        query: Optional[str] = None,
        archetype: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[str]:
        """
        Search for chats.
        
        Args:
            query: Text search query
            archetype: Filter by archetype
            user_id: Filter by user
            limit: Maximum results
        
        Returns:
            List of unique chat IDs
        """
        session = self.get_session()
        try:
            q = session.query(ChatMessage.chat_id).distinct()
            
            if query:
                q = q.filter(ChatMessage.content.ilike(f"%{query}%"))
            
            if archetype:
                q = q.filter(ChatMessage.archetype == archetype)
            
            if user_id:
                q = q.filter(ChatMessage.user_id == user_id)
            
            q = q.order_by(ChatMessage.created_at.desc()).limit(limit)
            
            results = q.all()
            return [row[0] for row in results]
            
        except Exception as e:
            logger.error(f"Error searching chats: {e}", exc_info=True)
            return []
        finally:
            session.close()
    
    def delete_chat(self, chat_id: str) -> bool:
        """
        Delete all messages for a chat.
        
        Args:
            chat_id: Chat identifier
        
        Returns:
            True if successful
        """
        session = self.get_session()
        try:
            session.query(ChatMessage).filter(
                ChatMessage.chat_id == chat_id
            ).delete()
            session.commit()
            logger.info(f"Deleted chat: {chat_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting chat: {e}", exc_info=True)
            return False
        finally:
            session.close()


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


def init_database(database_url: str):
    """
    Initialize global database manager.
    
    Args:
        database_url: PostgreSQL connection URL
    """
    global db_manager
    db_manager = DatabaseManager(database_url)
    db_manager.init_db()


def get_db():
    """
    FastAPI dependency to get database session.
    
    Yields:
        SQLAlchemy session
    """
    if db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()
