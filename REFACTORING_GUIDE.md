# 🔧 Рефакторинг main.py та main_production.py

**Дата:** 16 листопада 2025  
**Статус:** Рекомендації для поступової міграції

---

## 📋 Проблема

`main.py` та `main_production.py` мають **значне дублювання коду**:
- Обидва визначають схожі endpoints
- Обидва імпортують ті самі залежності
- `main_production.py` імпортує `app` з `main.py` та додає middleware

---

## ✅ Рекомендована архітектура

### Варіант 1: Модульна структура (Рекомендовано)

```
project/
├── main.py                    # Development entry point (простий)
├── main_production.py         # Production entry point (з middleware)
├── core/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py           # Auth endpoints
│   │   ├── chat.py           # Chat/process endpoints
│   │   ├── history.py        # History endpoints
│   │   ├── files.py          # File upload endpoints
│   │   ├── archetypes.py     # Archetype endpoints
│   │   └── stats.py          # Statistics endpoints
│   ├── auth.py
│   ├── database.py
│   └── ...
```

**main.py (Development):**
```python
from fastapi import FastAPI
from core.api import auth, chat, history, files, archetypes, stats

app = FastAPI()

# Register routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(history.router, prefix="/api/history", tags=["history"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(archetypes.router, prefix="/api/archetypes", tags=["archetypes"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")
```

**main_production.py (Production):**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from core.rate_limit import RateLimitMiddleware
from core.api import auth, chat, history, files, archetypes, stats

app = FastAPI(lifespan=lifespan)

# Production middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.add_middleware(RateLimitMiddleware)

# Register same routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(history.router, prefix="/api/history", tags=["history"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(archetypes.router, prefix="/api/archetypes", tags=["archetypes"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")
```

---

## 📝 Приклад: core/api/auth.py

```python
"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import authenticate_user, create_access_token, create_user_session
from core.models import LoginRequest, RegisterRequest

router = APIRouter()


@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """User login endpoint"""
    user = authenticate_user(request.email, request.password, db)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    
    token = create_access_token({
        "sub": user.email,
        "user_id": user.id
    })
    
    create_user_session(user.id, token, db)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 7 * 24 * 60 * 60
    }


@router.post("/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """User registration endpoint"""
    from core.db_models import User
    
    # Check if user exists
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(400, "Email already registered")
    
    # Create new user
    user = User(email=request.email)
    user.password_hash = User.hash_password(request.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create token
    token = create_access_token({
        "sub": user.email,
        "user_id": user.id
    })
    
    create_user_session(user.id, token, db)
    
    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/reset-admin")
async def reset_admin_password(request: dict, db: Session = Depends(get_db)):
    """Reset admin password"""
    from core.db_models import User, UserSession
    
    # Delete old admin
    admin = db.query(User).filter(User.email == "admin@brainai.local").first()
    if admin:
        # Invalidate all sessions
        db.query(UserSession).filter(UserSession.user_id == admin.id).delete()
        db.delete(admin)
        db.commit()
    
    # Create new admin
    new_admin = User(email="admin@brainai.local")
    new_admin.password_hash = User.hash_password(request["new_password"])
    db.add(new_admin)
    db.commit()
    
    return {"message": "Admin password reset successful"}
```

---

## 📝 Приклад: core/api/chat.py

```python
"""
Chat processing endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import get_current_user_id
from core.models import ProcessRequest
from core.logic import process_with_archetype
from core.db_models import ChatMessage
import uuid

router = APIRouter()


@router.post("/process")
async def process_message(
    request: ProcessRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Process user message with AI"""
    # Validate
    if not request.text or not request.text.strip():
        raise HTTPException(400, "Text cannot be empty")
    
    # Generate chat_id if new
    chat_id = request.chat_id or str(uuid.uuid4())
    
    # Get next message index
    last_message = db.query(ChatMessage)\
        .filter(
            ChatMessage.user_id == current_user_id,
            ChatMessage.chat_id == chat_id
        )\
        .order_by(ChatMessage.message_index.desc())\
        .first()
    
    next_index = (last_message.message_index + 1) if last_message else 0
    
    # Save user message
    user_msg = ChatMessage(
        user_id=current_user_id,
        chat_id=chat_id,
        role="user",
        content=request.text.strip(),
        message_index=next_index
    )
    db.add(user_msg)
    db.commit()
    
    # Process with AI
    try:
        response = await process_with_archetype(
            text=request.text,
            chat_id=chat_id,
            user_id=current_user_id,
            archetype_id=request.archetype_id
        )
    except Exception as e:
        raise HTTPException(500, f"AI processing failed: {str(e)}")
    
    # Save assistant message
    assistant_msg = ChatMessage(
        user_id=current_user_id,
        chat_id=chat_id,
        role="assistant",
        content=response,
        message_index=next_index + 1
    )
    db.add(assistant_msg)
    db.commit()
    
    return {
        "response": response,
        "chat_id": chat_id
    }
```

---

## 📝 Приклад: core/api/files.py

```python
"""
File upload and processing endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import get_current_user_id_optional
from main import MAX_FILE_SIZE, ALLOWED_MIME_TYPES
import os

router = APIRouter()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id_optional)
):
    """Upload and process a file"""
    # Validate file size
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            413,
            f"File too large. Max: {MAX_FILE_SIZE / 1024 / 1024:.1f}MB"
        )
    
    if file_size == 0:
        raise HTTPException(400, "File is empty")
    
    # Validate MIME type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            415,
            f"Unsupported file type: {file.content_type}"
        )
    
    # Process file...
    # (existing logic)
    
    return {"message": "File uploaded successfully"}
```

---

## 🚀 План міграції

### Крок 1: Створити структуру папок
```bash
mkdir core/api
touch core/api/__init__.py
touch core/api/auth.py
touch core/api/chat.py
touch core/api/history.py
touch core/api/files.py
touch core/api/archetypes.py
touch core/api/stats.py
```

### Крок 2: Винести auth endpoints
1. Скопіювати всі `/api/auth/*` endpoints з `main.py`
2. Перенести в `core/api/auth.py` як `router.post()`
3. Імпортувати в `main.py`: `from core.api.auth import router as auth_router`
4. Додати: `app.include_router(auth_router, prefix="/api/auth")`

### Крок 3: Винести chat endpoints
1. Перенести `/api/process` в `core/api/chat.py`
2. Імпортувати та додати router

### Крок 4: Винести інші endpoints
- History → `core/api/history.py`
- Files → `core/api/files.py`
- Archetypes → `core/api/archetypes.py`
- Stats → `core/api/stats.py`

### Крок 5: Оновити main_production.py
```python
# Замість:
from main import app as original_app

# Робимо:
from core.api import auth, chat, history, files, archetypes, stats

app = FastAPI(lifespan=lifespan)

# Middleware
app.add_middleware(...)

# Routers
app.include_router(auth.router, prefix="/api/auth")
app.include_router(chat.router, prefix="/api")
# ...
```

### Крок 6: Спростити main.py
```python
# main.py стає просто точкою входу для development
from core.api import auth, chat, history, files

app = FastAPI()
app.include_router(auth.router, prefix="/api/auth")
app.include_router(chat.router, prefix="/api")
# ...
```

---

## ⚠️ Важливі зауваження

### 1. **Не рушати зараз якщо працює**
- Поточна архітектура функціональна
- Рефакторинг потребує ретельного тестування
- Краще робити поступово, endpoint за endpoint

### 2. **Тестування після кожного кроку**
```bash
# Після кожного перенесення endpoint:
pytest tests/
python -m pytest tests/test_api.py -v
```

### 3. **Backward compatibility**
- Зберегти старі імпорти як deprecated
- Додати warnings про майбутні зміни

### 4. **Альтернатива: Залишити як є**
Якщо `main_production.py` просто додає middleware до `main.py`:
```python
# main_production.py
from main import app  # Використовуємо app з main.py

# Додаємо тільки production middleware
app.add_middleware(GZipMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(CORSMiddleware)

# Додаємо lifespan для startup/shutdown
# (через wrapper або monkey-patching)
```

Це **простіше** і менш ризиковано, але залишає дублювання.

---

## 📊 Порівняння підходів

| Підхід | Переваги | Недоліки | Складність |
|--------|----------|----------|------------|
| **Поточний** | Працює, простий | Дублювання коду | ⭐ |
| **Middleware wrapper** | Мінімальні зміни | Залишається дублювання | ⭐⭐ |
| **Модульні routers** | Чистий код, DRY | Потребує тестування | ⭐⭐⭐⭐ |

---

## 🎯 Рекомендація

**Для поточного проекту:**
1. ✅ Залишити як є (працює стабільно)
2. ✅ Додати TODO коментарі для майбутнього рефакторингу
3. ✅ Створити PoC (proof of concept) для 1-2 endpoints
4. ⏳ Мігрувати поступово при наявності часу та тестів

**Для нових проектів:**
- Одразу використовувати модульну структуру з роутерами

---

## 📝 TODO коментарі для коду

Додати в `main.py` та `main_production.py`:

```python
# TODO: Refactor to modular router structure
# See REFACTORING_GUIDE.md for migration plan
# Priority: MEDIUM (after test coverage reaches 80%)
```

---

**Останнє оновлення:** 16 листопада 2025  
**Автор:** BrainAi Development Team
