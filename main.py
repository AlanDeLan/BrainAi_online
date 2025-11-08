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
from conferences.rada import router as rada_router
import aiofiles
import yaml
import shutil

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

app = FastAPI(title="Local Brain")

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
    return templates.TemplateResponse(
        "index.html", {"request": request, "archetypes": archetypes}
    )

def get_chat_file(chat_id):
    return os.path.join(HISTORY_DIR, f"{chat_id}.json")

@app.post("/process")
async def process_text(request: Request):
    data = await request.json()
    text = data.get("text")
    archetype = data.get("archetype")
    remember = data.get("remember", True)
    chat_id = data.get("chat_id")
    if not text or not archetype:
        raise HTTPException(status_code=400, detail="Text and archetype are required")
    result = process_with_archetype(
        text=text,
        archetype_name=archetype,
        archetypes=archetypes
    )
    # --- Save chat as array of messages in single file ---
    if remember and chat_id:
        filepath = get_chat_file(chat_id)
        if os.path.exists(filepath):
            async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
                content = await f.read()
                try:
                    history = json.loads(content)
                except Exception:
                    history = []
        else:
            history = []
        history.append({
            "user_input": text,
            "archetype": archetype,
            "model_response": result.get("response", "")
        })
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(json.dumps(history, ensure_ascii=False, indent=2))
    return result

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

def get_archetypes_yaml_path():
    """Get path to archetypes.yaml with PyInstaller support."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller: search next to exe file
        if getattr(sys, 'frozen', False):
            return os.path.join(os.path.dirname(sys.executable), "archetypes.yaml")
        else:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), "archetypes.yaml")
    else:
        return "archetypes.yaml"

@app.get("/api/archetypes")
async def get_archetypes_config():
    """Get current agent configuration."""
    try:
        archetypes_path = get_archetypes_yaml_path()
        with open(archetypes_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return JSONResponse(content={"archetypes": config})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading configuration: {str(e)}")

@app.post("/api/archetypes")
async def save_archetypes_config(request: Request):
    """Save agent configuration."""
    try:
        data = await request.json()
        archetypes_config = data.get("archetypes", {})
        
        # Validation: check for required fields
        for archetype_key, archetype_config in archetypes_config.items():
            if not isinstance(archetype_config, dict):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid configuration for agent '{archetype_key}'"
                )
            if "name" not in archetype_config:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Agent '{archetype_key}' must have 'name' field"
                )
            if "model_name" not in archetype_config:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Agent '{archetype_key}' must have 'model_name' field"
                )
            # Check for at least one of prompt, prompt_file
            if "prompt" not in archetype_config and "prompt_file" not in archetype_config:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Agent '{archetype_key}' must have either 'prompt' or 'prompt_file'"
                )
        
        # Get path to archetypes.yaml
        archetypes_path = get_archetypes_yaml_path()
        backup_path = archetypes_path + ".backup"
        
        # Create backup
        try:
            import shutil
            if os.path.exists(archetypes_path):
                shutil.copy(archetypes_path, backup_path)
        except Exception:
            pass  # If backup creation failed, continue
        
        # Save new configuration
        with open(archetypes_path, "w", encoding="utf-8") as f:
            # Write header with comments
            f.write("# Archetype (agent) configuration\n")
            f.write("# Adding and editing agents is done through this file\n")
            f.write("# You can use:\n")
            f.write("# 1. prompt: direct text\n")
            f.write("# 2. prompt_file: path to file with main prompt (e.g., prompts/sofiya_base.txt)\n")
            f.write("# 3. additional_prompts: list of additional prompts (files .txt/.md or text)\n")
            f.write("# 4. Combination of all above\n")
            f.write("#\n")
            f.write("# Maximum 3 agents for RADA mode\n\n")
            
            # Save configuration
            yaml.dump(archetypes_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        # Reload archetypes in memory
        reload_archetypes()
        global archetypes
        archetypes = load_archetypes()
        
        return JSONResponse(content={"status": "success", "message": "Configuration saved successfully"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving configuration: {str(e)}")

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
                    # Uvicorn Server has should_exit attribute for graceful shutdown
                    if hasattr(_server_instance, 'should_exit'):
                        _server_instance.should_exit = True
                        # Wait longer for graceful shutdown
                        time.sleep(2)
                    # Also try shutdown through server.shutdown()
                    if hasattr(_server_instance, 'shutdown'):
                        try:
                            _server_instance.shutdown()
                            time.sleep(1)
                        except Exception:
                            pass
                except Exception as e:
                    print(f"Error in graceful shutdown: {e}")
            
            # Always exit process through os._exit(0)
            # This ensures process will exit even if graceful shutdown failed
            time.sleep(0.5)
            os._exit(0)
        
        # Run shutdown in separate thread (not daemon, so process doesn't exit before shutdown)
        shutdown_thread = threading.Thread(target=do_shutdown, daemon=False)
        shutdown_thread.start()
        
        # Send response
        return JSONResponse(content={
            "status": "success",
            "message": "Server is shutting down..."
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error shutting down server: {str(e)}")