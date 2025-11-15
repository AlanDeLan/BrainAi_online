from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from core.db_models import ChatMessage, ChatEmbedding
from core.embeddings import embed_text, EMBED_DIM
from core.logger import logger


def is_pgvector_enabled(session: Session) -> bool:
    try:
        # Quick check: ensure chat_embeddings table exists and has embedding column
        session.execute(text("SELECT 1 FROM chat_embeddings LIMIT 1"))
        return True
    except Exception as e:
        logger.debug(f"pgvector not enabled or table missing: {e}")
        return False

message_roles_to_index = {"assistant", "file"}


def index_message(session: Session, msg: ChatMessage) -> bool:
    """Compute and store embedding for a single message if role eligible."""
    if msg.role not in message_roles_to_index:
        return False
    vec = embed_text(msg.content)
    if not vec or len(vec) != EMBED_DIM:
        return False
    try:
        # Remove existing embedding for this message to avoid duplicates
        if msg.id:
            try:
                session.query(ChatEmbedding).filter(ChatEmbedding.message_id == msg.id).delete()
                session.flush()
            except Exception:
                session.rollback()
        emb = ChatEmbedding(
            user_id=msg.user_id,
            chat_id=msg.chat_id,
            message_id=msg.id,
            role=msg.role,
            content=msg.content,
            embedding=vec,
        )
        session.add(emb)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger.debug(f"Embedding index error: {e}")
        return False


def index_latest_assistant(session: Session, user_id: int, chat_id: str) -> bool:
    try:
        msg = (
            session.query(ChatMessage)
            .filter(ChatMessage.user_id == user_id, ChatMessage.chat_id == chat_id, ChatMessage.role == "assistant")
            .order_by(ChatMessage.message_index.desc())
            .first()
        )
        if not msg:
            return False
        return index_message(session, msg)
    except Exception as e:
        logger.debug(f"Index latest assistant error: {e}")
        return False


def search_semantic(session: Session, user_id: int, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """Semantic search over embeddings; returns list with chat_id, text, timestamp, relevance."""
    vec = embed_text(query)
    if not vec or len(vec) != EMBED_DIM:
        return []
    try:
        # Use SQL with vector cosine distance
        sql = text(
            """
            SELECT chat_id,
                   content,
                   created_at,
                   1 - (embedding <=> :query_vec) AS relevance
            FROM chat_embeddings
            WHERE user_id = :user_id
            ORDER BY embedding <=> :query_vec
            LIMIT :k
            """
        )
        rows = session.execute(sql, {"user_id": user_id, "query_vec": vec, "k": int(n_results)}).fetchall()
        results = []
        for r in rows:
            results.append({
                "chat_id": r[0],
                "text": r[1],
                "timestamp": r[2].isoformat() if r[2] else None,
                "relevance": float(r[3])
            })
        return results
    except Exception as e:
        logger.debug(f"Semantic search error: {e}")
        return []
