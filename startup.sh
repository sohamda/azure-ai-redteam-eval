#!/bin/bash
# startup.sh — Custom startup script for Azure App Service (Linux)
# Runs pip install from requirements.txt then starts the FastAPI app

# Install runtime-only dependencies (slim — no eval/test packages)
pip install --no-cache-dir -r requirements-app.txt

# Start the FastAPI app with uvicorn
uvicorn src.app:app --host 0.0.0.0 --port 8000
