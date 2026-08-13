@echo off
rem Auto-draft data\syllabus_map.greek.json from the Machen lesson texts.
rem Requires the Machen text ingested (python -m app.ingest.machen) and no
rem ANTHROPIC_API_KEY in the environment (subscription auth only).
set PYTHONUTF8=1
cd /d "%~dp0.."
set PYTHONPATH=service
service\.venv\Scripts\python.exe -m app.gen.syllabus
