"""Hard-disabled legacy vector DB client (Chroma/FAISS).

We now use PostgreSQL + pgvector exclusively.
Importing this module must never trigger heavy initialization.
All functions are safe no-ops for backward compatibility.
"""
from typing import List, Dict, Any, Optional

def is_vector_db_available() -> bool:
    return False

def get_vector_db_type() -> Optional[str]:
    return None

def get_user_collection(user_id):  # noqa: D401
    return None

def save_chat(chat_id, chat_text, archetypes, timestamp, topic=None, user_id=None):
    return None

def save_message(chat_id, message_id, message_text, role, archetype=None, timestamp=None, user_id=None):
    return None

def search_chat_messages(chat_id, query, n_results: int = 5, user_id=None) -> List[Dict[str, Any]]:
    return []

def search_chats(query, n_results: int = 3, user_id=None) -> List[Dict[str, Any]]:
    return []

def delete_chat(chat_id, user_id=None):
    return None

def get_all_chats(user_id=None) -> List[Dict[str, Any]]:
    return []

def get_all_chats_grouped(user_id=None) -> List[Dict[str, Any]]:
    return []

def update_chat(chat_id, chat_text, metadata=None, user_id=None):
    return None

# Original ChromaDB initialization code (DISABLED):
# try:
#     logger = get_logger()
#     chromadb, Settings = _import_chromadb()
#     vector_db_dir = os.path.join(get_base_dir(), "vector_db_storage")
#     os.makedirs(vector_db_dir, exist_ok=True)
#     
#     # Try to use PersistentClient first (more reliable with PyInstaller)
#     try:
#         client = chromadb.PersistentClient(path=vector_db_dir)
#     except (Exception, ModuleNotFoundError, ImportError) as e:
#         # Fallback to Client with Settings
#         try:
#             client = chromadb.Client(Settings(persist_directory=vector_db_dir))
#         except (Exception, ModuleNotFoundError, ImportError) as e2:
#             # If both fail, raise the original error
#             raise e
#     
#     # No single collection - we'll create per-user collections on demand
#     vector_db_available = True
#     use_faiss = False
#     logger.info(f"ChromaDB initialized at {vector_db_dir}")
# except (ImportError, ModuleNotFoundError, Exception) as e:
#     logger = get_logger()
#     error_msg = str(e)
#     # Check if it's the Rust module error
#     if "chromadb.api.rust" in error_msg or "No module named" in error_msg:
#         logger.warning("ChromaDB Rust components not available, trying FAISS as fallback...")
#     else:
#         logger.warning(f"ChromaDB not available: {error_msg}, trying FAISS as fallback...")
#     
#     # Try FAISS as fallback
#     try:
#         from vector_db.faiss_client import FAISSVectorDB
#         vector_db_dir = os.path.join(get_base_dir(), "vector_db_storage")
#         faiss_db = FAISSVectorDB(storage_dir=vector_db_dir)
#         vector_db_available = True
#         use_faiss = True
#         logger.info(f"FAISS vector database initialized at {vector_db_dir}")
#     except Exception as faiss_error:
#         logger.error(f"FAISS also failed: {faiss_error}", exc_info=True)
#         logger.warning("Vector database features will be disabled. Chat history will still be saved to files.")
#         client = None
#         faiss_db = None
#         vector_db_available = False
#         use_faiss = False

# (Legacy implementation removed)

# (Legacy implementation removed)

# (Legacy implementation removed)

# (Legacy implementation removed)

# (Legacy implementation removed)

# (Legacy implementation removed)


# (Legacy implementation removed)


# (Legacy implementation removed)
