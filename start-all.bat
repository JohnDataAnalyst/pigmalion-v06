@echo off
REM -- Exécute simultanément back et front --

call "%~dp0start-back.bat"
call "%~dp0start-front.bat"
