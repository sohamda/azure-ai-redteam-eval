#!/bin/bash
# startup.sh — Custom startup script for Azure App Service (Linux)
# Dependencies are installed by Oryx during deployment (SCM_DO_BUILD_DURING_DEPLOYMENT=true).
# This script only starts the FastAPI app.

set -e

# Start the FastAPI app with uvicorn
uvicorn src.app:app --host 0.0.0.0 --port 8000 --workers 2
