# ===========================================
# Production Environment Variables Template
# ===========================================
#
# ⚠️  ВАЖЛИВО: Це шаблон для Render Dashboard
# Копіюйте ці змінні в Render Environment Variables
# НЕ зберігайте реальні ключі в Git!

# === Required Variables ===

# Database (автоматично створюється Render)
DATABASE_URL=postgresql://user:password@host:port/database

# Security Keys (згенеруйте випадкові!)
# PowerShell: -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
SECRET_KEY=your-32-char-secret-key-here
SESSION_SECRET=your-32-char-session-secret-here

# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password-here  # Мінімум 8 символів

# AI Provider (оберіть один)
AI_PROVIDER=google_ai  # або openai
GOOGLE_API_KEY=your-google-ai-key-here
# OPENAI_API_KEY=your-openai-key-here
# OPENAI_BASE_URL=https://api.openai.com/v1

# Application Settings
ENVIRONMENT=production
DEBUG=false

# === Optional Variables ===

# CORS (додайте ваші домени)
CORS_ORIGINS=["https://your-domain.com","https://brainai-production.onrender.com"]
ALLOW_CREDENTIALS=true

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# JWT Settings
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Logging
LOG_LEVEL=INFO

# Server (Render встановлює автоматично)
# PORT=8000
# WORKERS=2

# === Приклади для різних середовищ ===

# Development:
# ENVIRONMENT=development
# DEBUG=true
# LOG_LEVEL=DEBUG

# Staging:
# ENVIRONMENT=staging
# DEBUG=false
# LOG_LEVEL=INFO

# Production:
# ENVIRONMENT=production
# DEBUG=false
# LOG_LEVEL=WARNING
