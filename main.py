import os
import json
from typing import List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from core.logic import load_archetypes, process_with_archetype
import logging
import aiofiles

# --- Логування ---
logger = logging.getLogger("local_brain")
logging.basicConfig(level=logging.INFO)

# --- Модель вхідних даних для API ---
class ProcessRequest(BaseModel):
    text: str
    archetype: str

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

# --- Маршрути (API Endpoints) ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Віддає головну HTML сторінку."""
    return templates.TemplateResponse(
        "index.html", {"request": request, "archetypes": archetypes}
    )

@app.post("/process")
async def process_text(request: ProcessRequest):
    """Приймає текст і назву архетипа, повертає оброблений результат."""
    if not request.text or not request.archetype:
        logger.warning("Empty text or archetype in request")
        raise HTTPException(status_code=400, detail="Text and archetype are required")
    result = process_with_archetype(
        text=request.text,
        archetype_name=request.archetype,
        archetypes=archetypes
    )
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
    """Повертає вміст конкретного файлу історії."""
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

# --------------------------------------------