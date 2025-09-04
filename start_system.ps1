# EventsDC Document POC System Starter
# This script bypasses PowerShell execution policy issues

Write-Host "Starting EventsDC Document POC System..." -ForegroundColor Green
Write-Host ""

# Start API Server
Write-Host "Starting API Server..." -ForegroundColor Yellow
Start-Process -FilePath ".venv\Scripts\uvicorn.exe" -ArgumentList "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000" -WindowStyle Normal

# Wait for API to start
Write-Host "Waiting 5 seconds for API to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Start UI Server
Write-Host "Starting UI Server..." -ForegroundColor Yellow
Start-Process -FilePath ".venv\Scripts\streamlit.exe" -ArgumentList "run", "ui.py", "--server.port", "8501" -WindowStyle Normal

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "System Started Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "API Server: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "UI Server: http://localhost:8501" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
