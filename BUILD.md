# Інструкції зі збірки програми

## Варіант 1: PyInstaller (Рекомендовано для Windows)

### Крок 1: Встановити PyInstaller
```bash
pip install pyinstaller
```

### Крок 2: Оновити run_app.spec (якщо потрібно)
Файл `run_app.spec` вже налаштований, але можна додати:
- Іконку програми
- Додаткові файли
- Налаштування оптимізації

### Крок 3: Зібрати exe
```bash
pyinstaller run_app.spec
```

### Крок 4: Результат
Файл `run_app.exe` буде в папці `dist/`

### Крок 5: Тестування
1. Скопіюйте `dist/run_app.exe` в окрему папку
2. Створіть файл `.env` з `GOOGLE_API_KEY=ваш_ключ`
3. Запустіть `run_app.exe`

---

## Варіант 2: Docker (Для кроссплатформенності)

### Крок 1: Встановити Docker
Завантажте та встановіть [Docker Desktop](https://www.docker.com/products/docker-desktop)

### Крок 2: Створити образ
```bash
docker build -t local-gemini .
```

### Крок 3: Запустити контейнер
```bash
docker run -p 8000:8000 -e GOOGLE_API_KEY=ваш_ключ local-gemini
```

Або використати docker-compose:
```bash
# Створіть .env файл з GOOGLE_API_KEY
docker-compose up
```

### Крок 4: Доступ до програми
Відкрийте браузер: http://localhost:8000

---

## Варіант 3: Portable (Найпростіший)

### Крок 1: Підготувати розповсюдження
Створіть папку з такими файлами:
```
local-gemini/
├── main.py
├── run_app.py
├── requirements.txt
├── archetypes.yaml
├── prompts/
├── templates/
├── static/
├── start_server.ps1
└── .env (з GOOGLE_API_KEY)
```

### Крок 2: Інструкції для користувача
1. Встановити Python 3.11+
2. Запустити `start_server.ps1`
3. Програма автоматично встановить залежності

---

## Покращення run_app.spec для продакшн

### Додати іконку:
```python
exe = EXE(
    ...
    icon='static/favicon.ico',  # Додати іконку
    ...
)
```

### Додати додаткові файли:
```python
datas += [
    ('archetypes.yaml', '.'),
    ('prompts', 'prompts'),
]
```

### Оптимізація розміру:
```python
exe = EXE(
    ...
    upx=True,  # Вже включено - стиснення
    optimize=2,  # Оптимізація Python коду
    ...
)
```

---

## Рекомендації для розповсюдження

### Для Windows:
1. **PyInstaller** - створює `.exe` файл
2. Додати інструкцію по налаштуванню `.env`
3. Можна створити інсталятор (Inno Setup)

### Для кроссплатформенності:
1. **Docker** - працює всюди
2. Або збирати PyInstaller для кожної платформи

### Для швидкого тестування:
1. **Portable** - використовувати `start_server.ps1`












