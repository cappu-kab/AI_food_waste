@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo Python not found. Install Python 3.10+ first.
    pause
    exit /b 1
  )
  .\.venv\Scripts\python.exe -m pip install --upgrade pip
  .\.venv\Scripts\pip.exe install -r requirements.txt
)

set MODEL_PATH=models\best.pt
set DEVICE=cpu
echo.
echo Starting Food Waste Lab...
echo   Scan page : http://localhost:8899/
echo   Lab site  : http://localhost:8899/site/
echo.
.\.venv\Scripts\python.exe webapp.py --model models\best.pt --device cpu --port 8899
pause
