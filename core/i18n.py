"""
Internationalization (i18n) support for Local Brain.
"""
import os
import json
from typing import Dict, Optional
from core.logger import logger

# Default language
DEFAULT_LANGUAGE = "uk"

# Supported languages
SUPPORTED_LANGUAGES = ["uk", "en"]

# Translation dictionary
_translations: Dict[str, Dict[str, str]] = {}

def load_translations(language: str = DEFAULT_LANGUAGE) -> Dict[str, str]:
    """
    Load translations for a specific language.
    
    Args:
        language: Language code (uk, en)
    
    Returns:
        Dictionary with translations
    """
    global _translations
    
    if language not in SUPPORTED_LANGUAGES:
        logger.warning(f"Unsupported language: {language}, using default: {DEFAULT_LANGUAGE}")
        language = DEFAULT_LANGUAGE
    
    # Check if translations are already loaded
    if language in _translations:
        return _translations[language]
    
    # Try to load from file
    try:
        import sys
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller: look for translations in bundled resources
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        translations_file = os.path.join(base_path, "core", "translations", f"{language}.json")
        
        if os.path.exists(translations_file):
            with open(translations_file, "r", encoding="utf-8") as f:
                _translations[language] = json.load(f)
                logger.info(f"Loaded translations for language: {language}")
        else:
            # Use built-in translations
            _translations[language] = get_builtin_translations(language)
            logger.info(f"Using built-in translations for language: {language}")
    except Exception as e:
        logger.error(f"Failed to load translations for {language}: {e}", exc_info=True)
        _translations[language] = get_builtin_translations(language)
    
    return _translations[language]

def get_builtin_translations(language: str) -> Dict[str, str]:
    """
    Get built-in translations for a language.
    
    Args:
        language: Language code (uk, en)
    
    Returns:
        Dictionary with translations
    """
    if language == "uk":
        return {
            # UI Elements
            "app_title": "Local Brain",
            "new_chat": "Новий чат",
            "history": "Історія",
            "menu": "☰ Меню",
            "agent_settings": "⚙️ Налаштування агентів",
            "ai_provider": "🤖 AI Провайдер",
            "vector_db": "📊 Векторна БД",
            "end_session": "⛔ Завершити сеанс",
            "ready": "Готово до роботи. Оберіть архетип та поставте запитання.",
            "send": "Надіслати",
            "type_message": "Введіть повідомлення...",
            "loading": "Завантаження...",
            "error": "Помилка",
            "success": "Успіх",
            "save": "Зберегти",
            "cancel": "Скасувати",
            "delete": "Видалити",
            "edit": "Редагувати",
            "close": "Закрити",
            "select_language": "Оберіть мову",
            
            # Messages
            "chat_saved": "Чат збережено",
            "chat_deleted": "Чат видалено",
            "config_saved": "Конфігурацію збережено",
            "config_error": "Помилка збереження конфігурації",
            "server_shutdown": "Сервер завершує роботу...",
            "session_ended": "Сеанс завершено",
        }
    elif language == "en":
        return {
            # UI Elements
            "app_title": "Local Brain",
            "new_chat": "New Chat",
            "history": "History",
            "menu": "☰ Menu",
            "agent_settings": "⚙️ Agent Settings",
            "ai_provider": "🤖 AI Provider",
            "vector_db": "📊 Vector DB",
            "end_session": "⛔ End Session",
            "ready": "Ready to work. Select an archetype and ask a question.",
            "send": "Send",
            "type_message": "Type a message...",
            "loading": "Loading...",
            "error": "Error",
            "success": "Success",
            "save": "Save",
            "cancel": "Cancel",
            "delete": "Delete",
            "edit": "Edit",
            "close": "Close",
            "select_language": "Select Language",
            
            # Messages
            "chat_saved": "Chat saved",
            "chat_deleted": "Chat deleted",
            "config_saved": "Configuration saved",
            "config_error": "Error saving configuration",
            "server_shutdown": "Server is shutting down...",
            "session_ended": "Session ended",
        }
    else:
        # Fallback to Ukrainian
        return get_builtin_translations("uk")

def t(key: str, language: str = DEFAULT_LANGUAGE, default: Optional[str] = None) -> str:
    """
    Translate a key to the specified language.
    
    Args:
        key: Translation key
        language: Language code (uk, en)
        default: Default value if key not found
    
    Returns:
        Translated string
    """
    translations = load_translations(language)
    return translations.get(key, default or key)

def get_user_language(request) -> str:
    """
    Get user's preferred language from request.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Language code (uk, en)
    """
    # Check Accept-Language header
    accept_language = request.headers.get("Accept-Language", "")
    if accept_language:
        # Parse Accept-Language header (e.g., "en-US,en;q=0.9,uk;q=0.8")
        languages = accept_language.split(",")
        for lang in languages:
            lang_code = lang.split(";")[0].strip().lower()[:2]
            if lang_code in SUPPORTED_LANGUAGES:
                return lang_code
    
    # Check cookie
    language_cookie = request.cookies.get("language")
    if language_cookie and language_cookie in SUPPORTED_LANGUAGES:
        return language_cookie
    
    # Default to Ukrainian
    return DEFAULT_LANGUAGE








