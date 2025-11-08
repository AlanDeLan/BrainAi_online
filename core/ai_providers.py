"""
Module for working with different AI providers.
Supports: Google AI Studio, OpenAI API, and others.
"""
import os
import sys
from typing import Dict, Optional, Any
from enum import Enum

class AIProvider(Enum):
    """AI provider types."""
    GOOGLE_AI = "google_ai"
    OPENAI = "openai"
    # Can add others: ANTHROPIC, COHERE, etc.

# Global variable for current provider
_current_provider: Optional[AIProvider] = None
_provider_config: Dict[str, Any] = {}

def get_base_directory():
    """Get base directory for searching configuration."""
    if hasattr(sys, '_MEIPASS'):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if 'core' in base_dir:
                base_dir = os.path.dirname(base_dir)
            return base_dir
    else:
        return os.getcwd()

def load_provider_config():
    """Load AI provider configuration from .env file."""
    global _current_provider, _provider_config
    
    from dotenv import dotenv_values, load_dotenv
    
    base_dir = get_base_directory()
    env_paths = [
        os.path.join(base_dir, '.env'),
        os.path.join(os.path.dirname(__file__), '..', '.env'),
        '.env',
    ]
    
    env_values = {}
    for env_path in env_paths:
        abs_path = os.path.abspath(env_path)
        if os.path.exists(abs_path):
            try:
                env_values = dotenv_values(abs_path)
                break
            except Exception:
                continue
    
    # If not found, try load_dotenv
    if not env_values:
        load_dotenv(override=True)
        env_values = {
            'AI_PROVIDER': os.getenv('AI_PROVIDER', 'google_ai'),
            'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY'),
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'OPENAI_BASE_URL': os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
        }
    
    # Determine provider
    provider_name = env_values.get('AI_PROVIDER', 'google_ai').lower()
    try:
        _current_provider = AIProvider(provider_name)
    except ValueError:
        # If unknown provider, use Google AI by default
        _current_provider = AIProvider.GOOGLE_AI
    
    # Save configuration
    _provider_config = {
        'provider': _current_provider,
        'google_api_key': env_values.get('GOOGLE_API_KEY') or os.getenv('GOOGLE_API_KEY'),
        'openai_api_key': env_values.get('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY'),
        'openai_base_url': env_values.get('OPENAI_BASE_URL') or os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
    }
    
    return _current_provider, _provider_config

def get_current_provider() -> AIProvider:
    """Get current AI provider."""
    global _current_provider
    if _current_provider is None:
        load_provider_config()
    return _current_provider

def get_provider_config() -> Dict[str, Any]:
    """Get current provider configuration."""
    global _provider_config
    if not _provider_config:
        load_provider_config()
    return _provider_config

def set_provider(provider: AIProvider, config: Optional[Dict[str, Any]] = None):
    """Set AI provider."""
    global _current_provider, _provider_config
    _current_provider = provider
    if config:
        _provider_config.update(config)

def generate_response(model_name: str, prompt: str, **kwargs) -> str:
    """
    Generate response through current AI provider.
    
    Args:
        model_name: Model name (depends on provider)
        prompt: Prompt text
        **kwargs: Additional parameters
    
    Returns:
        AI response
    """
    provider = get_current_provider()
    config = get_provider_config()
    
    if provider == AIProvider.GOOGLE_AI:
        return _generate_google_ai(model_name, prompt, config, **kwargs)
    elif provider == AIProvider.OPENAI:
        return _generate_openai(model_name, prompt, config, **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")

def _generate_google_ai(model_name: str, prompt: str, config: Dict[str, Any], **kwargs) -> str:
    """Generate response through Google AI."""
    import google.generativeai as genai
    
    api_key = config.get('google_api_key')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in configuration")
    
    # Configure API key
    genai.configure(api_key=api_key)
    
    # Create model
    model = genai.GenerativeModel(model_name)
    
    # Generate response
    response = model.generate_content(prompt)
    return response.text.strip()

def _generate_openai(model_name: str, prompt: str, config: Dict[str, Any], **kwargs) -> str:
    """Generate response through OpenAI API."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("OpenAI library not installed. Install: pip install openai")
    
    api_key = config.get('openai_api_key')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in configuration")
    
    base_url = config.get('openai_base_url', 'https://api.openai.com/v1')
    
    # Create client
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    # Generate response
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=kwargs.get('temperature', 0.7),
        max_tokens=kwargs.get('max_tokens', 2000),
    )
    
    return response.choices[0].message.content.strip()

def get_supported_models(provider: Optional[AIProvider] = None) -> Dict[str, list]:
    """Get list of supported models for provider."""
    if provider is None:
        provider = get_current_provider()
    
    if provider == AIProvider.GOOGLE_AI:
        return {
            'google_ai': [
                'gemini-2.5-flash',
                'gemini-1.5-pro',
                'gemini-1.5-flash',
                'gemini-pro',
            ]
        }
    elif provider == AIProvider.OPENAI:
        return {
            'openai': [
                'gpt-4o',
                'gpt-4-turbo',
                'gpt-4',
                'gpt-3.5-turbo',
                'gpt-3.5-turbo-16k',
            ]
        }
    else:
        return {}

def normalize_model_name(model_name: str, provider: Optional[AIProvider] = None) -> str:
    """Normalize model name for current provider."""
    if provider is None:
        provider = get_current_provider()
    
    # If model already matches provider, return as is
    if provider == AIProvider.GOOGLE_AI and model_name.startswith('gemini-'):
        return model_name
    elif provider == AIProvider.OPENAI and ('gpt' in model_name.lower() or 'o1' in model_name.lower()):
        return model_name
    
    # Try to find closest model
    supported = get_supported_models(provider)
    models = list(supported.values())[0] if supported else []
    
    # If model not found, return first available or original
    if models:
        # Try to find similar model
        for model in models:
            if model_name.lower() in model.lower() or model.lower() in model_name.lower():
                return model
        return models[0]  # Return first available
    
    return model_name

