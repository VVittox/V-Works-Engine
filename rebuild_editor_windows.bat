@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "V Works Engine.spec"
if errorlevel 1 exit /b 1
echo.
echo V Works Engine build complete.
echo dist\V Works Engine\V Works Engine.exe
pause
