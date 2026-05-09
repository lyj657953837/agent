@echo off
REM Quick setup script for Analysis Agent System

echo ========================================
echo Analysis Agent System - Quick Setup
echo ========================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo [1/3] Creating .env file from template...
    copy .env.example .env
    echo ✓ .env file created
    echo.
    echo ⚠️  IMPORTANT: Please edit .env file with your actual configuration!
    echo    Open .env and update database credentials and other settings.
    echo.
) else (
    echo [1/3] .env file already exists, skipping...
    echo.
)

REM Install dependencies
echo [2/3] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ✗ Failed to install dependencies
    exit /b 1
)
echo ✓ Dependencies installed
echo.

REM Initialize database
echo [3/3] Checking database connection...
python -c "from analysis_agent_system.app.config import settings; print(f'Database URL: {settings.DATABASE_URL}')"
if errorlevel 1 (
    echo ✗ Configuration error. Please check your .env file.
    exit /b 1
)
echo ✓ Configuration loaded successfully
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit .env file with your actual configuration
echo 2. Run: python run_server.py
echo.
pause
