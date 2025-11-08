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

# --- Function for correct resource handling in PyInstaller ---
def resource_path(relative_path):
    """Get correct path to resources for PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates temporary folder in _MEIPASS
        base_path = sys._MEIPASS
    else:
        # Normal mode - use current directory
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Import for vector database search ---
try:
    from vector_db.client import search_chats
except ImportError:
    search_chats = None

# --- Configuration ---
# Load .env file (use dotenv_values for reliability)
from dotenv import dotenv_values

# Function to get base directory (with PyInstaller support)
def get_base_directory():
    """Get base directory for searching .env file."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller: search next to exe file
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if 'core' in base_dir:
                base_dir = os.path.dirname(base_dir)
            return base_dir
    else:
        return os.getcwd()

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
            print(f"--- WARNING: GOOGLE_API_KEY not found. Check .env file ---")
        else:
            print(f"--- Google AI Client Configured Successfully ---")
    elif provider == AIProvider.OPENAI:
        api_key = provider_config.get('openai_api_key')
        if not api_key:
            print(f"--- WARNING: OPENAI_API_KEY not found. Check .env file ---")
        else:
            print(f"--- OpenAI Client Configured Successfully ---")
    else:
        print(f"--- AI Provider: {provider_name} ---")
        
except Exception as e:
    print(f"--- CRITICAL: Failed to configure AI provider! Error: {e} ---")

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
                    return content
        
        return None
    except Exception as e:
        print(f"--- Warning: Failed to load prompt file '{file_path}': {e} ---")
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
    """Load archetypes from YAML file with caching."""
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
            raise FileNotFoundError("archetypes.yaml not found. Make sure the file is next to the exe file or in the project.")
        
        with open(archetypes_path, "r", encoding="utf-8") as f:
            archetype_cache = yaml.safe_load(f)
        
        # For each archetype, build full prompt
        for archetype_name, config in archetype_cache.items():
            if isinstance(config, dict):
                # Build multi-stage prompt
                full_prompt = build_multistage_prompt(config)
                if full_prompt:
                    config["_full_prompt"] = full_prompt  # Cache built prompt
        
        print("--- Archetypes loaded successfully ---")
    except Exception as e:
        print(f"--- CRITICAL: Failed to load archetypes! Error: {e} ---")
        archetype_cache = {}
    return archetype_cache

def log_interaction(archetype_name, user_text, final_prompt, response):
    """Save full interaction information to file."""
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
    print(f"--- Interaction saved to {filename} ---")

def process_with_archetype(text: str, archetype_name: str, archetypes: dict):
    """
    Form prompt, pull relevant context from vector database,
    select appropriate model, generate response and log result.
    """
    if not text or not archetype_name:
        return {"error": "Text and archetype must be specified."}

    archetype_config = archetypes.get(archetype_name)
    if not archetype_config:
        return {"error": f"Archetype '{archetype_name}' not found."}

    model_name = archetype_config.get("model_name")
    if not model_name:
        return {"error": f"Model name not specified for archetype '{archetype_name}'."}

    # Use assembled multi-stage prompt or assemble on the fly
    if "_full_prompt" in archetype_config:
        system_prompt = archetype_config["_full_prompt"]
    else:
        # If not assembled during loading, assemble now
        system_prompt = build_multistage_prompt(archetype_config) or archetype_config.get("prompt", "")

    # --- Add relevant context from vector database ---
    context = ""
    if search_chats:
        similar_chats = search_chats(text, n_results=2)
        if similar_chats:
            context = "\n\n".join([f"Context from previous chat:\n{c['text']}" for c in similar_chats])

    full_prompt = f"{system_prompt}\n\n{context}\n\nUser query:\n{text}"

    try:
        # Normalize model name for current provider
        provider = get_current_provider()
        normalized_model = normalize_model_name(model_name, provider)
        
        # Generate response through current provider
        model_response = generate_response(normalized_model, full_prompt)
        log_interaction(archetype_name, text, full_prompt, model_response)
        return {"response": model_response}
    except ValueError as e:
        error_message = f"Configuration error: {e}"
        print(error_message)
        return {"error": error_message}
    except Exception as e:
        provider_name = get_current_provider().value
        error_message = f"Error calling {provider_name}: {e}"
        print(error_message)
        return {"error": error_message}