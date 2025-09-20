import os
import sys
import subprocess
import time
import webbrowser

# --- Автоматичний перезапуск у venv ---
VENV_PATH = os.path.join(os.path.dirname(__file__), "venv", "bin", "python3")
if sys.executable != VENV_PATH and os.path.exists(VENV_PATH):
    print("Перезапуск у віртуальному середовищі...")
    os.execv(VENV_PATH, [VENV_PATH] + sys.argv)

def pip_install(package, import_name=None):
    try:
        __import__(import_name or package)
    except ImportError:
        print(f"Встановлення пакета: {package} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

required = [
    ("fastapi", None),
    ("uvicorn", None),
    ("jinja2", None),
    ("aiofiles", None),
    ("pydantic", None),
    ("python-dotenv", "dotenv"),
    ("openai", None),
    ("chromadb", None)
]

for pkg, import_name in required:
    pip_install(pkg, import_name)

def start_server():
    print("Запуск FastAPI-сервера...")
    # Використовуємо --reload, як у ручному режимі
    return subprocess.Popen([
        sys.executable, "-m", "uvicorn", "main:app",
        "--host", "127.0.0.1", "--port", "8000", "--reload"
    ])

if __name__ == '__main__':
    print("Стартує сервер у окремому процесі...")
    server_proc = start_server()
    # Чекаємо, поки сервер реально стане доступним
    import socket
    for _ in range(30):
        try:
            with socket.create_connection(("127.0.0.1", 8000), timeout=1):
                break
        except Exception:
            time.sleep(0.5)
    print("Відкриваємо браузер...")
    webbrowser.open("http://127.0.0.1:8000")
    print("Для завершення роботи натисніть Ctrl+C")
    try:
        server_proc.wait()
    except KeyboardInterrupt:
        print("Завершення роботи...")
        server_proc.terminate()