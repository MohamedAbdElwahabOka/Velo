@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
    exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python main.py
    exit /b %ERRORLEVEL%
)

echo Python was not found. Install Python 3.11+ or create .venv first.
pause
exit /b 1
