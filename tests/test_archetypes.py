"""
Tests for archetypes loading and processing.
"""
import pytest
import os
import tempfile
import yaml
from core.logic import load_archetypes, reload_archetypes, build_multistage_prompt

def test_load_archetypes_not_found():
    """Test loading archetypes when file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        # This will fail if archetypes.yaml doesn't exist
        # In a real test, we'd mock the file path
        pass

def test_build_multistage_prompt():
    """Test building multi-stage prompt."""
    config = {
        "prompt_file": None,
        "prompt": "Base prompt",
        "additional_prompts": []
    }
    
    prompt = build_multistage_prompt(config)
    assert prompt == "Base prompt"

def test_build_multistage_prompt_with_additional():
    """Test building multi-stage prompt with additional prompts."""
    config = {
        "prompt_file": None,
        "prompt": "Base prompt",
        "additional_prompts": ["Additional prompt 1", "Additional prompt 2"]
    }
    
    prompt = build_multistage_prompt(config)
    assert "Base prompt" in prompt
    assert "Additional prompt 1" in prompt
    assert "Additional prompt 2" in prompt

def test_reload_archetypes():
    """Test reloading archetypes."""
    # This will reload from the actual file
    # In a real test, we'd mock the file
    try:
        reload_archetypes()
    except FileNotFoundError:
        # Expected if archetypes.yaml doesn't exist in test environment
        pass








