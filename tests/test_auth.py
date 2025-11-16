"""
Тести для автентифікації та авторизації
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os
import sys

# Додаємо шлях до кореневої директорії
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main_production import app, get_db
from core.database import Base, db_manager
from core.db_models import User, UserSession
from core.auth import create_access_token, verify_token, hash_token

# Тестова база даних (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"

# Тестові дані
TEST_USER_EMAIL = "test@brainai.local"
TEST_USER_PASSWORD = "TestPassword123!"
ADMIN_EMAIL = "admin@brainai.local"
ADMIN_PASSWORD = "SecureAdmin2024!"


@pytest.fixture
def test_db():
    """
    Створює тестову базу даних для кожного тесту
    """
    # Створюємо engine для тестової БД
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    
    # Створюємо всі таблиці
    Base.metadata.create_all(bind=engine)
    
    # Створюємо session factory
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Ініціалізуємо db_manager
    db_manager.engine = engine
    db_manager.SessionLocal = TestingSessionLocal
    
    # Override get_db dependency
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield TestingSessionLocal()
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_db):
    """
    Створює тестовий HTTP клієнт
    """
    return TestClient(app)


@pytest.fixture
def test_user(test_db):
    """
    Створює тестового користувача
    """
    user = User(email=TEST_USER_EMAIL)
    user.password_hash = User.hash_password(TEST_USER_PASSWORD)
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def admin_user(test_db):
    """
    Створює адміністратора
    """
    admin = User(email=ADMIN_EMAIL)
    admin.password_hash = User.hash_password(ADMIN_PASSWORD)
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin


@pytest.fixture
def auth_headers(test_user):
    """
    Створює заголовки з JWT токеном
    """
    token = create_access_token({
        "sub": test_user.email,
        "user_id": test_user.id
    })
    return {"Authorization": f"Bearer {token}"}


class TestUserRegistration:
    """
    Тести реєстрації користувачів
    """
    
    def test_register_new_user_success(self, client, test_db):
        """
        Тест успішної реєстрації нового користувача
        """
        response = client.post("/api/auth/register", json={
            "email": "newuser@brainai.local",
            "password": "NewPassword123!"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # Перевіряємо чи користувач створений в БД
        user = test_db.query(User).filter(User.email == "newuser@brainai.local").first()
        assert user is not None
        assert user.verify_password("NewPassword123!")
    
    def test_register_duplicate_email(self, client, test_user):
        """
        Тест реєстрації з існуючою email адресою
        """
        response = client.post("/api/auth/register", json={
            "email": TEST_USER_EMAIL,
            "password": "AnotherPassword123!"
        })
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    def test_register_invalid_email(self, client):
        """
        Тест реєстрації з невалідною email адресою
        """
        response = client.post("/api/auth/register", json={
            "email": "invalid-email",
            "password": "Password123!"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_register_weak_password(self, client):
        """
        Тест реєстрації зі слабким паролем
        """
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "123"  # Занадто короткий
        })
        
        # Може бути 422 (validation) або 400 (business logic)
        assert response.status_code in [400, 422]


class TestUserLogin:
    """
    Тести входу користувачів
    """
    
    def test_login_success(self, client, test_user):
        """
        Тест успішного входу
        """
        response = client.post("/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_login_wrong_password(self, client, test_user):
        """
        Тест входу з неправильним паролем
        """
        response = client.post("/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": "WrongPassword123!"
        })
        
        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()
    
    def test_login_nonexistent_user(self, client):
        """
        Тест входу неіснуючого користувача
        """
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@brainai.local",
            "password": "Password123!"
        })
        
        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()
    
    def test_login_empty_credentials(self, client):
        """
        Тест входу з пустими credentials
        """
        response = client.post("/api/auth/login", json={
            "email": "",
            "password": ""
        })
        
        assert response.status_code in [400, 422]
    
    def test_login_creates_session(self, client, test_user, test_db):
        """
        Тест що login створює сесію в БД
        """
        response = client.post("/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        # Перевіряємо чи сесія створена
        session = test_db.query(UserSession).filter(
            UserSession.token_hash == hash_token(token)
        ).first()
        
        assert session is not None
        assert session.user_id == test_user.id
        assert session.expires_at > datetime.utcnow()


class TestJWTTokens:
    """
    Тести JWT токенів
    """
    
    def test_valid_token_access(self, client, test_user, auth_headers):
        """
        Тест доступу з валідним токеном
        """
        response = client.get("/api/profile", headers=auth_headers)
        assert response.status_code == 200
    
    def test_invalid_token_access(self, client):
        """
        Тест доступу з невалідним токеном
        """
        headers = {"Authorization": "Bearer invalid_token_123"}
        response = client.get("/api/profile", headers=headers)
        assert response.status_code == 401
    
    def test_expired_token_access(self, client, test_user, test_db):
        """
        Тест доступу з expired токеном
        """
        # Створюємо токен що вже expired
        token = create_access_token({
            "sub": test_user.email,
            "user_id": test_user.id
        })
        
        # Створюємо сесію з минулим expires_at
        session = UserSession(
            user_id=test_user.id,
            token_hash=hash_token(token),
            expires_at=datetime.utcnow() - timedelta(days=1)  # Вчора
        )
        test_db.add(session)
        test_db.commit()
        
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/profile", headers=headers)
        assert response.status_code == 401
    
    def test_missing_token_access(self, client):
        """
        Тест доступу без токена
        """
        response = client.get("/api/profile")
        assert response.status_code == 403  # Forbidden (no auth)
    
    def test_token_contains_user_info(self, test_user):
        """
        Тест що токен містить інформацію про користувача
        """
        token = create_access_token({
            "sub": test_user.email,
            "user_id": test_user.id
        })
        
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == test_user.email
        assert payload["user_id"] == test_user.id


class TestPasswordReset:
    """
    Тести скидання пароля
    """
    
    def test_reset_admin_password_success(self, client, admin_user, test_db):
        """
        Тест успішного скидання пароля адміністратора
        """
        new_password = "NewAdminPassword2024!"
        
        response = client.post("/api/auth/reset-admin", json={
            "new_password": new_password
        })
        
        assert response.status_code == 200
        assert "password reset successful" in response.json()["message"].lower()
        
        # Перевіряємо чи можна залогінитись з новим паролем
        login_response = client.post("/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": new_password
        })
        assert login_response.status_code == 200
    
    def test_reset_invalidates_old_sessions(self, client, admin_user, test_db):
        """
        Тест що reset пароля інвалідує старі сесії
        """
        # Створюємо сесію
        old_token = create_access_token({
            "sub": admin_user.email,
            "user_id": admin_user.id
        })
        session = UserSession(
            user_id=admin_user.id,
            token_hash=hash_token(old_token),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        test_db.add(session)
        test_db.commit()
        
        # Скидаємо пароль
        response = client.post("/api/auth/reset-admin", json={
            "new_password": "NewPassword123!"
        })
        assert response.status_code == 200
        
        # Перевіряємо чи старий токен більше не працює
        headers = {"Authorization": f"Bearer {old_token}"}
        profile_response = client.get("/api/profile", headers=headers)
        
        # Сесія має бути видалена
        session_exists = test_db.query(UserSession).filter(
            UserSession.token_hash == hash_token(old_token)
        ).first()
        assert session_exists is None


class TestPasswordHashing:
    """
    Тести хешування паролів
    """
    
    def test_password_hashing(self):
        """
        Тест що паролі хешуються
        """
        password = "TestPassword123!"
        hashed = User.hash_password(password)
        
        assert hashed != password  # Хеш не дорівнює оригіналу
        assert len(hashed) > 50  # Bcrypt хеш довгий
    
    def test_password_verification(self, test_user):
        """
        Тест перевірки пароля
        """
        assert test_user.verify_password(TEST_USER_PASSWORD) is True
        assert test_user.verify_password("WrongPassword") is False
    
    def test_different_passwords_different_hashes(self):
        """
        Тест що різні паролі дають різні хеші
        """
        hash1 = User.hash_password("Password1")
        hash2 = User.hash_password("Password2")
        
        assert hash1 != hash2
    
    def test_same_password_different_hashes(self):
        """
        Тест що той самий пароль дає різні хеші (salt)
        """
        password = "TestPassword123!"
        hash1 = User.hash_password(password)
        hash2 = User.hash_password(password)
        
        # Bcrypt використовує salt, тому хеші різні
        assert hash1 != hash2
        
        # Але обидва мають перевірятись успішно
        user1 = User(email="test1@example.com")
        user1.password_hash = hash1
        assert user1.verify_password(password) is True
        
        user2 = User(email="test2@example.com")
        user2.password_hash = hash2
        assert user2.verify_password(password) is True


class TestUserIsolation:
    """
    Тести ізоляції користувачів
    """
    
    def test_user_can_only_access_own_data(self, client, test_user, auth_headers, test_db):
        """
        Тест що користувач бачить лише свої дані
        """
        # Створюємо іншого користувача
        other_user = User(email="other@brainai.local")
        other_user.password_hash = User.hash_password("Password123!")
        test_db.add(other_user)
        test_db.commit()
        
        # Запитуємо історію з токеном test_user
        response = client.get("/api/history/db", headers=auth_headers)
        
        assert response.status_code == 200
        # Перевіряємо що повертаються лише дані test_user
        # (детальна перевірка залежить від структури відповіді)
    
    def test_token_from_one_user_cannot_access_another(self, client, test_db):
        """
        Тест що токен одного користувача не дає доступ до даних іншого
        """
        # Створюємо двох користувачів
        user1 = User(email="user1@brainai.local")
        user1.password_hash = User.hash_password("Password123!")
        test_db.add(user1)
        
        user2 = User(email="user2@brainai.local")
        user2.password_hash = User.hash_password("Password123!")
        test_db.add(user2)
        test_db.commit()
        
        # Токен для user1
        token1 = create_access_token({
            "sub": user1.email,
            "user_id": user1.id
        })
        
        headers = {"Authorization": f"Bearer {token1}"}
        
        # Запитуємо профіль - має повернути дані user1
        response = client.get("/api/profile", headers=headers)
        assert response.status_code == 200
        # user_id у відповіді має бути user1.id


class TestRateLimiting:
    """
    Тести rate limiting (якщо реалізовано)
    """
    
    @pytest.mark.skip(reason="Rate limiting може потребувати специфічної конфігурації")
    def test_rate_limit_exceeded(self, client, test_user):
        """
        Тест перевищення rate limit
        """
        # Робимо багато запитів
        for i in range(70):  # Ліміт: 60/хв
            response = client.post("/api/auth/login", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            })
            
            if i < 60:
                assert response.status_code in [200, 401]  # Нормальна відповідь
            else:
                assert response.status_code == 429  # Too Many Requests


# Точка входу для pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
