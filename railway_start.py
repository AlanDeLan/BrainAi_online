#!/usr/bin/env python3
"""
Railway startup script - handles PORT variable correctly
"""
import os
import subprocess
import sys
from datetime import datetime

# Get port from environment variable
port = os.environ.get("PORT", "8000")

# Get git commit SHA from Railway environment
git_sha = os.environ.get("RAILWAY_GIT_COMMIT_SHA", "unknown")[:7]
build_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

print(f"🚀 Starting BrainAi on port {port}...")
print(f"📝 Build version: {git_sha}")
print(f"🕒 Build time: {build_time}")

# Start uvicorn with proper port
cmd = [
    "uvicorn",
    "main_production:app",
    "--host", "0.0.0.0",
    "--port", port,
    "--log-level", "info"
]

print(f"Running: {' '.join(cmd)}")

# Execute uvicorn
try:
    subprocess.run(cmd, check=True)
except subprocess.CalledProcessError as e:
    print(f"❌ Error starting server: {e}")
    sys.exit(1)
