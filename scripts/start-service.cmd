@echo off
rem Scriptorium backend — FastAPI on port 8012.
rem PYTHONUTF8=1 is non-negotiable: Greek/Hebrew text corrupts without it.
set PYTHONUTF8=1
cd /d "%~dp0.."
service\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir service --host 127.0.0.1 --port 8012
