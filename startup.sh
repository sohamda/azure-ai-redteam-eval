#!/bin/bash
# startup.sh — Custom startup script for Azure App Service (Linux)
# Runs pip install from requirements.txt then starts the FastAPI app

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI app with uvicorn
uvicorn src.app:app --host 0.0.0.0 --port 8000
