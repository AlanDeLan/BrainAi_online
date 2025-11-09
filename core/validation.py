"""
Validation utilities for Local Brain configuration.
"""
import os
import yaml
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError, field_validator
from core.logger import logger

class ArchetypeConfig(BaseModel):
    """Pydantic model for archetype configuration validation."""
    name: str = Field(..., min_length=1, description="Archetype name")
    description: Optional[str] = Field(None, description="Archetype description")
    model_name: str = Field(..., min_length=1, description="AI model name")
    role: str = Field(..., description="Role for RADA mode")
    prompt_file: Optional[str] = Field(None, description="Path to prompt file")
    prompt: Optional[str] = Field(None, description="Direct prompt text (deprecated)")
    additional_prompts: Optional[List[str]] = Field(None, description="Additional prompt files")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is one of the allowed values."""
        allowed_roles = ['creative_generator', 'critic', 'executor']
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {allowed_roles}")
        return v
    
    @field_validator('prompt_file', 'prompt')
    @classmethod
    def validate_prompt_source(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure at least one of prompt_file or prompt is provided."""
        # This will be validated at the model level
        return v
    
    def model_post_init(self, __context):
        """Validate that at least prompt_file or prompt is provided."""
        if not self.prompt_file and not self.prompt:
            raise ValueError("Either 'prompt_file' or 'prompt' must be provided")

def validate_archetypes_config(config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate archetypes configuration.
    
    Args:
        config: Dictionary with archetypes configuration
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not isinstance(config, dict):
        errors.append("Configuration must be a dictionary")
        return False, errors
    
    if len(config) == 0:
        errors.append("At least one archetype must be defined")
        return False, errors
    
    if len(config) > 10:
        errors.append("Too many archetypes (maximum 10 allowed)")
    
    for key, archetype_config in config.items():
        if not isinstance(key, str):
            errors.append(f"Archetype key must be a string, got: {type(key).__name__}")
            continue
        
        # Validate key format
        if not key or not key.replace('_', '').replace('-', '').isalnum():
            errors.append(f"Archetype key '{key}' must contain only alphanumeric characters, underscores, or hyphens")
        
        if not isinstance(archetype_config, dict):
            errors.append(f"Archetype '{key}' configuration must be a dictionary")
            continue
        
        try:
            # Validate using Pydantic model
            ArchetypeConfig(**archetype_config)
        except ValidationError as e:
            for error in e.errors():
                field = '.'.join(str(loc) for loc in error['loc'])
                errors.append(f"Archetype '{key}': {field} - {error['msg']}")
        except Exception as e:
            errors.append(f"Archetype '{key}': {str(e)}")
    
    return len(errors) == 0, errors

def validate_prompt_files(config: Dict, base_dir: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    Validate that prompt files exist.
    
    Args:
        config: Archetypes configuration
        base_dir: Base directory for resolving file paths (optional)
    
    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    import os
    import sys
    
    if base_dir is None:
        # Get base directory similar to core.logic
        if hasattr(sys, '_MEIPASS'):
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                if 'core' in base_dir:
                    base_dir = os.path.dirname(base_dir)
        else:
            base_dir = os.getcwd()
    
    warnings = []
    
    for key, archetype_config in config.items():
        if not isinstance(archetype_config, dict):
            continue
        
        # Check main prompt file
        prompt_file = archetype_config.get('prompt_file')
        if prompt_file:
            # Remove 'prompts/' prefix if present
            if prompt_file.startswith('prompts/'):
                file_path = os.path.join(base_dir, prompt_file)
            else:
                file_path = os.path.join(base_dir, 'prompts', prompt_file)
            
            if not os.path.exists(file_path):
                warnings.append(f"Archetype '{key}': Prompt file not found: {prompt_file}")
        
        # Check additional prompt files
        additional_prompts = archetype_config.get('additional_prompts', [])
        if isinstance(additional_prompts, list):
            for add_prompt in additional_prompts:
                if isinstance(add_prompt, str) and any(add_prompt.endswith(ext) for ext in ['.txt', '.md']):
                    if add_prompt.startswith('prompts/'):
                        file_path = os.path.join(base_dir, add_prompt)
                    else:
                        file_path = os.path.join(base_dir, 'prompts', add_prompt)
                    
                    if not os.path.exists(file_path):
                        warnings.append(f"Archetype '{key}': Additional prompt file not found: {add_prompt}")
    
    return len(warnings) == 0, warnings

def validate_env_file(env_path: str) -> Tuple[bool, List[str]]:
    """
    Validate .env file configuration.
    
    Args:
        env_path: Path to .env file
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not os.path.exists(env_path):
        errors.append(f".env file not found: {env_path}")
        return False, errors
    
    try:
        from dotenv import dotenv_values
        env_values = dotenv_values(env_path)
        
        # Check AI_PROVIDER
        ai_provider = env_values.get('AI_PROVIDER', 'google_ai')
        if ai_provider not in ['google_ai', 'openai']:
            errors.append(f"Invalid AI_PROVIDER: {ai_provider}. Must be 'google_ai' or 'openai'")
        
        # Check API keys based on provider
        if ai_provider == 'google_ai':
            if not env_values.get('GOOGLE_API_KEY'):
                errors.append("GOOGLE_API_KEY is required when AI_PROVIDER=google_ai")
        elif ai_provider == 'openai':
            if not env_values.get('OPENAI_API_KEY'):
                errors.append("OPENAI_API_KEY is required when AI_PROVIDER=openai")
        
    except Exception as e:
        errors.append(f"Error reading .env file: {str(e)}")
    
    return len(errors) == 0, errors

def validate_archetypes_yaml(yaml_path: str) -> Tuple[bool, List[str], List[str]]:
    """
    Validate archetypes.yaml file.
    
    Args:
        yaml_path: Path to archetypes.yaml file
    
    Returns:
        Tuple of (is_valid, list_of_errors, list_of_warnings)
    """
    errors = []
    warnings = []
    
    if not os.path.exists(yaml_path):
        errors.append(f"archetypes.yaml not found: {yaml_path}")
        return False, errors, warnings
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if config is None:
            errors.append("archetypes.yaml is empty")
            return False, errors, warnings
        
        # Validate structure
        is_valid, validation_errors = validate_archetypes_config(config)
        errors.extend(validation_errors)
        
        # Validate prompt files
        base_dir = os.path.dirname(yaml_path)
        files_valid, file_warnings = validate_prompt_files(config, base_dir)
        warnings.extend(file_warnings)
        
        return is_valid, errors, warnings
        
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML syntax: {str(e)}")
        return False, errors, warnings
    except Exception as e:
        errors.append(f"Error reading archetypes.yaml: {str(e)}")
        return False, errors, warnings

