@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Crea primero el entorno .venv e instala requirements.txt.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" app.py --open
pause
