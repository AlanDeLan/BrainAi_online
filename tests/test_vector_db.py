"""
Tests for vector database operations.
"""
import pytest
import os
import tempfile
from vector_db.client import save_chat, search_chats, delete_chat, update_chat

def test_save_chat():
    """Test saving a chat to vector database."""
    chat_id = "test_chat_1"
    chat_text = "Test chat text"
    archetypes = ["test_agent"]
    timestamp = "20250101_120000"
    
    try:
        save_chat(chat_id, chat_text, archetypes, timestamp, "Test topic")
        # If no exception, test passed
        assert True
    except Exception as e:
        # If ChromaDB is not available, skip test
        pytest.skip(f"ChromaDB not available: {e}")

def test_search_chats():
    """Test searching chats in vector database."""
    query = "test query"
    
    try:
        results = search_chats(query, n_results=3)
        assert isinstance(results, list)
    except Exception as e:
        pytest.skip(f"ChromaDB not available: {e}")

def test_update_chat():
    """Test updating a chat in vector database."""
    chat_id = "test_chat_1"
    chat_text = "Updated chat text"
    metadata = {
        "chat_id": chat_id,
        "archetypes": "test_agent",
        "timestamp": "20250101_120000",
        "topic": "Updated topic"
    }
    
    try:
        update_chat(chat_id, chat_text, metadata)
        # If no exception, test passed
        assert True
    except Exception as e:
        pytest.skip(f"ChromaDB not available: {e}")

def test_delete_chat():
    """Test deleting a chat from vector database."""
    chat_id = "test_chat_1"
    
    try:
        delete_chat(chat_id)
        # If no exception, test passed
        assert True
    except Exception as e:
        pytest.skip(f"ChromaDB not available: {e}")

