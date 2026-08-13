@echo off
rem Build a reviewed chapter's vocab + parsing decks: build-chapter.cmd greek 3
set PYTHONUTF8=1
cd /d "%~dp0.."
set PYTHONPATH=service
service\.venv\Scripts\python.exe -m app.gen.build_chapter %*
