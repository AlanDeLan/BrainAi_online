import chromadb
from chromadb.config import Settings

# Ініціалізація клієнта ChromaDB з локальним збереженням
client = chromadb.Client(Settings(persist_directory="vector_db_storage"))

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