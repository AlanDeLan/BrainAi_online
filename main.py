import os
import sys
import json
import threading
from typing import List, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from core.logic import load_archetypes, process_with_archetype, reload_archetypes
from core.ai_providers import (
    get_current_provider, 
    get_provider_config, 
    set_provider,
    AIProvider,
    get_supported_models,
    load_provider_config
)
from core.logger import logger
from core.validation import validate_archetypes_config, validate_env_file
from core.i18n import get_user_language, t, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from core.monitoring import (
    increment_counter, record_timer, record_metric,
    get_metrics_summary, TimerContext, reset_metrics
)
from conferences.rada import router as rada_router
import aiofiles
import yaml
import shutil
from datetime import datetime

# Global variable to store server object (for graceful shutdown)
_server_instance: Optional[object] = None
_shutdown_event: Optional[threading.Event] = None

def set_server_instance(server):
    """Set server instance for graceful shutdown."""
    global _server_instance
    _server_instance = server

def set_shutdown_event(event):
    """Set shutdown event to signal completion."""
    global _shutdown_event
    _shutdown_event = event

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

app = FastAPI(
    title="Local Brain",
    description="Intelligent local AI assistant with multiple agents and vector database support",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI at /docs
    redoc_url="/redoc",  # ReDoc at /redoc
    openapi_url="/openapi.json"  # OpenAPI schema at /openapi.json
)

# Setup logging
logger.info("Starting Local Brain application")

# Use resource_path for static files and templates
static_dir = resource_path("static")
templates_dir = resource_path("templates")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Include router for RADA mode
app.include_router(rada_router)

# For history, use directory next to exe file (not in _MEIPASS)
if hasattr(sys, '_MEIPASS'):
    # PyInstaller: use directory where exe file is located
    if getattr(sys, 'frozen', False):
        # Executable file
        base_dir = os.path.dirname(sys.executable)
    else:
        # Script
        base_dir = os.path.dirname(os.path.abspath(__file__))
else:
    # Normal mode
    base_dir = os.getcwd()

HISTORY_DIR = os.path.join(base_dir, "history")
os.makedirs(HISTORY_DIR, exist_ok=True)

archetypes = load_archetypes()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Main page with chat interface."""
    language = get_user_language(request)
    increment_counter("page_views")
    return templates.TemplateResponse(
        "index.html", {
            "request": request,
            "archetypes": archetypes,
            "language": language,
            "supported_languages": SUPPORTED_LANGUAGES
        }
    )

def get_chat_file(chat_id):
    return os.path.join(HISTORY_DIR, f"{chat_id}.json")

@app.post("/process")
async def process_text(request: Request):
    """Process text with selected archetype."""
    with TimerContext("process_request"):
        try:
            increment_counter("api_requests")
            data = await request.json()
            text = data.get("text")
            archetype = data.get("archetype")
            remember = data.get("remember", True)
            chat_id = data.get("chat_id")
            
            logger.info(f"Processing request: archetype={archetype}, chat_id={chat_id}, remember={remember}")
            increment_counter(f"archetype_{archetype}")
            
            if not text or not archetype:
                error_msg = "Text and archetype are required"
                logger.warning(error_msg)
                increment_counter("api_errors")
                raise HTTPException(status_code=400, detail=error_msg)
            
            result = process_with_archetype(
                text=text,
                archetype_name=archetype,
                archetypes=archetypes
            )
            
            if "error" in result:
                logger.error(f"Error processing request: {result['error']}")
                increment_counter("api_errors")
                raise HTTPException(status_code=500, detail=result["error"])
            
            # --- Save chat as array of messages in single file ---
            if remember and chat_id:
                try:
                    filepath = get_chat_file(chat_id)
                    if os.path.exists(filepath):
                        try:
                            async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
                                content = await f.read()
                                try:
                                    history = json.loads(content)
                                except json.JSONDecodeError as e:
                                    logger.warning(f"Failed to parse history file {filepath}: {e}, creating new history")
                                    history = []
                        except Exception as e:
                            logger.warning(f"Failed to read history file {filepath}: {e}, creating new history")
                            history = []
                    else:
                        history = []
                    
                    history.append({
                        "user_input": text,
                        "archetype": archetype,
                        "model_response": result.get("response", "")
                    })
                    
                    try:
                        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                            await f.write(json.dumps(history, ensure_ascii=False, indent=2))
                        logger.debug(f"Chat history saved to {filepath}")
                    except Exception as e:
                        logger.error(f"Failed to save chat history to {filepath}: {e}", exc_info=True)
                        # Don't fail the request if history save fails
                    
                    # --- Save to vector database ---
                    try:
                        from vector_db.client import update_chat
                        import datetime
                        
                        # Prepare chat text for vector database
                        chat_text_parts = []
                        for msg in history:
                            chat_text_parts.append(f"User: {msg.get('user_input', '')}")
                            chat_text_parts.append(f"{msg.get('archetype', 'Assistant')}: {msg.get('model_response', '')}")
                        chat_text = "\n".join(chat_text_parts)
                        
                        # Get timestamp from chat_id or use current time
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        if "_" in chat_id:
                            # Try to extract timestamp from chat_id
                            try:
                                timestamp = "_".join(chat_id.split("_")[:3])  # First 3 parts are date_time
                            except Exception:
                                pass
                        
                        metadata = {
                            "chat_id": chat_id,
                            "archetypes": archetype,
                            "timestamp": timestamp,
                            "topic": text[:100] if text else ""  # First 100 chars as topic
                        }
                        
                        # Update or create chat in vector database
                        update_chat(chat_id, chat_text, metadata)
                        logger.info(f"Chat saved to vector database: {chat_id}")
                        increment_counter("vector_db_saves")
                    except Exception as e:
                        # Log error but don't fail the request
                        logger.warning(f"Failed to save to vector database: {e}", exc_info=True)
                        increment_counter("vector_db_errors")
                except Exception as e:
                    logger.error(f"Unexpected error saving chat: {e}", exc_info=True)
                    # Don't fail the request if chat save fails
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in process_text: {e}", exc_info=True)
            increment_counter("api_errors")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/history", response_model=List[str])
async def get_history_list():
    try:
        files = [f for f in os.listdir(HISTORY_DIR) if f.endswith('.json')]
        files.sort(reverse=True)
        return files
    except FileNotFoundError:
        return []

@app.get("/history/{filename}")
async def get_history_file(filename: str):
    if "/" in filename or "\\" in filename or ".." in filename:
        return JSONResponse(status_code=400, content={"error": "Invalid filename"})
    try:
        filepath = os.path.join(HISTORY_DIR, filename)
        if not os.path.abspath(filepath).startswith(os.path.abspath(HISTORY_DIR)):
            return JSONResponse(status_code=403, content={"error": "Access denied"})
        async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
        return JSONResponse(content=data)
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"error": "File not found"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/history/{filename}")
async def delete_history_file(filename: str):
    if "/" in filename or "\\" in filename or ".." in filename:
        return JSONResponse(status_code=400, content={"error": "Invalid filename"})
    filepath = os.path.join(HISTORY_DIR, filename)
    if not os.path.exists(filepath):
        return JSONResponse(status_code=404, content={"error": "File not found"})
    try:
        os.remove(filepath)
        return JSONResponse(content={"status": "deleted"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/favicon.ico")
async def favicon():
    favicon_path = resource_path("static/favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    else:
        raise HTTPException(status_code=404, detail="Favicon not found")

def get_base_directory():
    """Get base directory (next to exe or project root) with PyInstaller support."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller: search next to exe file
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))
    else:
        return os.getcwd()

def get_archetypes_yaml_path():
    """Get path to archetypes.yaml with PyInstaller support."""
    base_dir = get_base_directory()
    return os.path.join(base_dir, "archetypes.yaml")

def get_prompts_directory():
    """Get path to prompts directory with PyInstaller support."""
    base_dir = get_base_directory()
    prompts_dir = os.path.join(base_dir, "prompts")
    # Create directory if it doesn't exist
    os.makedirs(prompts_dir, exist_ok=True)
    return prompts_dir

@app.get("/api/archetypes")
async def get_archetypes_config():
    """Get current agent configuration with prompt file contents for editing."""
    try:
        from core.logic import load_prompt_file
        
        logger.debug("Loading archetypes configuration")
        archetypes_path = get_archetypes_yaml_path()
        
        if not os.path.exists(archetypes_path):
            error_msg = f"archetypes.yaml not found at {archetypes_path}"
            logger.error(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)
        
        with open(archetypes_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        if config is None:
            error_msg = "archetypes.yaml is empty or invalid"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Load prompt file contents for editing
        config_with_contents = {}
        for key, archetype_config in config.items():
            if not isinstance(archetype_config, dict):
                config_with_contents[key] = archetype_config
                continue
            
            # Create a copy
            config_copy = archetype_config.copy()
            
            # Load prompt file content if exists for editing
            # We add it as a separate field for the UI, but keep prompt_file as the source of truth
            if "prompt_file" in config_copy:
                prompt_file_path = config_copy["prompt_file"]
                prompt_content = load_prompt_file(prompt_file_path)
                if prompt_content:
                    # Add prompt content for editing (temporary field for UI)
                    # The prompt_file remains the source of truth in YAML
                    config_copy["_prompt_content"] = prompt_content  # Temporary field, not saved to YAML
            
            # Load additional prompt file contents for editing
            # Keep file paths but also provide content for UI editing
            if "additional_prompts" in config_copy:
                additional_prompts = config_copy["additional_prompts"]
                if isinstance(additional_prompts, str):
                    additional_prompts = [additional_prompts]
                
                # Store both file paths and content
                loaded_additional = []
                additional_contents = []
                for add_prompt in additional_prompts:
                    if not add_prompt:
                        continue
                    # Check if it's a file path
                    if isinstance(add_prompt, str) and any(add_prompt.endswith(ext) for ext in ['.txt', '.md']):
                        # Keep the file path
                        loaded_additional.append(add_prompt)
                        # Load content for editing
                        content = load_prompt_file(add_prompt)
                        additional_contents.append(content if content else "")
                    else:
                        # It's already text (shouldn't happen in clean config, but handle it)
                        loaded_additional.append(add_prompt)
                        additional_contents.append(add_prompt)
                
                if loaded_additional:
                    # Keep file paths in additional_prompts
                    config_copy["additional_prompts"] = loaded_additional
                    # Store content separately for UI (temporary, not saved to YAML)
                    config_copy["_additional_prompts_content"] = additional_contents
            
            config_with_contents[key] = config_copy
        
        logger.info(f"Archetypes configuration loaded: {len(config_with_contents)} archetypes")
        return JSONResponse(content={"archetypes": config_with_contents})
    except HTTPException:
        raise
    except yaml.YAMLError as e:
        error_msg = f"Invalid YAML syntax in archetypes.yaml: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Error reading configuration: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/archetypes")
async def save_archetypes_config(request: Request):
    """Save agent configuration. Automatically creates prompt files for text prompts."""
    try:
        from core.logic import load_prompt_file
        
        data = await request.json()
        archetypes_config = data.get("archetypes", {})
        prompts_dir = get_prompts_directory()
        
        logger.info(f"Saving archetypes configuration: {len(archetypes_config)} archetypes")
        
        # Validate configuration
        is_valid, validation_errors = validate_archetypes_config(archetypes_config)
        if not is_valid:
            error_msg = f"Validation failed: {', '.join(validation_errors)}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Load original config to preserve file paths
        archetypes_path = get_archetypes_yaml_path()
        original_config = {}
        if os.path.exists(archetypes_path):
            with open(archetypes_path, "r", encoding="utf-8") as f:
                original_config = yaml.safe_load(f) or {}
        
        # Process each archetype: convert text prompts to files
        processed_config = {}
        for archetype_key, archetype_config in archetypes_config.items():
            if not isinstance(archetype_config, dict):
                error_msg = f"Invalid configuration for agent '{archetype_key}'"
                logger.error(error_msg)
                raise HTTPException(status_code=400, detail=error_msg)
            
            # Validate required fields
            if "name" not in archetype_config:
                error_msg = f"Agent '{archetype_key}' must have 'name' field"
                logger.error(error_msg)
                raise HTTPException(status_code=400, detail=error_msg)
            if "model_name" not in archetype_config:
                error_msg = f"Agent '{archetype_key}' must have 'model_name' field"
                logger.error(error_msg)
                raise HTTPException(status_code=400, detail=error_msg)
            
            # Create a copy of config to modify
            new_config = archetype_config.copy()
            
            # Process main prompt: always save to file
            # If prompt_file exists, update that file; otherwise create new file
            prompt_text = new_config.get("prompt", "")
            original_prompt_file = new_config.get("prompt_file")
            
            if prompt_text:
                # Determine file path
                if original_prompt_file:
                    # Use existing file path
                    prompt_file_path = original_prompt_file
                else:
                    # Create new file
                    prompt_filename = f"{archetype_key}_base.txt"
                    prompt_file_path = f"prompts/{prompt_filename}"
                
                # Extract file name (remove "prompts/" prefix if present)
                if prompt_file_path.startswith("prompts/"):
                    file_name = prompt_file_path[8:]
                else:
                    file_name = prompt_file_path
                
                file_full_path = os.path.join(prompts_dir, file_name)
                # Ensure directory exists
                os.makedirs(os.path.dirname(file_full_path) if os.path.dirname(file_full_path) else prompts_dir, exist_ok=True)
                
                # Save prompt to file
                with open(file_full_path, "w", encoding="utf-8") as pf:
                    pf.write(prompt_text)
                
                # Always use prompt_file in YAML (never prompt)
                new_config["prompt_file"] = prompt_file_path
                # Remove prompt field (it should not be in YAML)
                new_config.pop("prompt", None)
            elif "prompt_file" not in new_config:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Agent '{archetype_key}' must have prompt content"
                )
            else:
                # Only prompt_file, no prompt content - keep as is
                # But remove prompt field if it exists
                new_config.pop("prompt", None)
            
            # Process additional prompts: convert text prompts to files
            if "additional_prompts" in new_config:
                additional_prompts = new_config["additional_prompts"]
                if isinstance(additional_prompts, str):
                    additional_prompts = [additional_prompts]
                
                # Get original file paths from original config
                original_archetype = original_config.get(archetype_key, {})
                original_additional = original_archetype.get("additional_prompts", [])
                if isinstance(original_additional, str):
                    original_additional = [original_additional]
                
                processed_additional = []
                for idx, add_prompt in enumerate(additional_prompts):
                    if not add_prompt:
                        continue
                    
                    # Check if it's a file path (unlikely, but handle it)
                    if isinstance(add_prompt, str) and any(add_prompt.endswith(ext) for ext in ['.txt', '.md']) and not os.path.isabs(add_prompt):
                        processed_additional.append(add_prompt)
                        continue
                    
                    # Get original file path for this index if it exists
                    original_file_path = None
                    if idx < len(original_additional):
                        orig = original_additional[idx]
                        if isinstance(orig, str) and any(orig.endswith(ext) for ext in ['.txt', '.md']) and not os.path.isabs(orig):
                            original_file_path = orig
                    
                    # Determine file path: use original if exists, otherwise create new
                    if original_file_path:
                        file_path = original_file_path
                    else:
                        # Create new file name
                        add_prompt_filename = f"{archetype_key}_additional_{idx + 1}.txt"
                        file_path = f"prompts/{add_prompt_filename}"
                    
                    # Extract file name (remove "prompts/" prefix if present)
                    if file_path.startswith("prompts/"):
                        file_name = file_path[8:]
                    else:
                        file_name = file_path
                    
                    file_full_path = os.path.join(prompts_dir, file_name)
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(file_full_path) if os.path.dirname(file_full_path) else prompts_dir, exist_ok=True)
                    
                    # Save content to file
                    with open(file_full_path, "w", encoding="utf-8") as apf:
                        apf.write(str(add_prompt))
                    
                    # Use file path
                    processed_additional.append(file_path)
                
                if processed_additional:
                    new_config["additional_prompts"] = processed_additional
                else:
                    # Remove empty additional_prompts
                    new_config.pop("additional_prompts", None)
            
            processed_config[archetype_key] = new_config
        
        # Get path to archetypes.yaml
        archetypes_path = get_archetypes_yaml_path()
        backup_path = archetypes_path + ".backup"
        
        # Create backup
        try:
            if os.path.exists(archetypes_path):
                shutil.copy(archetypes_path, backup_path)
        except Exception:
            pass  # If backup creation failed, continue
        
        # Save new configuration
        with open(archetypes_path, "w", encoding="utf-8") as f:
            # Write header with comments
            f.write("# Configuration of archetypes (agents)\n")
            f.write("# Adding and editing agents is done through this file\n")
            f.write("# Use:\n")
            f.write("# 1. prompt_file: path to file with main prompt (e.g., prompts/sofiya_base.txt)\n")
            f.write("# 2. additional_prompts: list of additional prompts (files .txt/.md)\n")
            f.write("#\n")
            f.write("# Maximum 3 agents for RADA mode\n")
            f.write("#\n")
            f.write("# NOTE: All prompts must be in separate files in the prompts/ directory.\n")
            f.write("# When creating agents through the web interface, text prompts are automatically\n")
            f.write("# converted to files in the prompts/ directory.\n\n")
            
            # Save configuration
            yaml.dump(processed_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        # Reload archetypes in memory
        try:
            reload_archetypes()
            global archetypes
            archetypes = load_archetypes()
            logger.info("Archetypes reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload archetypes: {e}", exc_info=True)
            # Continue anyway - configuration is saved
        
        return JSONResponse(content={
            "status": "success", 
            "message": "Configuration saved successfully. All text prompts have been converted to files."
        })
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error saving configuration: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

# --- API for AI provider configuration ---
@app.get("/api/ai-provider")
async def get_ai_provider_config():
    """Get current AI provider configuration."""
    try:
        provider = get_current_provider()
        config = get_provider_config()
        supported_models = get_supported_models(provider)
        
        # Don't return API keys through API
        safe_config = {
            "provider": provider.value,
            "supported_models": supported_models,
            "has_google_key": bool(config.get('google_api_key')),
            "has_openai_key": bool(config.get('openai_api_key')),
            "openai_base_url": config.get('openai_base_url', 'https://api.openai.com/v1'),
        }
        return JSONResponse(content=safe_config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting configuration: {str(e)}")

@app.post("/api/ai-provider")
async def save_ai_provider_config(request: Request):
    """Save AI provider configuration."""
    try:
        data = await request.json()
        provider_name = data.get("provider", "google_ai").lower()
        
        # Validate provider
        try:
            provider = AIProvider(provider_name)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown provider: {provider_name}. Supported: google_ai, openai"
            )
        
        # Get API keys
        google_api_key = data.get("google_api_key")
        openai_api_key = data.get("openai_api_key")
        openai_base_url = data.get("openai_base_url", "https://api.openai.com/v1")
        
        # Update configuration
        config = {}
        if google_api_key:
            config['google_api_key'] = google_api_key
        if openai_api_key:
            config['openai_api_key'] = openai_api_key
        if openai_base_url:
            config['openai_base_url'] = openai_base_url
        
        set_provider(provider, config)
        
        # Update .env file
        if hasattr(sys, '_MEIPASS'):
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            base_dir = os.getcwd()
        env_path = os.path.join(base_dir, '.env')
        
        # Read existing .env
        env_vars = {}
        if os.path.exists(env_path):
            from dotenv import dotenv_values
            env_vars = dotenv_values(env_path)
        
        # Update values
        env_vars['AI_PROVIDER'] = provider_name
        if google_api_key:
            env_vars['GOOGLE_API_KEY'] = google_api_key
        if openai_api_key:
            env_vars['OPENAI_API_KEY'] = openai_api_key
        if openai_base_url:
            env_vars['OPENAI_BASE_URL'] = openai_base_url
        
        # Write .env
        with open(env_path, 'w', encoding='utf-8') as f:
            for key, value in env_vars.items():
                if value:
                    f.write(f"{key}={value}\n")
        
        # Reload configuration
        load_provider_config()
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Provider {provider_name} configured successfully"
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving configuration: {str(e)}")

# --- API for vector database operations ---
@app.get("/api/vector-db")
async def get_vector_db_entries():
    """Get all entries from vector database."""
    try:
        from vector_db.client import collection
        all_data = collection.get()
        
        entries = []
        if all_data['ids']:
            for i, chat_id in enumerate(all_data['ids']):
                metadata = all_data['metadatas'][i] if all_data['metadatas'] else {}
                document = all_data['documents'][i] if all_data['documents'] else ""
                
                entries.append({
                    "id": chat_id,
                    "metadata": metadata,
                    "document": document,
                    "preview": document[:200] + "..." if len(document) > 200 else document
                })
        
        return JSONResponse(content={"entries": entries, "count": len(entries)})
    except ImportError:
        raise HTTPException(status_code=500, detail="Vector database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading database: {str(e)}")

@app.get("/api/vector-db/{chat_id}")
async def get_vector_db_entry(chat_id: str):
    """Get specific entry from vector database by ID."""
    try:
        from vector_db.client import collection
        result = collection.get(ids=[chat_id])
        
        if not result['ids']:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        metadata = result['metadatas'][0] if result['metadatas'] else {}
        document = result['documents'][0] if result['documents'] else ""
        
        return JSONResponse(content={
            "id": chat_id,
            "metadata": metadata,
            "document": document
        })
    except ImportError:
        raise HTTPException(status_code=500, detail="Vector database not available")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading entry: {str(e)}")

@app.delete("/api/vector-db/{chat_id}")
async def delete_vector_db_entry(chat_id: str):
    """Delete entry from vector database by ID."""
    try:
        from vector_db.client import delete_chat
        delete_chat(chat_id)
        return JSONResponse(content={"status": "success", "message": f"Entry {chat_id} deleted"})
    except ImportError:
        raise HTTPException(status_code=500, detail="Vector database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting entry: {str(e)}")

@app.post("/api/vector-db/{chat_id}")
async def update_vector_db_entry(chat_id: str, request: Request):
    """Update entry in vector database."""
    try:
        from vector_db.client import update_chat
        data = await request.json()
        
        document = data.get("document")
        metadata = data.get("metadata", {})
        
        if not document:
            raise HTTPException(status_code=400, detail="Field 'document' is required")
        
        # Update entry (or create new if doesn't exist)
        update_chat(chat_id, document, metadata)
        
        return JSONResponse(content={"status": "success", "message": f"Entry {chat_id} updated"})
    except ImportError:
        raise HTTPException(status_code=500, detail="Vector database not available")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating entry: {str(e)}")

# --- API for server shutdown ---
@app.post("/api/shutdown")
async def shutdown_server():
    """Shutdown the server."""
    try:
        global _server_instance, _shutdown_event
        
        # Run shutdown in separate thread
        def do_shutdown():
            import time
            # Give time to send HTTP response
            time.sleep(0.5)
            
            # Try graceful shutdown through server instance
            if _server_instance:
                try:
                    logger.info("Initiating graceful shutdown...")
                    # Uvicorn Server has should_exit attribute for graceful shutdown
                    if hasattr(_server_instance, 'should_exit'):
                        _server_instance.should_exit = True
                        logger.info("Server shutdown signal sent")
                    
                    # Wait for server to shut down gracefully
                    # This allows connections to close and port to be released
                    max_wait = 5
                    for i in range(max_wait * 2):
                        # Check if server is still running
                        if hasattr(_server_instance, 'should_exit'):
                            # Server should exit when should_exit is True
                            pass
                        time.sleep(0.5)
                        if i % 2 == 0:
                            logger.debug(f"Waiting for server shutdown... ({i//2 + 1}/{max_wait}s)")
                    
                    # Also try shutdown through server.shutdown() if available
                    if hasattr(_server_instance, 'shutdown'):
                        try:
                            logger.info("Calling server.shutdown()...")
                            _server_instance.shutdown()
                            time.sleep(1)
                        except Exception as e:
                            logger.debug(f"Server.shutdown() error (may be expected): {e}")
                    
                    # Additional wait to ensure port is released
                    logger.info("Waiting for port to be released...")
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error in graceful shutdown: {e}", exc_info=True)
            
            # Give time for port to be released before exit
            # TIME_WAIT state typically lasts 30-120 seconds, but we wait a bit
            logger.info("Shutdown complete, exiting process")
            time.sleep(0.5)
            
            # Always exit process through os._exit(0)
            # This ensures process will exit even if graceful shutdown failed
            os._exit(0)
        
        # Run shutdown in separate thread (not daemon, so process doesn't exit before shutdown)
        shutdown_thread = threading.Thread(target=do_shutdown, daemon=False)
        shutdown_thread.start()
        
        # Send response
        logger.info("Shutdown requested via API")
        increment_counter("shutdown_requests")
        return JSONResponse(content={
            "status": "success",
            "message": "Server is shutting down..."
        })
    except Exception as e:
        logger.error(f"Error shutting down server: {e}", exc_info=True)
        increment_counter("api_errors")
        raise HTTPException(status_code=500, detail=f"Error shutting down server: {str(e)}")

# --- API for language settings ---
@app.get("/api/language")
async def get_language(request: Request):
    """Get current language setting."""
    language = get_user_language(request)
    return JSONResponse(content={"language": language, "supported_languages": SUPPORTED_LANGUAGES})

@app.post("/api/language")
async def set_language(request: Request):
    """Set language preference."""
    try:
        data = await request.json()
        language = data.get("language", DEFAULT_LANGUAGE)
        
        if language not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")
        
        response = JSONResponse(content={"status": "success", "language": language})
        response.set_cookie(key="language", value=language, max_age=365*24*60*60)  # 1 year
        increment_counter("language_changes")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting language: {e}", exc_info=True)
        increment_counter("api_errors")
        raise HTTPException(status_code=500, detail=f"Error setting language: {str(e)}")

# --- API for monitoring ---
@app.get("/api/metrics")
async def get_metrics():
    """Get application metrics."""
    try:
        metrics = get_metrics_summary()
        increment_counter("metrics_requests")
        return JSONResponse(content=metrics)
    except Exception as e:
        logger.error(f"Error getting metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting metrics: {str(e)}")

@app.post("/api/metrics/reset")
async def reset_metrics_endpoint():
    """Reset all metrics."""
    try:
        reset_metrics()
        increment_counter("metrics_resets")
        return JSONResponse(content={"status": "success", "message": "Metrics reset"})
    except Exception as e:
        logger.error(f"Error resetting metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error resetting metrics: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if archetypes are loaded
        archetypes_loaded = len(archetypes) > 0
        
        # Check if vector database is available
        vector_db_available = False
        try:
            from vector_db.client import collection
            vector_db_available = True
        except Exception:
            pass
        
        health_status = {
            "status": "healthy" if archetypes_loaded else "degraded",
            "archetypes_loaded": archetypes_loaded,
            "vector_db_available": vector_db_available,
            "timestamp": datetime.now().isoformat()
        }
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        increment_counter("health_checks")
        return JSONResponse(content=health_status, status_code=status_code)
    except Exception as e:
        logger.error(f"Error in health check: {e}", exc_info=True)
        return JSONResponse(
            content={"status": "error", "error": str(e)},
            status_code=500
        )