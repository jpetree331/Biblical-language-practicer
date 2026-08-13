@echo off
rem Zip data\ (the SQLite DB and local corpora) into backups\ with a timestamp.
cd /d "%~dp0.."
set PYTHONUTF8=1
for /f %%i in ('service\.venv\Scripts\python.exe -c "from datetime import datetime; print(datetime.now().strftime('%%Y%%m%%d-%%H%%M%%S'))"') do set STAMP=%%i
powershell -NoProfile -Command "Compress-Archive -Path 'data' -DestinationPath ('backups\scriptorium-data-' + '%STAMP%' + '.zip')"
echo Backed up data\ to backups\scriptorium-data-%STAMP%.zip
