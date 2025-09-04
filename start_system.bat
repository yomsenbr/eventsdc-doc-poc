@echo off
echo Starting EventsDC Document POC System...
echo.

echo Starting API Server...
start "API Server" cmd /k ".venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000"

echo Waiting 5 seconds for API to start...
timeout /t 5 /nobreak > nul

echo Starting UI Server...
start "UI Server" cmd /k ".venv\Scripts\streamlit.exe run ui.py --server.port 8501"

echo.
echo ========================================
echo System Started Successfully!
echo ========================================
echo API Server: http://127.0.0.1:8000
echo UI Server: http://localhost:8501
echo.
echo Press any key to exit this window...
pause > nul
