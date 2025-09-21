import os
import json
import re
from typing import List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from core.logic import load_archetypes, process_with_archetype
import aiofiles

app = FastAPI(title="Local Gemini Brain")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

HISTORY_DIR = "history"
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
    return FileResponse("static/favicon.ico")