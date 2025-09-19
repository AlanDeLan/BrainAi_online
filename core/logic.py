import os
import yaml
import datetime
import json
from dotenv import load_dotenv
import openai

# --- Конфігурація ---
load_dotenv()

try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY не знайдено у файлі .env")
    openai.api_key = api_key
    print("--- OpenAI Client Configured Successfully ---")
except Exception as e:
    print(f"--- CRITICAL: Failed to configure OpenAI client! Error: {e} ---")

HISTORY_DIR = "history"
os.makedirs(HISTORY_DIR, exist_ok=True)

archetype_cache = None

def load_archetypes():
    """Завантажує архетипи з YAML-файлу з кешуванням."""
    global archetype_cache
    if archetype_cache is not None:
        return archetype_cache
    try:
        with open("archetypes.yaml", "r", encoding="utf-8") as f:
            archetype_cache = yaml.safe_load(f)
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
    Формує промпт, обирає потрібну модель OpenAI, генерує відповідь і логує результат.
    """
    if not text or not archetype_name:
        return {"error": "Необхідно вказати текст і архетип."}

    archetype_config = archetypes.get(archetype_name)
    if not archetype_config:
        return {"error": f"Архетип '{archetype_name}' не знайдено."}
    
    model_name = archetype_config.get("model_name")
    if not model_name:
        return {"error": f"Для архетипа '{archetype_name}' не вказано model_name."}

    system_prompt = archetype_config.get("prompt", "")
    full_prompt = f"{system_prompt}\n\nОсь запит користувача:\n{text}"

    try:
        response = openai.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.7,
            max_tokens=1024
        )
        model_response = response.choices[0].message.content.strip()
        log_interaction(archetype_name, text, full_prompt, model_response)
        return {"response": model_response}
    except Exception as e:
        error_message = f"Помилка під час звернення до OpenAI: {e}"
        print(error_message)
        return {"error": error_message}