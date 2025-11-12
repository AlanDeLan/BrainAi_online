import os
import sys
import yaml
import datetime
import json
from dotenv import load_dotenv

# --- Import for AI providers ---
from core.ai_providers import (
    generate_response, 
    get_current_provider, 
    get_provider_config,
    normalize_model_name,
    AIProvider
)

# --- Import logging and validation ---
from core.logger import logger
from core.validation import validate_archetypes_yaml, validate_archetypes_config
from core.utils import resource_path, get_base_directory

# --- Import for vector database search ---
try:
    from vector_db.client import search_chats
except ImportError:
    search_chats = None

# --- Configuration ---
# Load .env file (use dotenv_values for reliability)
from dotenv import dotenv_values

# Search for .env in various locations (with PyInstaller support)
base_dir = get_base_directory()
env_paths = [
    os.path.join(base_dir, '.env'),  # Next to exe/script (priority for PyInstaller)
    os.path.join(os.path.dirname(__file__), '..', '.env'),  # Near core/logic.py
    os.path.join(os.path.dirname(__file__), '..', '..', '.env'),  # In project root
    '.env',  # Current directory
]

env_values = None
for env_path in env_paths:
    abs_path = os.path.abspath(env_path)
    if os.path.exists(abs_path):
        try:
            env_values = dotenv_values(abs_path)
            if 'GOOGLE_API_KEY' in env_values:
                break
        except Exception:
            continue

# If not found via dotenv_values, try load_dotenv
if not env_values or 'GOOGLE_API_KEY' not in env_values:
    # Also try loading from base directory
    load_dotenv(os.path.join(base_dir, '.env'), override=True)
    load_dotenv(override=True)
    env_values = {'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY')}

# Initialize AI provider
try:
    from core.ai_providers import load_provider_config
    provider, provider_config = load_provider_config()
    provider_name = provider.value
    
    # Check for API key for current provider
    if provider == AIProvider.GOOGLE_AI:
        api_key = provider_config.get('google_api_key')
        if not api_key:
            logger.warning("GOOGLE_API_KEY not found. Check .env file")
        else:
            logger.info("Google AI Client Configured Successfully")
    elif provider == AIProvider.OPENAI:
        api_key = provider_config.get('openai_api_key')
        if not api_key:
            logger.warning("OPENAI_API_KEY not found. Check .env file")
        else:
            logger.info("OpenAI Client Configured Successfully")
    else:
        logger.info(f"AI Provider: {provider_name}")
        
except Exception as e:
    logger.critical(f"Failed to configure AI provider! Error: {e}", exc_info=True)

# For history, use directory next to exe file (not in _MEIPASS)
if hasattr(sys, '_MEIPASS'):
    # PyInstaller: use directory where exe file is located
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if 'core' in base_dir:
            base_dir = os.path.dirname(base_dir)
else:
    base_dir = os.getcwd()

HISTORY_DIR = os.path.join(base_dir, "history")
os.makedirs(HISTORY_DIR, exist_ok=True)

archetype_cache = None

def reload_archetypes():
    """Reload archetypes from file (clear cache)."""
    global archetype_cache
    archetype_cache = None
    return load_archetypes()

def load_prompt_file(file_path):
    """Load prompt from file."""
    if not file_path:
        return None
    
    try:
        # Search in various locations (with PyInstaller support)
        possible_paths = [
            resource_path(file_path),  # Via resource_path for PyInstaller
            file_path,  # Absolute or relative path
            resource_path(os.path.join("prompts", file_path)),  # In prompts folder
            os.path.join("prompts", file_path),  # In prompts folder (normal mode)
            os.path.join(os.path.dirname(__file__), "..", "prompts", file_path),
            os.path.join(os.path.dirname(__file__), "..", file_path),
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    logger.debug(f"Loaded prompt file: {path} ({len(content)} chars)")
                    return content
        
        logger.warning(f"Prompt file not found: {file_path}")
        return None
    except Exception as e:
        logger.warning(f"Failed to load prompt file '{file_path}': {e}", exc_info=True)
        return None

def build_multistage_prompt(archetype_config):
    """
    Build multi-stage prompt from archetype configuration.
    Supports:
    - prompt: direct text
    - prompt_file: path to file with main prompt
    - additional_prompts: list of additional prompts (files or text)
    """
    prompt_parts = []
    
    # 1. Main prompt (from file or direct text)
    base_prompt = None
    
    # First check prompt_file
    if "prompt_file" in archetype_config:
        base_prompt = load_prompt_file(archetype_config["prompt_file"])
    
    # If not found in file, use prompt
    if not base_prompt:
        base_prompt = archetype_config.get("prompt", "")
    
    if base_prompt:
        prompt_parts.append(base_prompt)
    
    # 2. Additional prompts (can be files or text)
    additional_prompts = archetype_config.get("additional_prompts", [])
    if isinstance(additional_prompts, str):
        # If single string, make it a list
        additional_prompts = [additional_prompts]
    
    for add_prompt in additional_prompts:
        if not add_prompt:
            continue
        
        # Check if it's a file (ends with .txt, .md, etc.)
        if isinstance(add_prompt, str) and any(add_prompt.endswith(ext) for ext in ['.txt', '.md']):
            loaded = load_prompt_file(add_prompt)
            if loaded:
                prompt_parts.append(loaded)
        else:
            # It's text
            prompt_parts.append(str(add_prompt))
    
    # Join all parts
    return "\n\n".join(filter(None, prompt_parts))

def load_archetypes():
    """Load archetypes from YAML file with caching and validation."""
    global archetype_cache
    if archetype_cache is not None:
        return archetype_cache
    try:
        # Search for archetypes.yaml in various locations
        # Priority: 1) next to exe, 2) in PyInstaller resources, 3) in project
        archetypes_path = None
        
        # First search next to exe file (for editing)
        base_dir = get_base_directory()
        exe_local_path = os.path.join(base_dir, "archetypes.yaml")
        if os.path.exists(exe_local_path):
            archetypes_path = exe_local_path
        else:
            # Then search in PyInstaller resources
            possible_paths = [
                resource_path("archetypes.yaml"),  # In PyInstaller resources
                "archetypes.yaml",  # Current directory
                os.path.join(os.path.dirname(__file__), "..", "archetypes.yaml"),  # In project
            ]
            
            for path in possible_paths:
                if path and os.path.exists(path):
                    archetypes_path = path
                    break
        
        if not archetypes_path:
            error_msg = "archetypes.yaml not found. Make sure the file is next to the exe file or in the project."
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Validate YAML file
        is_valid, errors, warnings = validate_archetypes_yaml(archetypes_path)
        if not is_valid:
            error_msg = f"Validation failed for archetypes.yaml: {', '.join(errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if warnings:
            for warning in warnings:
                logger.warning(f"archetypes.yaml: {warning}")
        
        with open(archetypes_path, "r", encoding="utf-8") as f:
            archetype_cache = yaml.safe_load(f)
        
        # Validate configuration structure
        config_valid, config_errors = validate_archetypes_config(archetype_cache)
        if not config_valid:
            error_msg = f"Configuration validation failed: {', '.join(config_errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # For each archetype, build full prompt
        for archetype_name, config in archetype_cache.items():
            if isinstance(config, dict):
                # Build multi-stage prompt
                full_prompt = build_multistage_prompt(config)
                if full_prompt:
                    config["_full_prompt"] = full_prompt  # Cache built prompt
                    logger.debug(f"Built prompt for archetype '{archetype_name}' ({len(full_prompt)} chars)")
        
        logger.info(f"Archetypes loaded successfully: {len(archetype_cache)} archetypes")
    except FileNotFoundError:
        logger.error("archetypes.yaml not found", exc_info=True)
        archetype_cache = {}
        raise
    except (yaml.YAMLError, ValueError) as e:
        logger.error(f"Failed to load archetypes: {e}", exc_info=True)
        archetype_cache = {}
        raise
    except Exception as e:
        logger.critical(f"Unexpected error loading archetypes: {e}", exc_info=True)
        archetype_cache = {}
        raise
    return archetype_cache

def log_interaction(archetype_name, user_text, final_prompt, response):
    """Save full interaction information to file."""
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_archetype = "".join(c for c in archetype_name if c.isalnum() or c in ('_', '-'))
        filename = os.path.join(HISTORY_DIR, f"{timestamp}_{safe_archetype}.json")
        log_data = {
            "timestamp": timestamp,
            "archetype": archetype_name,
            "user_input": user_text,
            "full_prompt_sent_to_model": final_prompt,
            "model_response": response,
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=4)
        logger.debug(f"Interaction saved to {filename}")
    except Exception as e:
        logger.error(f"Failed to save interaction log: {e}", exc_info=True)

def process_with_archetype(text: str, archetype_name: str, archetypes: dict, chat_history=None, chat_id=None, **kwargs):
    """
    Form prompt, pull relevant context from vector database,
    select appropriate model, generate response and log result.
    
    Args:
        text: User input text
        archetype_name: Name of archetype to use
        archetypes: Dictionary of archetypes
        chat_history: List of previous messages (deprecated - used for file-based history only)
        chat_id: ID of current chat for vector database search
        **kwargs: Additional parameters (temperature, max_tokens, top_p, top_k)
    """
    if chat_history is None:
        chat_history = []
    logger.debug(f"Processing request for archetype '{archetype_name}', chat_id={chat_id}")
    
    if not text or not archetype_name:
        error_msg = "Text and archetype must be specified."
        logger.warning(error_msg)
        return {"error": error_msg}

    archetype_config = archetypes.get(archetype_name)
    if not archetype_config:
        error_msg = f"Archetype '{archetype_name}' not found."
        logger.warning(error_msg)
        return {"error": error_msg}

    model_name = archetype_config.get("model_name")
    if not model_name:
        error_msg = f"Model name not specified for archetype '{archetype_name}'."
        logger.error(error_msg)
        return {"error": error_msg}

    # Use assembled multi-stage prompt or assemble on the fly
    if "_full_prompt" in archetype_config:
        system_prompt = archetype_config["_full_prompt"]
    else:
        # If not assembled during loading, assemble now
        system_prompt = build_multistage_prompt(archetype_config) or archetype_config.get("prompt", "")

    # --- Smart context retrieval strategy ---
    # 1. Search for relevant messages in current chat via vector DB (for continuity)
    # 2. Search for relevant chats from entire database (for broader context)
    # 3. Use sliding window for last N messages (to maintain immediate context)
    # 4. Combine all for optimal context without token explosion
    
    context = ""
    context_messages = []
    context_chats = []
    recent_messages = []
    
    # Maximum number of recent messages to include (sliding window)
    MAX_RECENT_MESSAGES = 3  # Last 3 exchanges (6 messages: 3 user + 3 assistant)
    
    # Try to import vector DB functions
    try:
        from vector_db.client import search_chat_messages, search_chats, is_vector_db_available
        
        if is_vector_db_available():
            # 1. Search for relevant messages in CURRENT chat (for continuity)
            if chat_id:
                try:
                    relevant_messages = search_chat_messages(chat_id, text, n_results=3)
                    if relevant_messages:
                        # Sort by score (distance) - lower is better
                        relevant_messages.sort(key=lambda x: x.get("score", float("inf")))
                        context_messages = relevant_messages
                        logger.debug(f"Found {len(relevant_messages)} relevant messages in current chat")
                except Exception as e:
                    logger.warning(f"Failed to search messages in current chat: {e}")
            
            # 2. Search for relevant chats from ENTIRE database (for broader context)
            # This includes both chat conversations and uploaded files
            try:
                # Search across all chats and files (excluding current chat if chat_id exists)
                relevant_chats = search_chats(text, n_results=3)
                if relevant_chats:
                    # Filter out current chat if it appears in results
                    if chat_id:
                        relevant_chats = [c for c in relevant_chats if c.get("chat_id") != chat_id]
                    
                    # Sort by score (distance) - lower is better
                    relevant_chats.sort(key=lambda x: x.get("score", float("inf")))
                    context_chats = relevant_chats[:2]  # Take top 2 most relevant
                    logger.debug(f"Found {len(context_chats)} relevant chats/files from entire database")
            except Exception as e:
                logger.warning(f"Failed to search chats in database: {e}")
            
            # Combine context from current chat and other chats
            context_parts = []
            
            # Add context from current chat
            if context_messages:
                current_chat_parts = []
                for msg in context_messages[:3]:  # Top 3 from current chat
                    role_label = "User" if msg.get("role") == "user" else "Assistant"
                    current_chat_parts.append(f"{role_label}: {msg.get('text', '')}")
                if current_chat_parts:
                    context_parts.append("Relevant context from this conversation:\n" + "\n\n".join(current_chat_parts))
            
            # Add context from other chats
            if context_chats:
                other_chats_parts = []
                for chat in context_chats:
                    chat_text = chat.get("text", "")
                    # Truncate long chats to avoid token explosion
                    if len(chat_text) > 500:
                        chat_text = chat_text[:500] + "..."
                    other_chats_parts.append(f"From previous chat ({chat.get('chat_id', 'unknown')}):\n{chat_text}")
                if other_chats_parts:
                    context_parts.append("Relevant context from previous conversations:\n" + "\n\n".join(other_chats_parts))
            
            if context_parts:
                context = "\n\n".join(context_parts)
                logger.debug(f"Combined context: {len(context_messages)} messages from current chat, {len(context_chats)} chats from database")
    except ImportError:
        # Vector DB not available, skip context search
        pass
    
    # Get recent messages for sliding window (from file-based history)
    if chat_history and len(chat_history) > 0:
        # Take last MAX_RECENT_MESSAGES exchanges
        recent_history = chat_history[-MAX_RECENT_MESSAGES:]
        recent_messages = []
        for entry in recent_history:
            # Convert to conversation format
            if "user_input" in entry:
                recent_messages.append({
                    "role": "user",
                    "content": entry["user_input"]
                })
            if "model_response" in entry:
                recent_messages.append({
                    "role": "model",
                    "content": entry["model_response"]
                })
        logger.debug(f"Using {len(recent_messages)} recent messages for sliding window")

    full_prompt = f"{system_prompt}\n\n{context}\n\nUser query:\n{text}" if context else f"{system_prompt}\n\nUser query:\n{text}"
    logger.debug(f"Full prompt length: {len(full_prompt)} characters")

    # Get model parameters: use kwargs if provided, otherwise use archetype config, otherwise use defaults
    # Use 'in' check to allow 0.0 values (which would be False with 'or')
    model_params = {
        'temperature': kwargs.get('temperature') if 'temperature' in kwargs else archetype_config.get('temperature', 0.7),
        'max_tokens': kwargs.get('max_tokens') if 'max_tokens' in kwargs else archetype_config.get('max_tokens', 2000),
    }
    
    # Add optional parameters
    if 'top_p' in kwargs:
        model_params['top_p'] = kwargs['top_p']
    elif 'top_p' in archetype_config:
        model_params['top_p'] = archetype_config['top_p']
    
    if 'top_k' in kwargs:
        model_params['top_k'] = kwargs['top_k']
    elif 'top_k' in archetype_config:
        model_params['top_k'] = archetype_config['top_k']
    
    logger.debug(f"Model parameters: {model_params}")

    try:
        # Normalize model name for current provider
        provider = get_current_provider()
        normalized_model = normalize_model_name(model_name, provider)
        logger.debug(f"Using model: {normalized_model} (provider: {provider.value})")
        
        # Initialize cache_key variable
        cache_key = None
        
        # Check cache first
        # Note: We don't cache when there's context from vector DB or conversation history
        # Cache only works for stateless queries
        if not context_messages and not context_chats and not recent_messages:
            try:
                from core.cache import generate_cache_key, get_cached_response, cache_response, DEFAULT_TTL
                
                # Generate cache key using full prompt (for stateless queries)
                cache_key = generate_cache_key(
                    prompt=full_prompt,
                    model_name=normalized_model,
                    temperature=model_params.get('temperature'),
                    max_tokens=model_params.get('max_tokens'),
                    top_p=model_params.get('top_p'),
                    top_k=model_params.get('top_k')
                )
                
                # Try to get cached response
                cached_response = get_cached_response(cache_key, ttl=DEFAULT_TTL)
                if cached_response:
                    logger.info(f"Cache hit for archetype '{archetype_name}' ({len(cached_response)} chars)")
                    return {"response": cached_response, "cached": True}
            except Exception as cache_error:
                # If caching fails, continue without cache
                logger.debug(f"Cache check failed: {cache_error}")
        
        # Use sliding window: only last N messages + relevant context from vector DB
        # This prevents token explosion while maintaining context
        conversation_history = recent_messages if recent_messages else None
        
        # Generate response through current provider with parameters and context
        # Pass chat_id to enable ChatSession reuse (prevents token explosion)
        model_response = generate_response(
            normalized_model, 
            system_prompt=system_prompt,
            user_message=text,
            context=context,
            conversation_history=conversation_history,
            chat_id=chat_id,
            **model_params
        )
        logger.info(f"Successfully generated response for archetype '{archetype_name}' ({len(model_response)} chars)")
        
        # Cache the response (if cache_key was generated)
        if cache_key:
            try:
                from core.cache import cache_response, DEFAULT_TTL
                cache_response(cache_key, model_response, ttl=DEFAULT_TTL)
            except Exception as cache_error:
                logger.debug(f"Cache save failed: {cache_error}")
        
        # Note: Interaction logging is handled in main.py to avoid duplicate files
        # log_interaction is kept for backward compatibility but not called here
        return {"response": model_response, "cached": False}
    except ValueError as e:
        error_message = f"Configuration error: {e}"
        logger.error(error_message, exc_info=True)
        return {"error": error_message}
    except Exception as e:
        provider_name = get_current_provider().value
        error_message = f"Error calling {provider_name}: {e}"
        logger.error(error_message, exc_info=True)
        return {"error": error_message}