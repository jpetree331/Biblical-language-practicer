@echo off
rem Load data\syllabus_map.greek.json into concepts + lessons (validating).
set PYTHONUTF8=1
cd /d "%~dp0.."
set PYTHONPATH=service
service\.venv\Scripts\python.exe -m app.curriculum %*
