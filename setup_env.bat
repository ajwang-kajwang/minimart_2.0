@echo off
setlocal

echo ==================================================
echo 🚀 Minimart Dependency Setup
echo ==================================================

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.10 or 3.11 and add it to PATH.
    pause
    exit /b 1
)

:: 2. Create Virtual Environment
if not exist "venv_tracking" (
    echo 🐍 Creating Virtual Environment (venv_tracking)...
    python -m venv venv_tracking
    echo    ✅ Created venv_tracking
) else (
    echo    ⚠️  venv_tracking already exists, skipping creation.
)

:: 3. Activate & Install
echo ⬇️  Installing Python Libraries...

:: CALL is important here to prevent the script from exiting after activation
call venv_tracking\Scripts\activate.bat

:: Upgrade pip
python -m pip install --upgrade pip

:: Install dependencies
:: Note: On Windows, 'picamera2' will be skipped automatically due to platform markers
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ❌ Dependency installation failed.
    echo    You might need "Desktop development with C++" from Visual Studio Build Tools
    echo    if a package tries to compile from source.
    pause
    exit /b 1
)

echo.
echo ==================================================
echo 🎉 Setup Complete!
echo ==================================================
echo 👉 To start working:
echo    1. venv_tracking\Scripts\activate
echo    2. python main.py
echo.
pause