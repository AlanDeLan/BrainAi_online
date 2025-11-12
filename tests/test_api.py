"""
Tests for API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_endpoint():
    """Test root endpoint returns HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_process_endpoint_missing_fields():
    """Test process endpoint with missing fields."""
    response = client.post("/process", json={})
    assert response.status_code == 400
    assert "required" in response.json()["detail"].lower()

def test_process_endpoint_missing_text():
    """Test process endpoint with missing text."""
    response = client.post("/process", json={"archetype": "test"})
    assert response.status_code == 400

def test_process_endpoint_missing_archetype():
    """Test process endpoint with missing archetype."""
    response = client.post("/process", json={"text": "test"})
    assert response.status_code == 400

def test_get_history_list():
    """Test getting history list."""
    response = client.get("/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_archetypes():
    """Test getting archetypes configuration."""
    response = client.get("/api/archetypes")
    assert response.status_code == 200
    assert "archetypes" in response.json()

def test_get_ai_provider():
    """Test getting AI provider configuration."""
    response = client.get("/api/ai-provider")
    assert response.status_code == 200
    assert "provider" in response.json()

def test_get_vector_db():
    """Test getting vector database entries."""
    response = client.get("/api/vector-db")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_supported_models():
    """Test getting supported models."""
    response = client.get("/api/supported-models")
    assert response.status_code == 200
    assert "models" in response.json()








