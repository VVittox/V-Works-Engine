@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
)
if not exist ".venv\Scripts\python.exe" goto :failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "V Works Engine.spec"
if errorlevel 1 goto :failed
echo DEBUG BUILD: dist\V Works Engine\V Works Engine.exe
pause
exit /b 0
:failed
echo DEBUG BUILD FAILED.
pause
exit /b 1
