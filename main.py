import os
import json
import re
from typing import List
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from core.logic import load_archetypes, process_with_archetype
import logging
import aiofiles

# --- Додаємо імпорт для векторної бази ---
from vector_db.client import search_chats, delete_chat

# --- Логування ---
logger = logging.getLogger("local_brain")
logging.basicConfig(level=logging.INFO)

# --- Модель вхідних даних для API ---
class ProcessRequest(BaseModel):
    text: str
    archetype: str
    chat_id: str = None

# --- Кешування архетипів ---
archetype_cache = None
def get_archetypes():
    global archetype_cache
    if archetype_cache is not None:
        return archetype_cache
    archetype_cache = load_archetypes()
    return archetype_cache

# --- Завантаження конфігурації при старті ---
archetypes = get_archetypes()
if archetypes:
    logger.info("--- Archetypes successfully loaded ---")
else:
    logger.critical("--- CRITICAL: Failed to load archetypes! ---")

# --- Константи ---
HISTORY_DIR = "history"

# ---------------------------------------------
app = FastAPI(title="Local Brain")

# --- Підключення роутера "Рада" ---
from conferences.rada import router as rada_router
app.include_router(rada_router)

# --- Налаштування статичних файлів та шаблонів ---
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
# ----------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Віддає головну HTML сторінку."""
    return templates.TemplateResponse(
        "index.html", {"request": request, "archetypes": archetypes}
    )

def get_chat_file(chat_id):
    return os.path.join(HISTORY_DIR, f"{chat_id}.json")

@app.post("/process")
async def process_text(request: Request):
    """Приймає текст, назву архетипа, chat_id і прапорець remember, повертає оброблений результат."""
    data = await request.json()
    text = data.get("text")
    archetype = data.get("archetype")
    remember = data.get("remember", True)
    chat_id = data.get("chat_id")
    if not text or not archetype:
        logger.warning("Empty text or archetype in request")
        raise HTTPException(status_code=400, detail="Text and archetype are required")
    result = process_with_archetype(
        text=text,
        archetype_name=archetype,
        archetypes=archetypes
    )
    # --- Зберігаємо чат як масив повідомлень у одному файлі ---
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

# --- БЛОК ДЛЯ РОБОТИ З ІСТОРІЄЮ ---
@app.get("/history", response_model=List[str])
async def get_history_list():
    """Повертає список файлів історії, відсортований від найновішого."""
    try:
        files = [f for f in os.listdir(HISTORY_DIR) if f.endswith('.json')]
        files.sort(reverse=True)
        return files
    except FileNotFoundError:
        return []

@app.get("/history/{filename}")
async def get_history_file(filename: str):
    """Повертає вміст конкретного файлу історії (масив повідомлень чату)."""
    # Захист від path-injection
    if "/" in filename or "\\" in filename or ".." in filename:
        logger.warning(f"Path injection attempt: {filename}")
        return JSONResponse(status_code=400, content={"error": "Invalid filename"})
    try:
        filepath = os.path.join(HISTORY_DIR, filename)
        if not os.path.abspath(filepath).startswith(os.path.abspath(HISTORY_DIR)):
            logger.warning(f"Access denied to file: {filename}")
            return JSONResponse(status_code=403, content={"error": "Access denied"})
        async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
        return JSONResponse(content=data)
    except FileNotFoundError:
        logger.warning(f"File not found: {filename}")
        return JSONResponse(status_code=404, content={"error": "File not found"})
    except Exception as e:
        logger.error(f"Error reading file {filename}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/history/{filename}")
async def delete_history_file(filename: str):
    """Видаляє файл історії та відповідний запис у векторній базі."""
    # Захист від path-injection
    if "/" in filename or "\\" in filename or ".." in filename:
        return JSONResponse(status_code=400, content={"error": "Invalid filename"})
    filepath = os.path.join(HISTORY_DIR, filename)
    if not os.path.exists(filepath):
        return JSONResponse(status_code=404, content={"error": "File not found"})
    try:
        # Витягуємо chat_id з імені файлу (до .json)
        chat_id = re.sub(r"\.json$", "", filename)
        os.remove(filepath)
        if delete_chat:
            delete_chat(chat_id)
        return JSONResponse(content={"status": "deleted"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})