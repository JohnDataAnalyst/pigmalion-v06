@echo off
REM -- Démarrer le backend FastAPI dans une nouvelle fenêtre PowerShell --

start powershell -NoExit -Command "cd \"%~dp0backend\"; . \"%~dp0venv\\Scripts\\Activate.ps1\"; python -m uvicorn main:app --reload --port 8000"
