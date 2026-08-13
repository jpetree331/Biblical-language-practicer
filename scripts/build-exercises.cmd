@echo off
rem Generate translate + compose exercises for a chapter: build-exercises.cmd greek 8 [--count 3]
set PYTHONUTF8=1
cd /d "%~dp0.."
set PYTHONPATH=service
service\.venv\Scripts\python.exe -m app.gen.exercises %*
