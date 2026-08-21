@echo off
echo Starting AutoCut backend on :8000 ...
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
