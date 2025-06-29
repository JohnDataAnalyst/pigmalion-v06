@echo off
rem ========= start-back.bat =========
rem Lance le backend FastAPI dans une nouvelle fenêtre PowerShell

rem Chemin racine (dossier qui contient "backend\")
set "ROOT=%~dp0"

start "" powershell -NoExit -ExecutionPolicy Bypass -Command ^
    "cd '%ROOT%'; " ^
    " & '%ROOT%venv\Scripts\Activate.ps1'; " ^
    " python -m uvicorn backend.main:app --reload --port 8000"
