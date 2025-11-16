# 🧪 Інструкція з запуску тестів

**Дата:** 16 листопада 2025

---

## 📦 Встановлення залежностей для тестування

```bash
# Встановити pytest та необхідні пакети
pip install pytest pytest-asyncio httpx

# Або додати до requirements.txt:
# pytest==7.4.3
# pytest-asyncio==0.21.1
# httpx==0.25.1
```

---

## 🚀 Запуск тестів

### Запустити всі тести:
```bash
pytest
```

### Запустити тести з детальним виводом:
```bash
pytest -v
```

### Запустити тільки тести автентифікації:
```bash
pytest tests/test_auth.py -v
```

### Запустити конкретний тестовий клас:
```bash
pytest tests/test_auth.py::TestUserLogin -v
```

### Запустити конкретний тест:
```bash
pytest tests/test_auth.py::TestUserLogin::test_login_success -v
```

### Запустити з coverage:
```bash
pytest --cov=core --cov-report=html
```

---

## 📊 Структура тестів

```
tests/
├── __init__.py
├── test_api.py          # API тести (існуючі)
├── test_archetypes.py   # Тести архетипів (існуючі)
├── test_validation.py   # Тести валідації (існуючі)
├── test_vector_db.py    # Тести векторної БД (існуючі)
└── test_auth.py         # ✨ НОВІ тести автентифікації
```

---

## 🧪 Тестові класи в test_auth.py

### 1. `TestUserRegistration`
- ✅ `test_register_new_user_success` - успішна реєстрація
- ✅ `test_register_duplicate_email` - дублікат email
- ✅ `test_register_invalid_email` - невалідний email
- ✅ `test_register_weak_password` - слабкий пароль

### 2. `TestUserLogin`
- ✅ `test_login_success` - успішний вхід
- ✅ `test_login_wrong_password` - неправильний пароль
- ✅ `test_login_nonexistent_user` - неіснуючий користувач
- ✅ `test_login_empty_credentials` - пусті credentials
- ✅ `test_login_creates_session` - створення сесії

### 3. `TestJWTTokens`
- ✅ `test_valid_token_access` - доступ з валідним токеном
- ✅ `test_invalid_token_access` - доступ з невалідним токеном
- ✅ `test_expired_token_access` - доступ з expired токеном
- ✅ `test_missing_token_access` - доступ без токена
- ✅ `test_token_contains_user_info` - інформація в токені

### 4. `TestPasswordReset`
- ✅ `test_reset_admin_password_success` - успішний reset
- ✅ `test_reset_invalidates_old_sessions` - інвалідація сесій

### 5. `TestPasswordHashing`
- ✅ `test_password_hashing` - хешування працює
- ✅ `test_password_verification` - перевірка працює
- ✅ `test_different_passwords_different_hashes` - різні хеші
- ✅ `test_same_password_different_hashes` - salt працює

### 6. `TestUserIsolation`
- ✅ `test_user_can_only_access_own_data` - ізоляція даних
- ✅ `test_token_from_one_user_cannot_access_another` - безпека

### 7. `TestRateLimiting`
- ⏭️ `test_rate_limit_exceeded` - rate limiting (skipped)

---

## 🎯 Приклади використання

### Запустити тести login:
```bash
pytest tests/test_auth.py::TestUserLogin -v
```

**Очікуваний вивід:**
```
tests/test_auth.py::TestUserLogin::test_login_success PASSED          [ 20%]
tests/test_auth.py::TestUserLogin::test_login_wrong_password PASSED   [ 40%]
tests/test_auth.py::TestUserLogin::test_login_nonexistent_user PASSED [ 60%]
tests/test_auth.py::TestUserLogin::test_login_empty_credentials PASSED[ 80%]
tests/test_auth.py::TestUserLogin::test_login_creates_session PASSED  [100%]

========================== 5 passed in 2.34s ===========================
```

### Запустити з детальним логуванням:
```bash
pytest tests/test_auth.py -v -s
```

### Запустити тільки failed тести:
```bash
pytest --lf  # last failed
```

---

## 📈 Coverage

### Генерувати HTML звіт:
```bash
pytest --cov=core --cov-report=html
```

### Відкрити звіт:
```bash
# Windows
start htmlcov/index.html

# Linux/Mac
open htmlcov/index.html
```

---

## 🐛 Troubleshooting

### Помилка: "No module named 'pytest'"
```bash
pip install pytest
```

### Помилка: "No module named 'httpx'"
```bash
pip install httpx
```

### Помилка: "Database not initialized"
Тести використовують in-memory SQLite, не потребують PostgreSQL.

### Тести падають з "Token expired"
Перевірте часову зону системи та UTC.

---

## 📝 Додавання нових тестів

```python
# tests/test_auth.py

class TestNewFeature:
    """Тести для нової фічі"""
    
    def test_something(self, client, test_user):
        """Опис тесту"""
        # Arrange
        data = {"key": "value"}
        
        # Act
        response = client.post("/api/endpoint", json=data)
        
        # Assert
        assert response.status_code == 200
        assert "expected_key" in response.json()
```

---

## 🎓 Best Practices

1. **Використовуйте fixtures** для повторюваного коду
2. **Ізолюйте тести** - кожен тест незалежний
3. **Тестуйте edge cases** - пусті дані, великі дані, невалідні дані
4. **Перевіряйте статус коди** - 200, 400, 401, 403, 404, 500
5. **Тестуйте security** - unauthorized access, token validation

---

## ✅ Checklist перед commit

- [ ] Всі тести проходять: `pytest`
- [ ] Немає syntax errors: `python -m py_compile tests/test_auth.py`
- [ ] Coverage > 80%: `pytest --cov=core --cov-report=term-missing`
- [ ] Немає warnings: `pytest -W error`
- [ ] Code style: `flake8 tests/`

---

**Останнє оновлення:** 16 листопада 2025  
**Автор:** BrainAi Development Team
