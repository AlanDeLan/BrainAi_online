"""
Tests for validation functions.
"""
import pytest
import os
import tempfile
import yaml
from core.validation import (
    validate_archetypes_config,
    validate_prompt_files,
    validate_env_file,
    validate_archetypes_yaml
)

def test_validate_archetypes_config_empty():
    """Test validation of empty configuration."""
    is_valid, errors = validate_archetypes_config({})
    assert not is_valid
    assert len(errors) > 0
    assert "at least one" in errors[0].lower()

def test_validate_archetypes_config_valid():
    """Test validation of valid configuration."""
    config = {
        "test_agent": {
            "name": "Test Agent",
            "description": "Test description",
            "model_name": "gemini-2.5-flash",
            "role": "creative_generator",
            "prompt_file": "prompts/test.txt"
        }
    }
    is_valid, errors = validate_archetypes_config(config)
    assert is_valid
    assert len(errors) == 0

def test_validate_archetypes_config_missing_name():
    """Test validation with missing name."""
    config = {
        "test_agent": {
            "model_name": "gemini-2.5-flash",
            "role": "creative_generator",
            "prompt_file": "prompts/test.txt"
        }
    }
    is_valid, errors = validate_archetypes_config(config)
    assert not is_valid
    assert any("name" in error.lower() for error in errors)

def test_validate_archetypes_config_invalid_role():
    """Test validation with invalid role."""
    config = {
        "test_agent": {
            "name": "Test Agent",
            "model_name": "gemini-2.5-flash",
            "role": "invalid_role",
            "prompt_file": "prompts/test.txt"
        }
    }
    is_valid, errors = validate_archetypes_config(config)
    assert not is_valid
    assert any("role" in error.lower() for error in errors)

def test_validate_archetypes_config_no_prompt():
    """Test validation with no prompt file or prompt."""
    config = {
        "test_agent": {
            "name": "Test Agent",
            "model_name": "gemini-2.5-flash",
            "role": "creative_generator"
        }
    }
    is_valid, errors = validate_archetypes_config(config)
    assert not is_valid
    assert any("prompt" in error.lower() for error in errors)

def test_validate_prompt_files():
    """Test validation of prompt files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test prompt file
        prompt_file = os.path.join(tmpdir, "test.txt")
        with open(prompt_file, "w") as f:
            f.write("Test prompt")
        
        config = {
            "test_agent": {
                "prompt_file": "test.txt"
            }
        }
        
        is_valid, warnings = validate_prompt_files(config, tmpdir)
        assert is_valid
        assert len(warnings) == 0

def test_validate_prompt_files_missing():
    """Test validation with missing prompt file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            "test_agent": {
                "prompt_file": "nonexistent.txt"
            }
        }
        
        is_valid, warnings = validate_prompt_files(config, tmpdir)
        assert not is_valid
        assert len(warnings) > 0

def test_validate_env_file_missing():
    """Test validation of missing .env file."""
    is_valid, errors = validate_env_file("/nonexistent/.env")
    assert not is_valid
    assert len(errors) > 0

def test_validate_archetypes_yaml_valid():
    """Test validation of valid archetypes.yaml file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create prompts directory
        prompts_dir = os.path.join(tmpdir, "prompts")
        os.makedirs(prompts_dir, exist_ok=True)
        
        # Create test prompt file
        prompt_file = os.path.join(prompts_dir, "test.txt")
        with open(prompt_file, "w") as f:
            f.write("Test prompt")
        
        # Create archetypes.yaml
        yaml_file = os.path.join(tmpdir, "archetypes.yaml")
        config = {
            "test_agent": {
                "name": "Test Agent",
                "description": "Test description",
                "model_name": "gemini-2.5-flash",
                "role": "creative_generator",
                "prompt_file": "prompts/test.txt"
            }
        }
        with open(yaml_file, "w") as f:
            yaml.dump(config, f)
        
        is_valid, errors, warnings = validate_archetypes_yaml(yaml_file)
        assert is_valid
        assert len(errors) == 0

def test_validate_archetypes_yaml_invalid_yaml():
    """Test validation of invalid YAML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_file = os.path.join(tmpdir, "archetypes.yaml")
        with open(yaml_file, "w") as f:
            f.write("invalid: yaml: content: [")
        
        is_valid, errors, warnings = validate_archetypes_yaml(yaml_file)
        assert not is_valid
        assert len(errors) > 0





