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
collections_cache = {}  # Cache for per-user collections
faiss_db = None
vector_db_available = False
use_faiss = False


def get_user_collection(user_id):
    """
    Get or create collection for specific user.
    
    Args:
        user_id: User ID (can be None for legacy mode)
        
    Returns:
        ChromaDB collection for user (or default collection if user_id is None)
    """
    if not vector_db_available or client is None:
        return None
    
    # Legacy mode: use default collection if no user_id
    if user_id is None:
        collection_name = "chat_memory_legacy"
    else:
        collection_name = f"user_{user_id}_chats"
    
    # Check cache first
    if collection_name in collections_cache:
        return collections_cache[collection_name]
    
    # Create or get collection
    try:
        user_collection = client.get_or_create_collection(collection_name)
        collections_cache[collection_name] = user_collection
        return user_collection
    except Exception as e:
        logger = get_logger()
        logger.error(f"Error creating collection for user {user_id}: {e}")
        return None


def cleanup_old_user_messages(user_id: int, keep_count: int = 100):
    """
    Clean up old messages for user, keeping only last N.
    
    Args:
        user_id: User ID
        keep_count: Number of messages to keep
    """
    collection = get_user_collection(user_id)
    if collection is None:
        return
    
    try:
        # Get all messages
        results = collection.get()
        if results and 'ids' in results:
            total = len(results['ids'])
            if total > keep_count:
                # Sort by timestamp (if available in metadata) or just take first N
                ids_to_delete = results['ids'][:-keep_count]  # Keep last keep_count
                if ids_to_delete:
                    collection.delete(ids=ids_to_delete)
                    logger = get_logger()
                    logger.info(f"Cleaned up {len(ids_to_delete)} old messages for user {user_id}")
    except Exception as e:
        logger = get_logger()
        logger.error(f"Error cleaning up messages for user {user_id}: {e}")

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
    
    # No single collection - we'll create per-user collections on demand
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
        faiss_db = None
        vector_db_available = False
        use_faiss = False

def save_chat(chat_id, chat_text, archetypes, timestamp, topic=None, user_id=None):
    """
    Зберігає чат як один документ у векторній базі.
    archetypes: список архетипів (list) -> треба перетворити на str!
    user_id: ID користувача (обов'язково для multi-user)
    """
    logger = get_logger()
    if not vector_db_available:
        logger.debug("Vector database not available, skipping save")
        return
    
    if user_id is None:
        logger.error("user_id is required for save_chat")
        return
    
    try:
        metadata = {
            "chat_id": chat_id,
            "archetypes": ", ".join(archetypes) if isinstance(archetypes, list) else str(archetypes),
            "timestamp": timestamp,
            "topic": topic or "",
            "user_id": str(user_id)
        }
        
        if use_faiss and faiss_db:
            # Use FAISS (add user_id to metadata)
            faiss_db.add(
                ids=[str(chat_id)],
                documents=[chat_text],
                metadatas=[metadata]
            )
        else:
            # Use ChromaDB with per-user collection
            collection = get_user_collection(user_id)
            if collection is None:
                logger.error(f"Failed to get collection for user {user_id}")
                return
            
            collection.add(
                documents=[chat_text],
                metadatas=[metadata],
                ids=[str(chat_id)]
            )
            
            # Cleanup old messages
            cleanup_old_user_messages(user_id, keep_count=100)
        
        logger.debug(f"Chat saved to vector database: {chat_id} for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to save chat to vector database: {e}", exc_info=True)
        # Don't raise - allow app to continue

def save_message(chat_id, message_id, message_text, role, archetype=None, timestamp=None, user_id=None):
    """
    Зберігає окреме повідомлення у векторній базі.
    
    Args:
        chat_id: ID чату
        message_id: Унікальний ID повідомлення (наприклад, "{chat_id}_msg_{index}")
        message_text: Текст повідомлення
        role: Роль повідомлення ("user" або "assistant")
        archetype: Архетип (опціонально)
        timestamp: Часова мітка (опціонально)
        user_id: ID користувача (обов'язково для multi-user)
    """
    logger = get_logger()
    if not vector_db_available:
        logger.debug("Vector database not available, skipping save")
        return
    
    if user_id is None:
        logger.error("user_id is required for save_message")
        return
    
    try:
        if timestamp is None:
            import datetime
            timestamp = datetime.datetime.now().isoformat()
        
        metadata = {
            "chat_id": str(chat_id),
            "message_id": str(message_id),
            "role": role,
            "timestamp": timestamp,
            "user_id": str(user_id)
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
        else:
            # Use ChromaDB with per-user collection
            collection = get_user_collection(user_id)
            if collection is None:
                logger.error(f"Failed to get collection for user {user_id}")
                return
            
            collection.add(
                documents=[message_text],
                metadatas=[metadata],
                ids=[str(message_id)]
            )
            
            # Cleanup old messages
            cleanup_old_user_messages(user_id, keep_count=100)
        
        logger.debug(f"Message saved to vector database: {message_id} (chat: {chat_id}, user: {user_id})")
    except Exception as e:
        logger.error(f"Failed to save message to vector database: {e}", exc_info=True)
        # Don't raise - allow app to continue

def search_chat_messages(chat_id, query, n_results=5, user_id=None):
    """
    Пошук релевантних повідомлень в конкретному чаті.
    
    Args:
        chat_id: ID чату для пошуку
        query: Текст для пошуку (str)
        n_results: Кількість результатів (int)
        user_id: ID користувача (обов'язково для multi-user)
    
    Returns:
        List of message dictionaries with text, role, score, etc.
    """
    logger = get_logger()
    if not vector_db_available:
        logger.debug("Vector database not available, returning empty results")
        return []
    
    if user_id is None:
        logger.error("user_id is required for search_chat_messages")
        return []
    
    try:
        if use_faiss and faiss_db:
            # Use FAISS with filter
            results = faiss_db.query(
                query_texts=[query],
                n_results=n_results,
                where={"chat_id": str(chat_id), "user_id": str(user_id)}
            )
        else:
            # Use ChromaDB with per-user collection
            collection = get_user_collection(user_id)
            if collection is None:
                logger.error(f"Failed to get collection for user {user_id}")
                return []
            
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

def search_chats(query, n_results=3, user_id=None):
    """
    Пошук релевантних чатів для контексту.
    query: текст для пошуку (str)
    n_results: кількість результатів (int)
    user_id: ID користувача (обов'язково для multi-user)
    """
    logger = get_logger()
    if not vector_db_available:
        logger.debug("Vector database not available, returning empty results")
        return []
    
    if user_id is None:
        logger.error("user_id is required for search_chats")
        return []
    
    try:
        if use_faiss and faiss_db:
            # Use FAISS with user filter
            results = faiss_db.query(
                query_texts=[query],
                n_results=n_results,
                where={"user_id": str(user_id)}
            )
        else:
            # Use ChromaDB with per-user collection
            collection = get_user_collection(user_id)
            if collection is None:
                logger.error(f"Failed to get collection for user {user_id}")
                return []
            
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )
        
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
        logger.debug(f"Found {len(chats)} chats for user {user_id} with query: {query[:50]}")
        return chats
    except Exception as e:
        logger.error(f"Failed to search chats in vector database: {e}", exc_info=True)
        return []

def delete_chat(chat_id, user_id=None):
    """
    Видаляє чат з векторної бази за chat_id.
    
    Args:
        chat_id: ID чату для видалення
        user_id: ID користувача (обов'язково для multi-user)
    """
    logger = get_logger()
    if not vector_db_available:
        logger.debug("Vector database not available, skipping delete")
        return
    
    if user_id is None:
        logger.error("user_id is required for delete_chat")
        return
    
    try:
        if use_faiss and faiss_db:
            # Use FAISS
            faiss_db.delete(ids=[str(chat_id)])
        else:
            # Use ChromaDB with per-user collection
            collection = get_user_collection(user_id)
            if collection is None:
                logger.error(f"Failed to get collection for user {user_id}")
                return
            
            collection.delete(ids=[str(chat_id)])
        
        logger.info(f"Chat {chat_id} deleted from vector database for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to delete chat from vector database: {e}", exc_info=True)

def get_all_chats(user_id=None):
    """
    Отримує всі чати з векторної бази даних для користувача.
    
    Args:
        user_id: ID користувача (обов'язково для multi-user)
        
    Returns:
        List of chat dictionaries with id, metadata, document, and preview
    """
    logger = get_logger()
    if not vector_db_available:
        logger.debug("Vector database not available, returning empty list")
        return []
    
    if user_id is None:
        logger.error("user_id is required for get_all_chats")
        return []
    
    try:
        if use_faiss and faiss_db:
            # Use FAISS - get all and filter by user_id
            all_data = faiss_db.get()
            # Filter by user_id
            filtered_ids = []
            filtered_metadatas = []
            filtered_documents = []
            
            if all_data.get('ids'):
                for i, chat_id in enumerate(all_data['ids']):
                    metadata = all_data['metadatas'][i] if all_data.get('metadatas') and i < len(all_data['metadatas']) else {}
                    if metadata.get('user_id') == str(user_id):
                        filtered_ids.append(chat_id)
                        filtered_metadatas.append(metadata)
                        if all_data.get('documents') and i < len(all_data['documents']):
                            filtered_documents.append(all_data['documents'][i])
            
            all_data = {
                'ids': filtered_ids,
                'metadatas': filtered_metadatas,
                'documents': filtered_documents
            }
        else:
            # Use ChromaDB with per-user collection
            collection = get_user_collection(user_id)
            if collection is None:
                logger.error(f"Failed to get collection for user {user_id}")
                return []
            
            all_data = collection.get()
        
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
        
        logger.debug(f"Retrieved {len(entries)} chats from vector database for user {user_id}")
        return entries
    except Exception as e:
        logger.error(f"Failed to get all chats from vector database: {e}", exc_info=True)
        return []

def update_chat(chat_id, chat_text, metadata=None, user_id=None):
    """
    Оновлює чат у векторній базі даних.
    Якщо запис не існує, створює новий.
    
    Args:
        chat_id: ID чату
        chat_text: Текст чату
        metadata: Метадані чату (dict)
        user_id: ID користувача (обов'язково для multi-user)
    """
    logger = get_logger()
    if not vector_db_available:
        logger.debug("Vector database not available, skipping update")
        return
    
    if user_id is None:
        logger.error("user_id is required for update_chat")
        return
    
    if metadata is None:
        metadata = {}
    
    # Add user_id to metadata
    metadata["user_id"] = str(user_id)
    
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
                faiss_db.add(
                    ids=[str(chat_id)],
                    documents=[chat_text],
                    metadatas=[metadata]
                )
                logger.debug(f"Chat added to FAISS database: {chat_id}")
        else:
            # Use ChromaDB with per-user collection
            collection = get_user_collection(user_id)
            if collection is None:
                logger.error(f"Failed to get collection for user {user_id}")
                return
            
            try:
                collection.update(
                    ids=[str(chat_id)],
                    documents=[chat_text],
                    metadatas=[metadata]
                )
                logger.debug(f"Chat updated in ChromaDB: {chat_id}")
            except Exception:
                # If update fails, try add
                collection.add(
                    ids=[str(chat_id)],
                    documents=[chat_text],
                    metadatas=[metadata]
                )
                logger.debug(f"Chat added to ChromaDB: {chat_id}")
            
            # Cleanup old messages
            cleanup_old_user_messages(user_id, keep_count=100)
    except Exception as e:
        logger.error(f"Failed to update chat in vector database: {e}", exc_info=True)
        logger.error(f"Failed to update chat in vector database: {e}", exc_info=True)
        # Don't raise - allow app to continue