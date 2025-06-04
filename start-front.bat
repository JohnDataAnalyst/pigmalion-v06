@echo off
REM -- Démarrer l’application React dans une nouvelle fenêtre PowerShell --

start powershell -NoExit -Command "cd \"%~dp0frontend_react\"; npm start"
