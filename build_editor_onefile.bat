@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "VENV_PY=.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3.12 -m venv .venv 2>nul
        if errorlevel 1 py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
)
if not exist "%VENV_PY%" (
    echo ERROR: Python 3 and venv are required.
    pause
    exit /b 1
)
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 goto :failed
"%VENV_PY%" -m pip install -r requirements-gpu.txt
if errorlevel 1 echo WARNING: GPU dependencies unavailable. CPU renderer remains available.
"%VENV_PY%" -m PyInstaller --noconfirm --clean "V Works Engine Onefile.spec"
if errorlevel 1 goto :failed
if not exist "dist\V Works Engine.exe" goto :failed
for %%F in ("dist\V Works Engine.exe") do echo SUCCESS: %%~fF
pause
exit /b 0
:failed
echo.
echo BUILD FAILED. Scroll up for the error details.
pause
exit /b 1
