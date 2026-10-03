@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run setup.bat first.
    pause
    exit /b 1
)
.venv\Scripts\python.exe -m src.train_model
if errorlevel 1 (
    echo Training failed. The previous active model was retained unless the failure occurred after publication.
) else (
    echo Training complete. Restart start.bat to load the new model version.
)
pause
