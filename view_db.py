"""
Скрипт для перегляду бази даних проекту
Використання: python view_db.py
"""
import os
import json
import sys
from pathlib import Path

# Налаштування кодування для коректного відображення кирилиці
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

print("=" * 60)
print("Перегляд бази даних Local Gemini Brain")
print("=" * 60)

# 1. Перегляд історії (JSON файли)
print("\n[1] Історія чатів (папка history/):")
print("-" * 60)
history_dir = Path("history")
if history_dir.exists():
    json_files = list(history_dir.glob("*.json"))
    if json_files:
        print(f"Знайдено {len(json_files)} файлів:\n")
        for file in sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
            size = file.stat().st_size
            print(f"  [+] {file.name}")
            print(f"     Розмір: {size} байт")
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        print(f"     Повідомлень: {len(data)}")
                    elif isinstance(data, dict):
                        print(f"     Тип: {data.get('type', 'unknown')}")
            except Exception as e:
                print(f"     Помилка читання: {e}")
            print()
    else:
        print("  Файлів не знайдено")
else:
    print("  Папка history/ не існує")

# 2. Перегляд ChromaDB векторної бази
print("\n[2] ChromaDB векторна база (vector_db_storage/):")
print("-" * 60)
try:
    import chromadb
    from chromadb.config import Settings
    
    db_path = Path("vector_db_storage")
    if db_path.exists():
        print(f"  Папка бази: {db_path.absolute()}")
        
        # Підключення до бази
        client = chromadb.Client(Settings(persist_directory=str(db_path)))
        collection = client.get_or_create_collection("chat_memory")
        
        # Отримуємо всі записи
        all_data = collection.get()
        
        if all_data['ids']:
            print(f"  Знайдено записів: {len(all_data['ids'])}\n")
            
            for i, chat_id in enumerate(all_data['ids'], 1):
                print(f"  [{i}] Chat ID: {chat_id}")
                
                # Отримуємо метадані
                if all_data['metadatas'] and i <= len(all_data['metadatas']):
                    metadata = all_data['metadatas'][i-1]
                    print(f"      Архетипи: {metadata.get('archetypes', 'N/A')}")
                    print(f"      Timestamp: {metadata.get('timestamp', 'N/A')}")
                    print(f"      Topic: {metadata.get('topic', 'N/A')}")
                
                # Отримуємо текст
                if all_data['documents'] and i <= len(all_data['documents']):
                    text = all_data['documents'][i-1]
                    preview = text[:100] + "..." if len(text) > 100 else text
                    print(f"      Текст: {preview}")
                
                print()
        else:
            print("  База даних порожня")
    else:
        print("  Папка vector_db_storage/ не існує (база ще не створена)")
        
except ImportError:
    print("  ChromaDB не встановлено. Встановіть: pip install chromadb")
except Exception as e:
    print(f"  Помилка при читанні ChromaDB: {e}")

# 3. Статистика
print("\n[3] Статистика:")
print("-" * 60)
if history_dir.exists():
    json_files = list(history_dir.glob("*.json"))
    total_size = sum(f.stat().st_size for f in json_files)
    print(f"  JSON файлів: {len(json_files)}")
    print(f"  Загальний розмір: {total_size / 1024:.2f} KB")

print("\n" + "=" * 60)

