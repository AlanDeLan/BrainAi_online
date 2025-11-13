"""
Configuration management for BrainAi_online.
"""
import os
import yaml
from typing import Dict, Any, Optional
from core.logger import logger

_config: Optional[Dict[str, Any]] = None

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file (optional)
    
    Returns:
        Configuration dictionary
    """
    global _config
    
    if _config is not None:
        return _config
    
    # Default configuration
    default_config = {
        "server": {
            "host": "127.0.0.1",
            "port": 8000,
            "reload": False
        },
        "logging": {
            "level": "INFO",
            "file": "logs/brainai_online.log",
            "max_bytes": 10485760,
            "backup_count": 5,
            "console": True,
            "file_enabled": True
        },
        "app": {
            "default_language": "uk",
            "supported_languages": ["uk", "en"],
            "max_chat_history": 1000,
            "auto_save_chat": True,
            "auto_save_vector_db": True
        },
        "vector_db": {
            "collection_name": "chat_memory",
            "persist_directory": "vector_db_storage",
            "n_results": 3
        },
        "ai_provider": {
            "default_provider": "google_ai",
            "timeout": 30,
            "max_retries": 3
        },
        "monitoring": {
            "enabled": True,
            "metrics_retention": 1000,
            "enable_health_check": True
        },
        "security": {
            "allow_cors": False,
            "cors_origins": []
        }
    }
    
    # Try to load from file
    if config_path is None:
        import sys
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller: look for config next to exe
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                if 'core' in base_dir:
                    base_dir = os.path.dirname(base_dir)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        config_path = os.path.join(base_dir, "config.yaml")
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f) or {}
                # Merge with default config
                _config = merge_config(default_config, file_config)
                logger.info(f"Configuration loaded from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}, using defaults")
            _config = default_config
    else:
        logger.info("No config file found, using default configuration")
        _config = default_config
    
    return _config

def merge_config(default: Dict, override: Dict) -> Dict:
    """
    Merge two configuration dictionaries recursively.
    
    Args:
        default: Default configuration
        override: Override configuration
    
    Returns:
        Merged configuration
    """
    result = default.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    return result

def get_config(key: Optional[str] = None, default: Any = None) -> Any:
    """
    Get configuration value.
    
    Args:
        key: Configuration key (e.g., "server.port" or "server")
        default: Default value if key not found
    
    Returns:
        Configuration value
    """
    config = load_config()
    
    if key is None:
        return config
    
    keys = key.split(".")
    value = config
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value

def reload_config():
    """Reload configuration from file."""
    global _config
    _config = None
    return load_config()








