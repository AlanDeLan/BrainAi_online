import os
import sys
import json
import threading
from typing import List, Optional
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
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
from core.utils import resource_path, get_base_directory
from conferences.rada import router as rada_router
from core.auth_routes import router as auth_router
from core.auth import decode_access_token, get_current_user_id, get_current_user_id_optional
from core.database import get_db
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

app = FastAPI(
    title="BrainAi",
    description="Intelligent local AI assistant with multiple agents and vector database support",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI at /docs
    redoc_url="/redoc",  # ReDoc at /redoc
    openapi_url="/openapi.json"  # OpenAPI schema at /openapi.json
)

# JWT Authentication Middleware
class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to optionally extract user_id from JWT token."""
    
    async def dispatch(self, request: Request, call_next):
        # Public routes that don't require authentication
        public_routes = [
            "/", "/docs", "/redoc", "/openapi.json",
            "/static", "/health", "/favicon.ico",
            "/api/auth/register", "/api/auth/login",
            "/process"  # Temporarily public during migration
        ]
        
        # Check if route is public
        path = request.url.path
        is_public = any(path.startswith(route) for route in public_routes)
        
        # Extract user_id from token if present (but don't block if missing on public routes)
        user_id = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                token_data = decode_access_token(token)
                user_id = token_data.user_id
                request.state.user_id = user_id
            except Exception as e:
                # Invalid token - only fail on protected routes
                if not is_public:
                    logger.warning(f"Invalid token on protected route: {e}")
                    return Response(
                        content=json.dumps({"detail": "Invalid or expired token"}),
                        status_code=401,
                        media_type="application/json"
                    )
                else:
                    logger.debug(f"Invalid token on public route, continuing without auth: {e}")
        
        response = await call_next(request)
        return response

# Add middleware
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(rada_router)
app.include_router(auth_router)  # Authentication routes

# Setup logging
logger.info("Starting BrainAi application")

# Use resource_path for static files and templates
static_dir = resource_path("static")
templates_dir = resource_path("templates")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

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

UPLOAD_DIR = os.path.join(base_dir, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
async def process_text(
    request: Request,
    user_id: Optional[int] = Depends(get_current_user_id_optional)
):
    """
    Process text with selected archetype.
    Optional authentication - works with or without JWT token.
    """
    with TimerContext("process_request"):
        try:
            increment_counter("api_requests")
            data = await request.json()
            text = data.get("text")
            archetype = data.get("archetype")
            remember = data.get("remember", True)
            chat_id = data.get("chat_id")
            
            logger.info(f"Processing request: user_id={user_id}, archetype={archetype}, chat_id={chat_id}, remember={remember}")
            increment_counter(f"archetype_{archetype}")
            
            if not text or not archetype:
                error_msg = "Text and archetype are required"
                logger.warning(error_msg)
                increment_counter("api_errors")
                raise HTTPException(status_code=400, detail=error_msg)
            
            # Get model parameters from request (if provided)
            model_params = {}
            if 'temperature' in data:
                model_params['temperature'] = float(data['temperature'])
            if 'max_tokens' in data:
                model_params['max_tokens'] = int(data['max_tokens'])
            if 'top_p' in data:
                model_params['top_p'] = float(data['top_p'])
            if 'top_k' in data:
                model_params['top_k'] = int(data['top_k'])
            
            # --- Load chat history BEFORE processing (for context) ---
            chat_history = []
            if remember and chat_id:
                try:
                    filepath = get_chat_file(chat_id)
                    if os.path.exists(filepath):
                        try:
                            async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
                                content = await f.read()
                                try:
                                    chat_history = json.loads(content)
                                except json.JSONDecodeError as e:
                                    logger.warning(f"Failed to parse history file {filepath}: {e}, using empty history")
                                    chat_history = []
                        except Exception as e:
                            logger.warning(f"Failed to read history file {filepath}: {e}, using empty history")
                            chat_history = []
                except Exception as e:
                    logger.warning(f"Error loading chat history: {e}, using empty history")
                    chat_history = []
            
            result = process_with_archetype(
                text=text,
                archetype_name=archetype,
                archetypes=archetypes,
                chat_history=chat_history,
                chat_id=chat_id if remember else None,
                user_id=user_id,
                **model_params
            )
            
            if "error" in result:
                logger.error(f"Error processing request: {result['error']}")
                increment_counter("api_errors")
                raise HTTPException(status_code=500, detail=result["error"])
            
            # --- Save chat as array of messages in single file ---
            if remember and chat_id:
                try:
                    filepath = get_chat_file(chat_id)
                    # Use chat_history we already loaded (or create new if not loaded)
                    if not chat_history:
                        # If chat_history wasn't loaded (e.g., remember=False initially), load it now
                        if os.path.exists(filepath):
                            try:
                                async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
                                    content = await f.read()
                                    try:
                                        chat_history = json.loads(content)
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"Failed to parse history file {filepath}: {e}, creating new history")
                                        chat_history = []
                            except Exception as e:
                                logger.warning(f"Failed to read history file {filepath}: {e}, creating new history")
                                chat_history = []
                    
                    # Append new message to history
                    chat_history.append({
                        "user_input": text,
                        "archetype": archetype,
                        "model_response": result.get("response", "")
                    })
                    
                    try:
                        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                            await f.write(json.dumps(chat_history, ensure_ascii=False, indent=2))
                        logger.debug(f"Chat history saved to {filepath}")
                    except Exception as e:
                        logger.error(f"Failed to save chat history to {filepath}: {e}", exc_info=True)
                        # Don't fail the request if history save fails
                    
                    # --- Save to vector database (save each message separately) ---
                    try:
                        from vector_db.client import save_message
                        import datetime
                        
                        # Get timestamp with microsecond precision for uniqueness
                        timestamp = datetime.datetime.now().isoformat()
                        msg_index = len(chat_history) - 1  # Index of the last message (just added)
                        
                        # Save user message (use message index * 2 for user messages)
                        user_msg_id = f"{chat_id}_msg_{msg_index * 2}_user"
                        save_message(
                            chat_id=chat_id,
                            message_id=user_msg_id,
                            message_text=text,
                            role="user",
                            archetype=archetype,
                            timestamp=timestamp,
                            user_id=user_id
                        )
                        
                        # Save assistant response (use message index * 2 + 1 for assistant messages)
                        assistant_msg_id = f"{chat_id}_msg_{msg_index * 2 + 1}_assistant"
                        save_message(
                            chat_id=chat_id,
                            message_id=assistant_msg_id,
                            message_text=result.get("response", ""),
                            role="assistant",
                            archetype=archetype,
                            timestamp=timestamp,
                            user_id=user_id
                        )
                        
                        logger.debug(f"Messages saved to vector database: {user_msg_id}, {assistant_msg_id}")
                        increment_counter("vector_db_saves")
                    except Exception as e:
                        # Log error but don't fail the request
                        logger.warning(f"Failed to save to vector database: {e}", exc_info=True)
                        increment_counter("vector_db_errors")
                except Exception as e:
                    logger.error(f"Unexpected error saving chat: {e}", exc_info=True)
                    # Don't fail the request if chat save fails
            
            # Track cache hits/misses
            if result.get("cached"):
                increment_counter("cache_hits")
            else:
                increment_counter("cache_misses")
            
            # Return result with cache status
            return JSONResponse(content=result)
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

@app.get("/api/history/search")
async def search_history(query: str = None, archetype: str = None):
    """Search history files by text content and/or archetype."""
    try:
        # Allow search with just query or just archetype, or both
        # If both are None, return empty results
        if not query and not archetype:
            return JSONResponse(content={
                "results": [],
                "count": 0,
                "query": query,
                "archetype": archetype
            })
        
        if not os.path.exists(HISTORY_DIR):
            os.makedirs(HISTORY_DIR, exist_ok=True)
            return JSONResponse(content={
                "results": [],
                "count": 0,
                "query": query,
                "archetype": archetype
            })
        
        files = [f for f in os.listdir(HISTORY_DIR) if f.endswith('.json')]
        results = []
        
        query_lower = query.lower() if query else None
        archetype_lower = archetype.lower() if archetype else None
        
        for filename in files:
            try:
                filepath = os.path.join(HISTORY_DIR, filename)
                async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
                    content = await f.read()
                    data = json.loads(content)
                
                # Check if matches archetype filter
                matches_archetype = True
                if archetype_lower:
                    # Check if any message has matching archetype
                    if isinstance(data, list):
                        # Regular chat format
                        matches_archetype = any(
                            msg.get('archetype', '').lower() == archetype_lower 
                            for msg in data if isinstance(msg, dict)
                        )
                    elif isinstance(data, dict):
                        # RADA format or other format
                        matches_archetype = (
                            data.get('archetype', '').lower() == archetype_lower or
                            archetype_lower in str(data.get('archetypes', '')).lower()
                        )
                # If no archetype filter, matches_archetype remains True
                
                # Check if matches text query
                matches_query = True
                if query_lower:
                    # Search in all messages
                    content_lower = content.lower()
                    matches_query = query_lower in content_lower
                # If no query, matches_query remains True
                
                # Include result if it matches both filters (or if filter is not applied)
                if matches_archetype and matches_query:
                    # Extract preview and metadata
                    preview = ""
                    chat_archetype = ""
                    timestamp = filename.split('_')[0] if '_' in filename else ""
                    
                    if isinstance(data, list) and len(data) > 0:
                        first_msg = data[0]
                        if isinstance(first_msg, dict):
                            preview = first_msg.get('user_input', '')[:100]
                            chat_archetype = first_msg.get('archetype', '')
                    elif isinstance(data, dict):
                        preview = data.get('user_input', '')[:100]
                        chat_archetype = data.get('archetype', '') or str(data.get('archetypes', ''))
                    
                    results.append({
                        "filename": filename,
                        "preview": preview,
                        "archetype": chat_archetype,
                        "timestamp": timestamp,
                        "matches": {
                            "query": matches_query if query else False,
                            "archetype": matches_archetype if archetype else False
                        }
                    })
            except Exception as e:
                logger.warning(f"Error reading history file {filename}: {e}")
                continue
        
        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return JSONResponse(content={
            "results": results,
            "count": len(results),
            "query": query,
            "archetype": archetype
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error searching history: {str(e)}")

@app.get("/favicon.ico")
async def favicon():
    favicon_path = resource_path("static/favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    else:
        raise HTTPException(status_code=404, detail="Favicon not found")

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
async def get_vector_db_entries(user_id: Optional[int] = Depends(get_current_user_id_optional)):
    """Get all entries from vector database (grouped by chat_id)."""
    try:
        from vector_db.client import get_all_chats_grouped, is_vector_db_available
        if not is_vector_db_available():
            return JSONResponse(content={
                "entries": [],
                "count": 0,
                "error": "Vector database not available (ChromaDB may not work in EXE mode)",
                "available": False
            })
        # If no user_id (no auth), return empty
        if user_id is None:
            logger.warning("No user_id provided for vector-db, returning empty")
            return JSONResponse(content={"entries": [], "count": 0, "available": True})
        
        chats = get_all_chats_grouped(user_id=user_id)
        return JSONResponse(content={"entries": chats, "count": len(chats), "available": True})
    except ImportError:
        return JSONResponse(content={
            "entries": [],
            "count": 0,
            "error": "Vector database module not available",
            "available": False
        })
    except Exception as e:
        logger.error(f"Error getting vector DB entries: {e}", exc_info=True)
        return JSONResponse(content={
            "entries": [],
            "count": 0,
            "error": f"Error getting entries: {str(e)}",
            "available": False
        })

@app.get("/api/vector-db/search")
async def search_vector_db(
    query: str = None,
    n_results: int = 5,
    user_id: Optional[int] = Depends(get_current_user_id_optional)
):
    """Search vector database for relevant chats (optional user filtering)."""
    try:
        if not query:
            raise HTTPException(status_code=400, detail="Query parameter is required")
        
        from vector_db.client import search_chats, is_vector_db_available
        if not is_vector_db_available():
            return JSONResponse(content={
                "results": [],
                "query": query,
                "error": "Vector database not available (ChromaDB may not work in EXE mode)",
                "available": False
            })
        
        # If no user_id, return empty results for now
        if user_id is None:
            logger.warning("No user_id provided for search, returning empty")
            return JSONResponse(content={"results": [], "query": query, "available": True})
        
        results = search_chats(query, n_results=n_results, user_id=user_id)
        
        # Convert score (distance) to relevance (1 - distance for similarity)
        for result in results:
            if 'score' in result:
                # ChromaDB returns distances (lower is better), convert to relevance (higher is better)
                result['relevance'] = max(0, 1 - result['score'])
                # Keep score for compatibility
        return JSONResponse(content={"results": results, "query": query, "available": True})
    except HTTPException:
        raise
    except ImportError:
        return JSONResponse(content={
            "results": [],
            "query": query,
            "error": "Vector database module not available",
            "available": False
        })
    except Exception as e:
        logger.error(f"Error searching vector DB: {e}", exc_info=True)
        return JSONResponse(content={
            "results": [],
            "query": query,
            "error": f"Error searching: {str(e)}",
            "available": False
        })


@app.get("/api/vector-db/{chat_id}")
async def get_vector_db_entry(chat_id: str, user_id: Optional[int] = Depends(get_current_user_id_optional)):
    """Get specific chat from vector database by chat_id (grouped messages)."""
    try:
        from vector_db.client import get_user_collection, is_vector_db_available
        
        if not is_vector_db_available():
            raise HTTPException(status_code=503, detail="Vector database not available")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        collection = get_user_collection(user_id)
        if collection is None:
            raise HTTPException(status_code=503, detail="Failed to get user collection")
        
        # Get all messages for this chat_id
        all_data = collection.get()
        
        messages = []
        chat_metadata = {}
        
        if all_data.get('ids'):
            for i, msg_id in enumerate(all_data['ids']):
                metadata = all_data['metadatas'][i] if all_data.get('metadatas') and i < len(all_data['metadatas']) else {}
                document = all_data['documents'][i] if all_data.get('documents') and i < len(all_data['documents']) else ""
                
                if metadata.get('chat_id') == chat_id:
                    messages.append({
                        'role': metadata.get('role', 'unknown'),
                        'content': document,
                        'message_id': msg_id,
                        'timestamp': metadata.get('timestamp', '')
                    })
                    
                    # Save first message metadata as chat metadata
                    if not chat_metadata:
                        chat_metadata = {
                            'archetype': metadata.get('archetype', 'N/A'),
                            'timestamp': metadata.get('timestamp', 'N/A'),
                            'user_id': metadata.get('user_id')
                        }
        
        if not messages:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Sort messages by timestamp
        messages.sort(key=lambda x: x.get('timestamp', ''))
        
        # Create document preview
        user_messages = [msg for msg in messages if msg['role'] == 'user']
        document = "\n\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in messages])
        
        return JSONResponse(content={
            "id": chat_id,
            "metadata": chat_metadata,
            "document": document,
            "messages": messages,
            "message_count": len(messages)
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat {chat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error reading entry: {str(e)}")

@app.delete("/api/vector-db/{chat_id}")
async def delete_vector_db_entry(chat_id: str, user_id: Optional[int] = Depends(get_current_user_id_optional)):
    """Delete all messages for a chat from vector database."""
    try:
        from vector_db.client import get_user_collection, is_vector_db_available
        
        if not is_vector_db_available():
            raise HTTPException(status_code=503, detail="Vector database not available")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        collection = get_user_collection(user_id)
        if collection is None:
            raise HTTPException(status_code=503, detail="Failed to get user collection")
        
        # Get all messages for this chat
        all_data = collection.get()
        message_ids_to_delete = []
        
        if all_data.get('ids'):
            for i, msg_id in enumerate(all_data['ids']):
                metadata = all_data['metadatas'][i] if all_data.get('metadatas') and i < len(all_data['metadatas']) else {}
                
                if metadata.get('chat_id') == chat_id:
                    message_ids_to_delete.append(msg_id)
        
        if not message_ids_to_delete:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Delete all messages
        collection.delete(ids=message_ids_to_delete)
        
        logger.info(f"Deleted {len(message_ids_to_delete)} messages from chat {chat_id} for user {user_id}")
        
        return JSONResponse(content={
            "status": "success", 
            "message": f"Chat {chat_id} deleted ({len(message_ids_to_delete)} messages)"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat {chat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting entry: {str(e)}")

@app.post("/api/vector-db/{chat_id}")
async def update_vector_db_entry(chat_id: str, request: Request, user_id: Optional[int] = Depends(get_current_user_id_optional)):
    """Update entry in vector database (updates assistant response)."""
    try:
        from vector_db.client import get_user_collection, is_vector_db_available
        
        if not is_vector_db_available():
            raise HTTPException(status_code=503, detail="Vector database not available")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        data = await request.json()
        
        document = data.get("document")
        if not document:
            raise HTTPException(status_code=400, detail="Field 'document' is required")
        
        collection = get_user_collection(user_id)
        if collection is None:
            raise HTTPException(status_code=503, detail="Failed to get user collection")
        
        # Get all messages for this chat
        all_data = collection.get()
        assistant_messages = []
        
        if all_data.get('ids'):
            for i, msg_id in enumerate(all_data['ids']):
                metadata = all_data['metadatas'][i] if all_data.get('metadatas') and i < len(all_data['metadatas']) else {}
                
                if metadata.get('chat_id') == chat_id and metadata.get('role') == 'assistant':
                    assistant_messages.append(msg_id)
        
        if not assistant_messages:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Update the first assistant message (response)
        collection.update(
            ids=[assistant_messages[0]],
            documents=[document]
        )
        
        logger.info(f"Updated chat {chat_id} for user {user_id}")
        
        return JSONResponse(content={"status": "success", "message": f"Entry {chat_id} updated"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chat {chat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating entry: {str(e)}")

# --- API for file upload and processing ---
@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a text file for vector database."""
    try:
        from core.file_processor import process_file, is_file_supported, get_supported_extensions
        from vector_db.client import save_message, is_vector_db_available
        import datetime
        
        # Check if file is supported
        if not is_file_supported(file.filename):
            supported = ", ".join(get_supported_extensions())
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported: {supported}"
            )
        
        # Check vector DB availability
        if not is_vector_db_available():
            raise HTTPException(
                status_code=503,
                detail="Vector database not available. Cannot process files."
            )
        
        # Save uploaded file temporarily
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"File uploaded: {file.filename} ({len(content)} bytes)")
        
        # Process file into chunks
        chunks = process_file(file_path, chunk_size=1000, chunk_overlap=200)
        
        if not chunks:
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail="File is empty or contains no text"
            )
        
        # Save chunks to vector database
        timestamp = datetime.datetime.now().isoformat()
        saved_count = 0
        
        for chunk in chunks:
            # Create unique ID for chunk
            chunk_id = f"file_{file.filename}_{chunk['chunk_index']}"
            
            # Save to vector DB
            save_message(
                chat_id=f"file_{file.filename}",
                message_id=chunk_id,
                message_text=chunk["text"],
                role="file",
                archetype=None,
                timestamp=timestamp
            )
            saved_count += 1
        
        logger.info(f"File processed: {file.filename} -> {saved_count} chunks saved to vector DB")
        
        return JSONResponse(content={
            "status": "success",
            "message": f"File '{file.filename}' processed and saved to vector database",
            "filename": file.filename,
            "chunks_count": saved_count,
            "file_size": len(content)
        })
        
    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"Import error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"File processing module not available: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info=True)
        # Clean up uploaded file if exists
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )

@app.get("/api/files/supported")
async def get_supported_file_types():
    """Get list of supported file types."""
    try:
        from core.file_processor import get_supported_extensions
        extensions = get_supported_extensions()
        return JSONResponse(content={
            "supported_extensions": extensions,
            "supported_types": {
                ".txt": "Plain text",
                ".md": "Markdown",
                ".docx": "Microsoft Word",
                ".pdf": "PDF document"
            }
        })
    except ImportError:
        return JSONResponse(content={
            "supported_extensions": [".txt", ".md"],
            "supported_types": {
                ".txt": "Plain text",
                ".md": "Markdown"
            },
            "note": "Full file processing not available"
        })

# --- API for server shutdown ---
@app.post("/api/set-language")
async def set_language(request: Request):
    """Set user's preferred language."""
    try:
        data = await request.json()
        language = data.get("language", DEFAULT_LANGUAGE)
        
        if language not in SUPPORTED_LANGUAGES:
            language = DEFAULT_LANGUAGE
        
        # Create response with cookie
        response = JSONResponse(content={
            "status": "success",
            "language": language
        })
        
        # Set cookie for language preference
        response.set_cookie(
            key="language",
            value=language,
            max_age=365 * 24 * 60 * 60,  # 1 year
            httponly=False,
            samesite="lax"
        )
        
        logger.info(f"Language set to: {language}")
        return response
    except Exception as e:
        logger.error(f"Error setting language: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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
        
        # Add cache statistics
        try:
            from core.cache import get_cache_stats
            metrics["cache"] = get_cache_stats()
        except Exception as e:
            logger.debug(f"Error getting cache stats: {e}")
            metrics["cache"] = None
        
        # Add archetype usage statistics
        archetype_counts = {}
        for key, value in metrics.get("counters", {}).items():
            if key.startswith("archetype_"):
                archetype_name = key.replace("archetype_", "")
                archetype_counts[archetype_name] = value
        
        metrics["archetype_usage"] = archetype_counts
        
        # Add history statistics
        try:
            history_files = [f for f in os.listdir(HISTORY_DIR) if f.endswith('.json')]
            metrics["history"] = {
                "total_chats": len(history_files),
                "history_dir": HISTORY_DIR
            }
        except Exception as e:
            logger.debug(f"Error getting history stats: {e}")
            metrics["history"] = {"total_chats": 0}
        
        # Add vector DB statistics
        try:
            from vector_db.client import get_all_chats, is_vector_db_available, get_vector_db_type
            if is_vector_db_available():
                vector_db_chats = get_all_chats()
                db_type = get_vector_db_type()
                metrics["vector_db"] = {
                    "total_entries": len(vector_db_chats),
                    "available": True,
                    "type": db_type
                }
            else:
                metrics["vector_db"] = {
                    "total_entries": 0,
                    "available": False,
                    "error": "Vector database not available"
                }
        except Exception as e:
            logger.debug(f"Error getting vector DB stats: {e}")
            metrics["vector_db"] = {
                "total_entries": 0,
                "available": False,
                "error": str(e)
            }
        
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
        
        # Also reset cache stats if requested
        try:
            from core.cache import reset_cache_stats
            reset_cache_stats()
        except Exception:
            pass
        
        return JSONResponse(content={"status": "success", "message": "Metrics reset"})
    except Exception as e:
        logger.error(f"Error resetting metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error resetting metrics: {str(e)}")

# --- API for cache management ---
@app.get("/api/cache/stats")
async def get_cache_stats_endpoint():
    """Get cache statistics."""
    try:
        from core.cache import get_cache_stats
        stats = get_cache_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {str(e)}")

@app.post("/api/cache/clear")
async def clear_cache_endpoint():
    """Clear the cache."""
    try:
        from core.cache import clear_cache
        clear_cache()
        return JSONResponse(content={"status": "success", "message": "Cache cleared"})
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

@app.post("/api/cache/clear-expired")
async def clear_expired_cache_endpoint():
    """Clear expired cache entries."""
    try:
        from core.cache import clear_expired_entries, DEFAULT_TTL
        cleared = clear_expired_entries(ttl=DEFAULT_TTL)
        return JSONResponse(content={
            "status": "success",
            "message": f"Cleared {cleared} expired entries",
            "cleared_count": cleared
        })
    except Exception as e:
        logger.error(f"Error clearing expired cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error clearing expired cache: {str(e)}")

# --- API for export/import chats ---
@app.get("/api/history/export/{filename}")
async def export_history_file(filename: str, format: str = "json"):
    """Export a history file in specified format (json or markdown)."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    try:
        filepath = os.path.join(HISTORY_DIR, filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="File not found")
        
        async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
        
        if format.lower() == "markdown":
            # Convert to Markdown format
            markdown_content = f"# Chat History: {filename}\n\n"
            markdown_content += f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            markdown_content += "---\n\n"
            
            if isinstance(data, list):
                # Regular chat format
                for i, msg in enumerate(data, 1):
                    markdown_content += f"## Message {i}\n\n"
                    markdown_content += f"**Archetype:** {msg.get('archetype', 'N/A')}\n\n"
                    markdown_content += f"**User:**\n{msg.get('user_input', '')}\n\n"
                    markdown_content += f"**Assistant:**\n{msg.get('model_response', '')}\n\n"
                    markdown_content += "---\n\n"
            elif isinstance(data, dict):
                # RADA format
                markdown_content += f"**Question:** {data.get('user_input', 'N/A')}\n\n"
                markdown_content += f"**Type:** {data.get('type', 'N/A')}\n\n"
                
                if data.get('type') == 'rada':
                    if data.get('initial'):
                        markdown_content += "### Initial Thoughts\n\n"
                        for agent, response in data['initial'].items():
                            markdown_content += f"**{agent}:**\n{response}\n\n"
                    
                    if data.get('discussion'):
                        markdown_content += "### Discussion\n\n"
                        for agent, response in data['discussion'].items():
                            markdown_content += f"**{agent}:**\n{response}\n\n"
                    
                    if data.get('consensus'):
                        markdown_content += "### Consensus\n\n"
                        markdown_content += f"{data['consensus']}\n\n"
            
            return JSONResponse(content={
                "format": "markdown",
                "filename": filename.replace('.json', '.md'),
                "content": markdown_content
            })
        else:
            # JSON format
            return JSONResponse(content={
                "format": "json",
                "filename": filename,
                "content": data
            })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting history file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error exporting file: {str(e)}")

@app.get("/api/history/export/all")
async def export_all_history(format: str = "json"):
    """Export all history files as a single file."""
    try:
        if not os.path.exists(HISTORY_DIR):
            os.makedirs(HISTORY_DIR, exist_ok=True)
        
        files = [f for f in os.listdir(HISTORY_DIR) if f.endswith('.json')]
        files.sort(reverse=True)
        
        if not files:
            return JSONResponse(content={
                "format": format,
                "filename": f"all_chats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}",
                "content": {} if format.lower() == "json" else "# All Chat History\n\n**No chats found.**\n\n",
                "total_chats": 0
            })
        
        all_chats = {}
        for filename in files:
            try:
                filepath = os.path.join(HISTORY_DIR, filename)
                async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
                    content = await f.read()
                    data = json.loads(content)
                    all_chats[filename] = data
            except Exception as e:
                logger.warning(f"Error reading file {filename}: {e}")
                continue
        
        if format.lower() == "markdown":
            # Convert all to Markdown
            markdown_content = f"# All Chat History\n\n"
            markdown_content += f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            markdown_content += f"**Total Chats:** {len(all_chats)}\n\n"
            markdown_content += "---\n\n"
            
            for filename, data in all_chats.items():
                markdown_content += f"## {filename}\n\n"
                
                if isinstance(data, list):
                    for i, msg in enumerate(data, 1):
                        markdown_content += f"### Message {i}\n\n"
                        markdown_content += f"**Archetype:** {msg.get('archetype', 'N/A')}\n\n"
                        markdown_content += f"**User:**\n{msg.get('user_input', '')}\n\n"
                        markdown_content += f"**Assistant:**\n{msg.get('model_response', '')}\n\n"
                elif isinstance(data, dict):
                    markdown_content += f"**Question:** {data.get('user_input', 'N/A')}\n\n"
                    if data.get('type') == 'rada':
                        if data.get('consensus'):
                            markdown_content += f"**Consensus:**\n{data['consensus']}\n\n"
                
                markdown_content += "---\n\n"
            
            return JSONResponse(content={
                "format": "markdown",
                "filename": f"all_chats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                "content": markdown_content,
                "total_chats": len(all_chats)
            })
        else:
            # JSON format
            return JSONResponse(content={
                "format": "json",
                "filename": f"all_chats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "content": all_chats,
                "total_chats": len(all_chats)
            })
    except Exception as e:
        logger.error(f"Error exporting all history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error exporting history: {str(e)}")

@app.post("/api/history/import")
async def import_history_file(request: Request):
    """Import a history file."""
    try:
        data = await request.json()
        content = data.get("content")
        filename = data.get("filename")
        format_type = data.get("format", "json")
        
        if not content or not filename:
            raise HTTPException(status_code=400, detail="Content and filename are required")
        
        # Validate filename
        if "/" in filename or "\\" in filename or ".." in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        # Parse content based on format
        if format_type.lower() == "markdown":
            # For markdown, we'll create a simple structure
            # This is a basic implementation - could be enhanced
            raise HTTPException(status_code=501, detail="Markdown import not yet implemented")
        else:
            # JSON format
            if isinstance(content, str):
                imported_data = json.loads(content)
            else:
                imported_data = content
        
        # Save to history directory
        filepath = os.path.join(HISTORY_DIR, filename)
        
        # If file exists, add timestamp to avoid overwriting
        if os.path.exists(filepath):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = filename.replace('.json', '')
            filename = f"{base_name}_imported_{timestamp}.json"
            filepath = os.path.join(HISTORY_DIR, filename)
        
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(json.dumps(imported_data, ensure_ascii=False, indent=2))
        
        logger.info(f"Imported history file: {filename}")
        
        return JSONResponse(content={
            "status": "success",
            "message": f"File imported as {filename}",
            "filename": filename
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing history file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error importing file: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if archetypes are loaded
        archetypes_loaded = len(archetypes) > 0
        
        # Check if vector database is available
        vector_db_available = False
        try:
            from vector_db.client import is_vector_db_available
            vector_db_available = is_vector_db_available()
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