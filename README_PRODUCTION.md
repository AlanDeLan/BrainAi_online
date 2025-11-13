# 🚀 BrainAi - Production Ready

> Production-ready AI assistant with security, authentication, and automated deployment.

---

## ⚠️ ВАЖЛИВО: Почніть звідси!

### 🎯 Для розгортання на Render → **[START_HERE.md](START_HERE.md)**

Там покрокова інструкція що робити зараз!

---

## 📚 Документація

| Документ | Опис | Для кого |
|----------|------|----------|
| **[START_HERE.md](START_HERE.md)** ⭐ | **Покрокова інструкція розгортання** | **Почніть звідси!** |
| [QUICKSTART.md](QUICKSTART.md) | Швидкий старт (30 хвилин) | Для швидкого деплою |
| [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md) | Огляд усього що зроблено | Для розуміння архітектури |
| [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) | Детальна інструкція Render | Для детального розуміння |
| [SECURITY.md](SECURITY.md) | Security checklist | Для безпеки |
| [ENVIRONMENT_VARS.md](ENVIRONMENT_VARS.md) | Опис змінних середовища | Для налаштування |
| [FILES_CREATED.md](FILES_CREATED.md) | Список створених файлів | Для огляду змін |

---

## ✅ Що підготовлено

### 🔐 Безпека
- ✅ JWT автентифікація (core/auth.py)
- ✅ Rate limiting - 60/хв, 1000/год (core/rate_limit.py)
- ✅ Password hashing (bcrypt)
- ✅ Input validation (Pydantic)
- ✅ CORS налаштування
- ✅ Environment variables для секретів

### 🗄️ База даних
- ✅ PostgreSQL підтримка (core/database.py)
- ✅ SQLAlchemy ORM
- ✅ Автоматичні міграції
- ✅ Session management

### 🚀 DevOps
- ✅ GitHub Actions CI/CD (.github/workflows/deploy.yml)
- ✅ Automated testing
- ✅ Security scanning (Trivy)
- ✅ Auto-deployment на Render
- ✅ Health checks

### 📊 Моніторинг
- ✅ Enhanced health checks
- ✅ Metrics endpoints
- ✅ Structured logging
- ✅ Error tracking

---

## 🏗️ Архітектура

```
Client → Render → FastAPI → PostgreSQL
                    ↓
              AI Provider
            (Google/OpenAI)
```

**Middleware Stack:**
1. TrustedHost (security)
2. CORS (cross-origin)
3. RateLimit (DDoS protection)
4. GZip (compression)

**Security Layer:**
- JWT authentication
- Password hashing
- Token validation
- Role-based access

---

## 💡 Швидкий старт (для нетерплячих)

```powershell
# 1. Клонуйте репозиторій
git clone https://github.com/YOUR_USERNAME/brainai-production.git
cd brainai-production

# 2. Створіть .env
Copy-Item .env.example .env
notepad .env  # Додайте API ключі

# 3. Встановіть залежності
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 4. Запустіть локально
python main_production.py

# 5. Перевірте: http://localhost:8000
```

**Для продакшн → читайте [START_HERE.md](START_HERE.md)**

---

## 🔑 Environment Variables

### Обов'язкові:
```bash
DATABASE_URL=postgresql://...
SECRET_KEY=<32 символи>
SESSION_SECRET=<32 символи>
ADMIN_PASSWORD=<надійний пароль>
GOOGLE_API_KEY=<ваш ключ>
AI_PROVIDER=google_ai
ENVIRONMENT=production
DEBUG=false
```

Повний список → [ENVIRONMENT_VARS.md](ENVIRONMENT_VARS.md)

---

## 📡 API Endpoints

### Публічні (без автентифікації):
- `GET /` - Головна сторінка
- `GET /health` - Health check
- `POST /api/auth/login` - Отримати JWT токен

### Захищені (потрібен JWT):
- `POST /process` - Обробка тексту через AI
- `GET /api/metrics` - Метрики системи
- `GET /api/history` - Історія чатів

### Приклад використання:

```bash
# 1. Логін
curl -X POST https://your-app.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'

# 2. Використання AI
curl -X POST https://your-app.onrender.com/process \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Привіт!","archetype":"sofiya"}'
```

---

## 💰 Вартість

### Free Tier (90 днів):
- Web Service: **FREE**
- PostgreSQL: **FREE**

### Після 90 днів:
- **$14/міс** (Web + DB)

Детальніше → [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md#-вартість)

---

## 🔒 Security Checklist

Перед розгортанням:

- [ ] .env видалено з Git
- [ ] Нові API ключі створено
- [ ] SECRET_KEY згенеровано
- [ ] ADMIN_PASSWORD змінено
- [ ] CORS налаштовано
- [ ] Rate limiting активний

Повний чеклист → [SECURITY.md](SECURITY.md)

---

## 🆘 Troubleshooting

| Проблема | Рішення |
|----------|---------|
| "Database connection failed" | Перевірте DATABASE_URL в Environment Variables |
| "AI API key not found" | Додайте GOOGLE_API_KEY або OPENAI_API_KEY |
| "401 Unauthorized" | Отримайте новий токен через /api/auth/login |
| "429 Too Many Requests" | Зачекайте або збільште rate limit |

Детальніше → [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md#-troubleshooting)

---

## 📖 Навчальні матеріали

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Render Documentation](https://render.com/docs)
- [Pydantic Settings](https://docs.pydantic.dev/)
- [JWT Introduction](https://jwt.io/introduction)

---

## 🎯 Roadmap

- [x] JWT автентифікація
- [x] Rate limiting
- [x] PostgreSQL база
- [x] CI/CD pipeline
- [x] Security hardening
- [ ] Redis caching
- [ ] WebSocket support
- [ ] Multi-user system
- [ ] API rate limiting per user

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

- FastAPI for the amazing framework
- Render for easy deployment
- Google AI & OpenAI for AI capabilities

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/brainai-production/issues)
- **Render Support**: support@render.com
- **Documentation**: See files above

---

## ⚡ Quick Links

- 🚀 **[START HERE!](START_HERE.md)** - Покрокова інструкція
- 📖 [Full Documentation](DEPLOYMENT_SUMMARY.md)
- 🔐 [Security Guide](SECURITY.md)
- 💡 [Quick Start](QUICKSTART.md)

---

**Ready to deploy? → [START_HERE.md](START_HERE.md)** 🚀
