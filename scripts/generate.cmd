@echo off
rem Headless generation pipeline. Examples:
rem   generate.cmd vocab --rank-from 1 --rank-to 40 --deck "GNT Vocab 1-40"
rem   generate.cmd parsing --book John --chapter 1 --parse-like "V- _PAI%%" --deck "John 1 parsing"
rem ANTHROPIC_API_KEY must NOT be set (the pipeline refuses if it is).
set PYTHONUTF8=1
cd /d "%~dp0.."
set PYTHONPATH=service
service\.venv\Scripts\python.exe -m app.gen.run %*
