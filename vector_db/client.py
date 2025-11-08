import os
import sys
import chromadb
from chromadb.config import Settings

# --- Функція для коректної роботи з ресурсами у PyInstaller ---
def get_base_dir():
    """Отримує базову директорію для збереження даних."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller: використовуємо директорію, де знаходиться exe файл
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if 'vector_db' in base_dir:
                base_dir = os.path.dirname(base_dir)
            return base_dir
    else:
        return os.getcwd()

# Ініціалізація клієнта ChromaDB з локальним збереженням
vector_db_dir = os.path.join(get_base_dir(), "vector_db_storage")
os.makedirs(vector_db_dir, exist_ok=True)
client = chromadb.Client(Settings(persist_directory=vector_db_dir))

# Колекція для збереження чатів
collection = client.get_or_create_collection("chat_memory")

def save_chat(chat_id, chat_text, archetypes, timestamp, topic=None):
    """
    Зберігає чат як один документ у векторній базі.
    archetypes: список архетипів (list) -> треба перетворити на str!
    """
    metadata = {
        "chat_id": chat_id,
        "archetypes": ", ".join(archetypes) if isinstance(archetypes, list) else str(archetypes),
        "timestamp": timestamp,
        "topic": topic or ""
    }
    collection.add(
        documents=[chat_text],
        metadatas=[metadata],
        ids=[str(chat_id)]
    )

def search_chats(query, n_results=3):
    """
    Пошук релевантних чатів для контексту.
    query: текст для пошуку (str)
    n_results: кількість результатів (int)
    """
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    chats = []
    for i in range(len(results["ids"][0])):
        chats.append({
            "chat_id": results["metadatas"][0][i].get("chat_id"),
            "archetypes": results["metadatas"][0][i].get("archetypes"),
            "timestamp": results["metadatas"][0][i].get("timestamp"),
            "topic": results["metadatas"][0][i].get("topic"),
            "text": results["documents"][0][i],
            "score": results["distances"][0][i]
        })
    return chats

def delete_chat(chat_id):
    """Видаляє чат з векторної бази за chat_id."""
    collection.delete(ids=[str(chat_id)])

def update_chat(chat_id, chat_text, metadata=None):
    """
    Оновлює чат у векторній базі даних.
    Якщо запис не існує, створює новий.
    """
    if metadata is None:
        metadata = {}
    
    # Спробуємо оновити існуючий запис
    try:
        collection.update(
            ids=[str(chat_id)],
            documents=[chat_text],
            metadatas=[metadata]
        )
    except Exception:
        # Якщо запис не існує, створюємо новий
        collection.add(
            documents=[chat_text],
            metadatas=[metadata],
            ids=[str(chat_id)]
        )