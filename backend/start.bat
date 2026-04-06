@echo off
echo ====================================
echo Starting ARS Backend Environment...
echo ====================================

IF NOT EXIST ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing requirements...
pip install -r requirements.txt

echo Starting server...
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
