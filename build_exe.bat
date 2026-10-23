@echo off
title Building PowerPilot Windows Standalone Executable
color 0B
echo ==============================================================================
echo       PowerPilot -- Standalone Windows 11 Executable Builder (PyInstaller)
echo ==============================================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH!
    echo Please install Python 3.10+ and check "Add Python to PATH".
    pause
    exit /b 1
)

echo [1/4] Ensuring PyInstaller and dependencies are installed...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [2/4] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist PowerPilot.spec del /f /q PowerPilot.spec

echo.
echo [3/4] Compiling Standalone Executable (PowerPilot.exe)...
pyinstaller --noconsole --onefile ^
    --name "PowerPilot" ^
    --collect-all customtkinter ^
    --add-data "core;core" ^
    --add-data "config;config" ^
    --add-data "ui;ui" ^
    main.py

if %errorlevel% neq 0 (
    echo [ERROR] Compilation failed!
    pause
    exit /b 1
)

echo.
echo [4/4] Build Succeeded!
echo ==============================================================================
echo Standalone executable created at:
echo   dist\PowerPilot.exe
echo.
echo You can run this executable on any Windows 10/11 system without installing Python.
echo ==============================================================================
pause
