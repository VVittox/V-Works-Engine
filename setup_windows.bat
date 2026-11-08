@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo   V Works Engine - Windows Setup
echo ==========================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher "py" was not found.
  echo Install Python 3.12 from python.org or with: winget install -e --id Python.Python.3.12
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating Python 3.12 virtual environment...
  py -3.12 -m venv .venv
  if errorlevel 1 goto :fail
)
echo Installing/updating dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Dependency installation failed. If you see getaddrinfo failed, check DNS/Internet access.
  goto :fail
)
echo.
echo Setup complete! Run start_editor.bat
pause
exit /b 0
:fail
echo Setup failed.
pause
exit /b 1
