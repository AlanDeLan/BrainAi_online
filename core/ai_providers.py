"""
Module for working with different AI providers.
Supports: Google AI Studio, OpenAI API, and others.
"""
import os
import sys
from typing import Dict, Optional, Any
from enum import Enum
from core.utils import get_base_directory
from core.logger import logger

class AIProvider(Enum):
    """AI provider types."""
    GOOGLE_AI = "google_ai"
    OPENAI = "openai"
    # Can add others: ANTHROPIC, COHERE, etc.

# Global variable for current provider
_current_provider: Optional[AIProvider] = None
_provider_config: Dict[str, Any] = {}

# Global dictionary to store ChatSession objects by chat_id
# Format: {(chat_id, model_name): ChatSession}
_google_ai_chat_sessions: Dict[tuple, Any] = {}

def load_provider_config():
    """Load AI provider configuration from settings or .env file."""
    global _current_provider, _provider_config
    
    # Try to load from settings first (production/Railway)
    try:
        from core.settings import settings
        _provider_config = {
            'google_api_key': settings.google_api_key,
            'openai_api_key': settings.openai_api_key,
            'openai_base_url': settings.openai_base_url,
        }
        provider_name = settings.ai_provider.lower()
        _current_provider = AIProvider(provider_name)
        
        # SUCCESS - settings loaded, return immediately
        return _current_provider, _provider_config
    except Exception as e:
        # Log the error but continue to fallback
        import sys
        if 'core.logger' in sys.modules:
            from core.logger import logger
            logger.debug(f"Settings not available, falling back to .env: {e}")
    
    # Fallback: load from .env file or environment variables (development)
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

def generate_response(model_name: str, system_prompt: str = None, user_message: str = None, context: str = None, conversation_history: list = None, prompt: str = None, chat_id: str = None, **kwargs) -> str:
    """
    Generate response through current AI provider.
    
    Args:
        model_name: Model name (depends on provider)
        system_prompt: System prompt/instructions
        user_message: Current user message
        context: Additional context (e.g., from vector DB)
        conversation_history: List of previous messages (deprecated - use chat_id for session reuse)
        prompt: Legacy parameter - full prompt text (used if system_prompt/user_message not provided)
        chat_id: Unique chat ID for session reuse (Google AI ChatSession will be reused for same chat_id)
        **kwargs: Additional parameters
    
    Returns:
        AI response
    """
    provider = get_current_provider()
    config = get_provider_config()
    
    # Auto-fallback: if Google AI is configured but key is missing, use OpenAI
    if provider == AIProvider.GOOGLE_AI and not config.get('google_api_key'):
        logger.warning("=" * 60)
        logger.warning("⚠️  GOOGLE_API_KEY not found in environment!")
        logger.warning("Automatically switching to OpenAI provider...")
        logger.warning("To fix: Add GOOGLE_API_KEY to your .env file")
        logger.warning("Or set AI_PROVIDER=openai in .env")
        logger.warning("=" * 60)
        provider = AIProvider.OPENAI
        
        # Verify OpenAI is available
        if not config.get('openai_api_key'):
            error_msg = "Neither GOOGLE_API_KEY nor OPENAI_API_KEY found! Please configure at least one AI provider."
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    if provider == AIProvider.GOOGLE_AI:
        logger.debug(f"Using Google AI provider: {model_name}")
        return _generate_google_ai(model_name, system_prompt=system_prompt, user_message=user_message, context=context, conversation_history=conversation_history, prompt=prompt, chat_id=chat_id, config=config, **kwargs)
    elif provider == AIProvider.OPENAI:
        logger.debug(f"Using OpenAI provider: {model_name}")
        return _generate_openai(model_name, system_prompt=system_prompt, user_message=user_message, context=context, conversation_history=conversation_history, prompt=prompt, chat_id=chat_id, config=config, **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")

def _generate_google_ai(model_name: str, system_prompt: str = None, user_message: str = None, context: str = None, conversation_history: list = None, prompt: str = None, chat_id: str = None, config: Dict[str, Any] = None, **kwargs) -> str:
    """
    Generate response through Google AI with ChatSession reuse.
    
    If chat_id is provided, reuses the same ChatSession for all messages in that chat.
    ChatSession automatically maintains conversation history, so we don't need to pass
    the entire history each time - this prevents token explosion.
    """
    import google.generativeai as genai
    global _google_ai_chat_sessions
    
    api_key = config.get('google_api_key')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in configuration")
    
    # Configure API key
    genai.configure(api_key=api_key)
    
    # Get generation config parameters
    generation_config = {
        'temperature': kwargs.get('temperature', 0.7),
        'max_output_tokens': kwargs.get('max_tokens', 2000),
    }
    
    # Add top_p and top_k if provided (Google AI supports these)
    if 'top_p' in kwargs:
        generation_config['top_p'] = kwargs['top_p']
    if 'top_k' in kwargs:
        generation_config['top_k'] = kwargs['top_k']
    
    # Build current message with context if available
    current_message = user_message if user_message else prompt
    if context:
        current_message = f"{context}\n\n{current_message}" if current_message else context
    
    # If chat_id is provided, reuse or create ChatSession
    if chat_id:
        # Create unique key: (chat_id, model_name, system_prompt_hash)
        # Different system prompts need different sessions
        system_prompt_hash = hash(system_prompt) if system_prompt else None
        session_key = (chat_id, model_name, system_prompt_hash)
        
        # Check if we have existing ChatSession
        if session_key in _google_ai_chat_sessions:
            # Reuse existing ChatSession - it automatically maintains history
            chat = _google_ai_chat_sessions[session_key]
            response = chat.send_message(
                current_message,
                generation_config=genai.types.GenerationConfig(**generation_config)
            )
        else:
            # Create new ChatSession
            # If we have conversation_history, initialize with it (for first message in chat)
            model = genai.GenerativeModel(
                model_name,
                system_instruction=system_prompt if system_prompt else None
            )
            
            if conversation_history and len(conversation_history) > 0:
                # Convert conversation_history to Google AI format
                history = []
                for msg in conversation_history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "user":
                        history.append({"role": "user", "parts": [content]})
                    elif role == "model":
                        history.append({"role": "model", "parts": [content]})
                chat = model.start_chat(history=history)
            else:
                # Start empty chat
                chat = model.start_chat(history=[])
            
            # Store ChatSession for reuse
            _google_ai_chat_sessions[session_key] = chat
            
            # Send message
            response = chat.send_message(
                current_message,
                generation_config=genai.types.GenerationConfig(**generation_config)
            )
    else:
        # No chat_id - use stateless approach
        model = genai.GenerativeModel(
            model_name,
            system_instruction=system_prompt if system_prompt else None
        )
        
        # If we have conversation history, use ChatSession for context (one-time)
        if conversation_history and len(conversation_history) > 0:
            # Convert conversation_history to Google AI format
            history = []
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    history.append({"role": "user", "parts": [content]})
                elif role == "model":
                    history.append({"role": "model", "parts": [content]})
            
            chat = model.start_chat(history=history)
            response = chat.send_message(
                current_message,
                generation_config=genai.types.GenerationConfig(**generation_config)
            )
        else:
            # No history - use simple generate_content
            if prompt:
                full_prompt = prompt
            else:
                parts = []
                if system_prompt:
                    parts.append(system_prompt)
                if context:
                    parts.append(context)
                if user_message:
                    parts.append(user_message)
                full_prompt = "\n\n".join(parts) if parts else ""
            
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(**generation_config)
            )
    
    return response.text.strip()

def _generate_openai(model_name: str, system_prompt: str = None, user_message: str = None, context: str = None, conversation_history: list = None, prompt: str = None, chat_id: str = None, config: Dict[str, Any] = None, **kwargs) -> str:
    """
    Generate response through OpenAI API with conversation history support.
    
    Note: OpenAI doesn't have persistent ChatSession like Google AI, so we still
    need to pass conversation_history each time. However, chat_id can be used
    for caching or other optimizations in the future.
    """
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
    
    # Build messages array
    messages = []
    
    # Add system message
    system_content = system_prompt if system_prompt else "You are a helpful assistant."
    if context:
        system_content = f"{system_content}\n\nContext: {context}"
    messages.append({"role": "system", "content": system_content})
    
    # Add conversation history
    if conversation_history:
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # OpenAI uses "assistant" instead of "model"
            if role == "model":
                role = "assistant"
            messages.append({"role": role, "content": content})
    
    # Add current user message
    current_message = user_message if user_message else prompt
    if current_message:
        messages.append({"role": "user", "content": current_message})
    
    # Prepare generation parameters
    generation_params = {
        'model': model_name,
        'messages': messages,
        'temperature': kwargs.get('temperature', 0.7),
        'max_tokens': kwargs.get('max_tokens', 2000),
    }
    
    # Add top_p if provided (OpenAI supports top_p)
    if 'top_p' in kwargs:
        generation_params['top_p'] = kwargs['top_p']
    
    # Generate response
    response = client.chat.completions.create(**generation_params)
    
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

