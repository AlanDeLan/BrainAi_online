#!/bin/bash

# ===========================================
# Production Startup Script for Render
# ===========================================

set -e  # Exit on error

echo "======================================"
echo "🚀 Starting BrainAi Production Server"
echo "======================================"

# Check Python version
python --version

# Check required environment variables
echo "📋 Checking environment variables..."

required_vars=("DATABASE_URL" "SECRET_KEY" "SESSION_SECRET" "ADMIN_PASSWORD")

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: $var is not set"
        exit 1
    fi
    echo "✅ $var is set"
done

# Check AI provider configuration
if [ -z "$GOOGLE_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: No AI API key set. Set GOOGLE_API_KEY or OPENAI_API_KEY"
fi

# Run database migrations (if needed)
echo "📊 Running database migrations..."
# Add alembic migration here when ready

# Start the application
echo "🎯 Starting server..."
exec uvicorn main_production:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers ${WORKERS:-2} \
    --log-level ${LOG_LEVEL:-info} \
    --access-log \
    --proxy-headers \
    --forwarded-allow-ips='*'
