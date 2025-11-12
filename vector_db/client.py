import os
import sys
from core.utils import get_base_dir

# Lazy import logger to avoid circular imports
def get_logger():
    """Get logger instance (lazy import)."""
    try:
        from core.logger import logger
        return logger
    except ImportError:
        # Fallback if logger is not available
        import logging
        return logging.getLogger("local_brain")

# Lazy import chromadb to handle PyInstaller issues with Rust components
_chromadb = None
_Settings = None

def _import_chromadb():
    """Lazy import chromadb to avoid issues with PyInstaller."""
    global _chromadb, _Settings
    if _chromadb is None:
        try:
            import chromadb
            from chromadb.config import Settings
            _chromadb = chromadb
            _Settings = Settings
        except (ImportError, ModuleNotFoundError) as e:
            # ChromaDB may not be available in PyInstaller due to Rust components
            raise ImportError(f"ChromaDB not available: {e}")
    return _chromadb, _Settings

# Ініціалізація клієнта векторної бази даних
# Спочатку пробуємо ChromaDB, якщо не працює - використовуємо FAISS
client = None
collection = None
faiss_db = None
vector_db_available = False
use_faiss = False

# Export function to check if vector DB is available
def is_vector_db_available():
    """Check if vector database is available."""
    return vector_db_available

# Export function to check which vector DB is being used
def get_vector_db_type():
    """Get the type of vector database being used."""
    if not vector_db_available:
        return None
    return "FAISS" if use_faiss else "ChromaDB"

# Try ChromaDB first
try:
    logger = get_logger()
    chromadb, Settings = _import_chromadb()
    vector_db_dir = os.path.join(get_base_dir(), "vector_db_storage")
    os.makedirs(vector_db_dir, exist_ok=True)
    
    # Try to use PersistentClient first (more reliable with PyInstaller)
    try:
        client = chromadb.PersistentClient(path=vector_db_dir)
    except (Exception, ModuleNotFoundError, ImportError) as e:
        # Fallback to Client with Settings
        try:
            client = chromadb.Client(Settings(persist_directory=vector_db_dir))
        except (Exception, ModuleNotFoundError, ImportError) as e2:
            # If both fail, raise the original error
            raise e
    
    # Колекція для збереження чатів
    collection = client.get_or_create_collection("chat_memory")
    vector_db_available = True
    use_faiss = False
    logger.info(f"ChromaDB initialized at {vector_db_dir}")
except (ImportError, ModuleNotFoundError, Exception) as e:
    logger = get_logger()
    error_msg = str(e)
    # Check if it's the Rust module error
    if "chromadb.api.rust" in error_msg or "No module named" in error_msg:
        logger.warning("ChromaDB Rust components not available, trying FAISS as fallback...")
    else:
        logger.warning(f"ChromaDB not available: {error_msg}, trying FAISS as fallback...")
    
    # Try FAISS as fallback
    try:
        from vector_db.faiss_client import FAISSVectorDB
        vector_db_dir = os.path.join(get_base_dir(), "vector_db_storage")
        faiss_db = FAISSVectorDB(storage_dir=vector_db_dir)
        vector_db_available = True
        use_faiss = True
        logger.info(f"FAISS vector database initialized at {vector_db_dir}")
    except Exception as faiss_error:
        logger.error(f"FAISS also failed: {faiss_error}", exc_info=True)
        logger.warning("Vector database features will be disabled. Chat history will still be saved to files.")
        client = None
        collection = None
        faiss_db = None
        vector_db_available = False
        use_faiss = False

def save_chat(chat_id, chat_text, archetypes, timestamp, topic=None):
    """
    Зберігає чат як один документ у векторній базі.
    archetypes: список архетипів (list) -> треба перетворити на str!
    """
    logger = get_logger()
    if not vector_db_available:
        logger.debug("Vector database not available, skipping save")
        return
    
    try:
        metadata = {
            "chat_id": chat_id,
            "archetypes": ", ".join(archetypes) if isinstance(archetypes, list) else str(archetypes),
            "timestamp": timestamp,
            "topic": topic or ""
        }
        
        if use_faiss and faiss_db:
            # Use FAISS
            faiss_db.add(
                ids=[str(chat_id)],
                documents=[chat_text],
                metadatas=[metadata]
            )
        elif collection:
            # Use ChromaDB
            collection.add(
                documents=[chat_text],
                metadatas=[metadata],
                ids=[str(chat_id)]
            )
        else:
            logger.debug("No vector database collection available")
            return
        
        logger.debug(f"Chat saved to vector database: {chat_id}")
    except Exception as e:
        logger.error(f"Failed to save chat to vector database: {e}", exc_info=True)
        # Don't raise - allow app to continue

def save_message(chat_id, message_id, message_text, role, archetype=None, timestamp=None):
    """
    Зберігає окреме повідомлення у векторній базі.
    
    Args:
        chat_id: ID чату
        message_id: Унікальний ID повідомлення (наприклад, "{chat_id}_msg_{index}")
        message_text: Текст повідомлення
        role: Роль повідомлення ("user" або "assistant")
        archetype: Архетип (опціонально)
        timestamp: Часова мітка (опціонально)
    """
    logger = get_logger()
    if not vector_db_available:
        logger.debug("Vector database not available, skipping save")
        return
    
    try:
        if timestamp is None:
            import datetime
            timestamp = datetime.datetime.now().isoformat()
        
        metadata = {
            "chat_id": str(chat_id),
            "message_id": str(message_id),
            "role": role,
            "timestamp": timestamp
        }
        
        if archetype:
            metadata["archetype"] = archetype
        
        if use_faiss and faiss_db:
            # Use FAISS
            faiss_db.add(
                ids=[str(message_id)],
                documents=[message_text],
                metadatas=[metadata]
            )
        elif collection:
            # Use ChromaDB
            collection.add(
                documents=[message_text],
                metadatas=[metadata],
                ids=[str(message_id)]
            )
        else:
            logger.debug("No vector database collection available")
            return
        
        logger.debug(f"Message saved to vector database: {message_id} (chat: {chat_id})")
    except Exception as e:
        logger.error(f"Failed to save message to vector database: {e}", exc_info=True)
        # Don't raise - allow app to continue

def search_chat_messages(chat_id, query, n_results=5):
    """
    Пошук релевантних повідомлень в конкретному чаті.
    
    Args:
        chat_id: ID чату для пошуку
        query: Текст для пошуку (str)
        n_results: Кількість результатів (int)
    
    Returns:
        List of message dictionaries with text, role, score, etc.
    """
    logger = get_logger()
    if not vector_db_available:
        logger.debug("Vector database not available, returning empty results")
        return []
    
    try:
        if use_faiss and faiss_db:
            # Use FAISS with filter
            results = faiss_db.query(
                query_texts=[query],
                n_results=n_results,
                where={"chat_id": str(chat_id)}
            )
        elif collection:
            # Use ChromaDB with where filter
            # Try with where filter first, fallback to filtering results if not supported
            try:
                results = collection.query(
                    query_texts=[query],
                    n_results=n_results * 3,  # Get more results to filter
                    where={"chat_id": str(chat_id)}
                )
            except (TypeError, ValueError, Exception) as e:
                # If where filter is not supported, query all and filter manually
                logger.debug(f"ChromaDB where filter not supported, filtering manually: {e}")
                results = collection.query(
                    query_texts=[query],
                    n_results=n_results * 5  # Get more results to compensate for filtering
                )
        else:
            return []
        
        messages = []
        if results.get("ids") and len(results["ids"]) > 0 and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i]
                # Filter by chat_id if not already filtered by ChromaDB
                if metadata.get("chat_id") != str(chat_id):
                    continue
                
                messages.append({
                    "message_id": metadata.get("message_id"),
                    "chat_id": metadata.get("chat_id"),
                    "role": metadata.get("role"),
                    "text": results["documents"][0][i],
                    "score": results["distances"][0][i],
                    "timestamp": metadata.get("timestamp"),
                    "archetype": metadata.get("archetype")
                })
                
                # Stop when we have enough results
                if len(messages) >= n_results:
                    break
        
        logger.debug(f"Found {len(messages)} messages in chat {chat_id} for query: {query[:50]}")
        return messages
    except Exception as e:
        logger.error(f"Failed to search messages in vector database: {e}", exc_info=True)
        return []

def search_chats(query, n_results=3):
    """
    Пошук релевантних чатів для контексту.
    query: текст для пошуку (str)
    n_results: кількість результатів (int)
    """
    logger = get_logger()
    if not vector_db_available:
        logger.debug("Vector database not available, returning empty results")
        return []
    
    try:
        if use_faiss and faiss_db:
            # Use FAISS
            results = faiss_db.query(query_texts=[query], n_results=n_results)
        elif collection:
            # Use ChromaDB
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )
        else:
            return []
        
        chats = []
        if results.get("ids") and len(results["ids"]) > 0 and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                chats.append({
                    "chat_id": results["metadatas"][0][i].get("chat_id"),
                    "archetypes": results["metadatas"][0][i].get("archetypes"),
                    "timestamp": results["metadatas"][0][i].get("timestamp"),
                    "topic": results["metadatas"][0][i].get("topic"),
                    "text": results["documents"][0][i],
                    "score": results["distances"][0][i]
                })
        logger.debug(f"Found {len(chats)} chats for query: {query[:50]}")
        return chats
    except Exception as e:
        logger.error(f"Failed to search chats in vector database: {e}", exc_info=True)
        return []

def delete_chat(chat_id):
    """Видаляє чат з векторної бази за chat_id."""
    logger = get_logger()
    if not vector_db_available:
        logger.debug("Vector database not available, skipping delete")
        return
    
    try:
        if use_faiss and faiss_db:
            # Use FAISS
            faiss_db.delete(ids=[str(chat_id)])
        elif collection:
            # Use ChromaDB
            collection.delete(ids=[str(chat_id)])
        else:
            return
        
        logger.info(f"Chat deleted from vector database: {chat_id}")
    except Exception as e:
        logger.error(f"Failed to delete chat from vector database: {e}", exc_info=True)
        # Don't raise - allow app to continue

def get_all_chats():
    """
    Отримує всі чати з векторної бази даних.
    
    Returns:
        List of chat dictionaries with id, metadata, document, and preview
    """
    logger = get_logger()
    if not vector_db_available:
        logger.debug("Vector database not available, returning empty list")
        return []
    
    try:
        if use_faiss and faiss_db:
            # Use FAISS
            all_data = faiss_db.get()
        elif collection:
            # Use ChromaDB
            all_data = collection.get()
        else:
            return []
        
        entries = []
        if all_data.get('ids') and len(all_data['ids']) > 0:
            for i, chat_id in enumerate(all_data['ids']):
                metadata = all_data['metadatas'][i] if all_data.get('metadatas') and i < len(all_data['metadatas']) else {}
                document = all_data['documents'][i] if all_data.get('documents') and i < len(all_data['documents']) else ""
                
                entries.append({
                    "id": chat_id,
                    "metadata": metadata,
                    "document": document,
                    "preview": document[:200] + "..." if len(document) > 200 else document
                })
        
        logger.debug(f"Retrieved {len(entries)} chats from vector database")
        return entries
    except Exception as e:
        logger.error(f"Failed to get all chats from vector database: {e}", exc_info=True)
        return []

def update_chat(chat_id, chat_text, metadata=None):
    """
    Оновлює чат у векторній базі даних.
    Якщо запис не існує, створює новий.
    """
    logger = get_logger()
    if not vector_db_available:
        logger.debug("Vector database not available, skipping update")
        return
    
    if metadata is None:
        metadata = {}
    
    try:
        if use_faiss and faiss_db:
            # Use FAISS - update will handle create if not exists
            try:
                faiss_db.update(
                    ids=[str(chat_id)],
                    documents=[chat_text],
                    metadatas=[metadata]
                )
                logger.debug(f"Chat updated in FAISS database: {chat_id}")
            except Exception:
                # If update fails, try add
                try:
                    faiss_db.add(
                        ids=[str(chat_id)],
                        documents=[chat_text],
                        metadatas=[metadata]
                    )
                    logger.debug(f"Chat created in FAISS database: {chat_id}")
                except Exception as add_error:
                    logger.warning(f"Failed to add chat to FAISS database: {add_error}")
        elif collection:
            # Use ChromaDB
            try:
                collection.update(
                    ids=[str(chat_id)],
                    documents=[chat_text],
                    metadatas=[metadata]
                )
                logger.debug(f"Chat updated in vector database: {chat_id}")
            except Exception:
                # Якщо запис не існує, створюємо новий
                try:
                    collection.add(
                        documents=[chat_text],
                        metadatas=[metadata],
                        ids=[str(chat_id)]
                    )
                    logger.debug(f"Chat created in vector database: {chat_id}")
                except Exception as add_error:
                    logger.warning(f"Failed to add chat to vector database: {add_error}")
        else:
            logger.debug("No vector database collection available")
    except Exception as e:
        logger.error(f"Failed to update chat in vector database: {e}", exc_info=True)
        # Don't raise - allow app to continue