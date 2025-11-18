from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

app = FastAPI()

# Підключення статичних файлів
app.mount("/static", StaticFiles(directory="static"), name="static")

# Підключення шаблонів
templates = Jinja2Templates(directory="templates")

# Дозволені джерела для CORS
origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Головна сторінка з підтримкою мов
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, lang: str = "uk"):
    return templates.TemplateResponse("index.html", {"request": request, "lang": lang})