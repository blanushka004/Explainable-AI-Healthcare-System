@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo Python 3.12 is required. Install it with the Windows Python launcher, then retry.
        pause
        exit /b 1
    )
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed. Read the error above before continuing.
    pause
    exit /b 1
)
echo.
echo Setup complete. Run start.bat and open http://127.0.0.1:8000
pause
