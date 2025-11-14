#!/bin/bash
# Simple startup script for Railway

set -e

echo "🚀 Starting BrainAi on port ${PORT:-8000}..."

# Start uvicorn
exec uvicorn main_production:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --log-level info

