@echo off
rem One-shot MorphGNT SBLGNT ingest. Idempotent: wipes + reloads corpus 'sblgnt'.
set PYTHONUTF8=1
cd /d "%~dp0.."
if not exist data\morphgnt-sblgnt (
  git clone --depth 1 https://github.com/morphgnt/sblgnt data\morphgnt-sblgnt
)
set PYTHONPATH=service
service\.venv\Scripts\python.exe -m app.ingest.morphgnt
