@echo off
cd /d "%~dp0"
if not exist .venv py -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if not exist .env (
  copy .env.example .env >nul
  echo .env file created. Add all three API keys, then run this file again.
  notepad .env
  pause
  exit /b 0
)
start http://127.0.0.1:5000
python app.py
