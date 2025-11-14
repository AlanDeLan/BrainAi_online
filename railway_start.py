#!/usr/bin/env python3
"""
Railway startup script - handles PORT variable correctly
Updated: Force Railway to rebuild with ChromaDB disabled
"""
import os
import subprocess
import sys

# Get port from environment variable
port = os.environ.get("PORT", "8000")

print(f"🚀 Starting BrainAi on port {port}...")
print(f"📝 Build version: 5048e20 (ChromaDB disabled)")

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
