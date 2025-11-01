import os
import yaml
import datetime
import json
from dotenv import load_dotenv

# --- Додаємо імпорт для Google Gemini ---
import google.generativeai as genai

# --- Додаємо імпорт для пошуку у векторній базі ---
try:
    from vector_db.client import search_chats
except ImportError:
    search_chats = None

# --- Конфігурація ---
# Завантажуємо .env файл (використовуємо dotenv_values для надійності)
from dotenv import dotenv_values

# Шукаємо .env в різних місцях
env_paths = [
    os.path.join(os.path.dirname(__file__), '..', '.env'),  # Біля core/logic.py
    os.path.join(os.path.dirname(__file__), '..', '..', '.env'),  # В корені проекту
    '.env',  # Поточна директорія
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

# Якщо не знайдено через dotenv_values, пробуємо load_dotenv
if not env_values or 'GOOGLE_API_KEY' not in env_values:
    load_dotenv(override=True)
    env_values = {'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY')}

try:
    api_key = env_values.get('GOOGLE_API_KEY') or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY не знайдено у файлі .env")
    # Встановлюємо в os.environ для сумісності
    os.environ['GOOGLE_API_KEY'] = api_key
    genai.configure(api_key=api_key)
    print("--- Google Gemini Client Configured Successfully ---")
except Exception as e:
    print(f"--- CRITICAL: Failed to configure Google Gemini client! Error: {e} ---")

HISTORY_DIR = "history"
os.makedirs(HISTORY_DIR, exist_ok=True)

archetype_cache = None

def load_prompt_file(file_path):
    """Завантажує промпт з файлу."""
    if not file_path or not os.path.exists(file_path):
        return None
    
    try:
        # Шукаємо в різних місцях
        possible_paths = [
            file_path,  # Абсолютний або відносний шлях
            os.path.join("prompts", file_path),  # В папці prompts
            os.path.join(os.path.dirname(__file__), "..", "prompts", file_path),
            os.path.join(os.path.dirname(__file__), "..", file_path),
        ]
        
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                with open(abs_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    return content
        
        return None
    except Exception as e:
        print(f"--- Warning: Failed to load prompt file '{file_path}': {e} ---")
        return None

def build_multistage_prompt(archetype_config):
    """
    Будує багатоступінчастий промпт з конфігурації архетипа.
    Підтримує:
    - prompt: прямий текст
    - prompt_file: шлях до файлу з основним промптом
    - additional_prompts: список додаткових промптів (файли або текст)
    """
    prompt_parts = []
    
    # 1. Основний промпт (з файлу або прямого тексту)
    base_prompt = None
    
    # Спочатку перевіряємо prompt_file
    if "prompt_file" in archetype_config:
        base_prompt = load_prompt_file(archetype_config["prompt_file"])
    
    # Якщо не знайдено в файлі, використовуємо prompt
    if not base_prompt:
        base_prompt = archetype_config.get("prompt", "")
    
    if base_prompt:
        prompt_parts.append(base_prompt)
    
    # 2. Додаткові промпти (можуть бути файли або текст)
    additional_prompts = archetype_config.get("additional_prompts", [])
    if isinstance(additional_prompts, str):
        # Якщо один рядок, робимо список
        additional_prompts = [additional_prompts]
    
    for add_prompt in additional_prompts:
        if not add_prompt:
            continue
        
        # Перевіряємо, чи це файл (закінчується на .txt, .md тощо)
        if isinstance(add_prompt, str) and any(add_prompt.endswith(ext) for ext in ['.txt', '.md']):
            loaded = load_prompt_file(add_prompt)
            if loaded:
                prompt_parts.append(loaded)
        else:
            # Це текст
            prompt_parts.append(str(add_prompt))
    
    # З'єднуємо всі частини
    return "\n\n".join(filter(None, prompt_parts))

def load_archetypes():
    """Завантажує архетипи з YAML-файлу з кешуванням."""
    global archetype_cache
    if archetype_cache is not None:
        return archetype_cache
    try:
        with open("archetypes.yaml", "r", encoding="utf-8") as f:
            archetype_cache = yaml.safe_load(f)
        
        # Для кожного архетипа будуємо повний промпт
        for archetype_name, config in archetype_cache.items():
            if isinstance(config, dict):
                # Будуємо багатоступінчастий промпт
                full_prompt = build_multistage_prompt(config)
                if full_prompt:
                    config["_full_prompt"] = full_prompt  # Кешуємо зібраний промпт
        
        print("--- Archetypes loaded successfully ---")
    except Exception as e:
        print(f"--- CRITICAL: Failed to load archetypes! Error: {e} ---")
        archetype_cache = {}
    return archetype_cache

def log_interaction(archetype_name, user_text, final_prompt, response):
    """Зберігає повну інформацію про взаємодію у файл."""
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
    Формує промпт, підтягує релевантний контекст з векторної бази,
    обирає потрібну модель Gemini, генерує відповідь і логує результат.
    """
    if not text or not archetype_name:
        return {"error": "Необхідно вказати текст і архетип."}

    archetype_config = archetypes.get(archetype_name)
    if not archetype_config:
        return {"error": f"Архетип '{archetype_name}' не знайдено."}

    model_name = archetype_config.get("model_name")
    if not model_name:
        return {"error": f"Для архетипа '{archetype_name}' не вказано model_name."}

    # Використовуємо зібраний багатоступінчастий промпт або збираємо на льоту
    if "_full_prompt" in archetype_config:
        system_prompt = archetype_config["_full_prompt"]
    else:
        # Якщо не був зібраний при завантаженні, збираємо зараз
        system_prompt = build_multistage_prompt(archetype_config) or archetype_config.get("prompt", "")

    # --- Додаємо релевантний контекст з векторної бази ---
    context = ""
    if search_chats:
        similar_chats = search_chats(text, n_results=2)
        if similar_chats:
            context = "\n\n".join([f"Контекст з минулого чату:\n{c['text']}" for c in similar_chats])

    full_prompt = f"{system_prompt}\n\n{context}\n\nОсь запит користувача:\n{text}"

    try:
        model = genai.GenerativeModel(model_name)
        gemini_response = model.generate_content(full_prompt)
        model_response = gemini_response.text.strip()
        log_interaction(archetype_name, text, full_prompt, model_response)
        return {"response": model_response}
    except Exception as e:
        error_message = f"Помилка під час звернення до Google Gemini: {e}"
        print(error_message)
        return {"error": error_message}