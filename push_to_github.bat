@echo off
setlocal
set PATH=%LOCALAPPDATA%\Programs\Git\cmd;%PATH%
title Push PowerPilot to GitHub
color 0B
echo ==============================================================================
echo             PowerPilot -- Push to GitHub & Enable GitHub Pages
echo ==============================================================================
echo.
echo If you haven't created a GitHub repository yet:
echo 1. Open your browser and go to: https://github.com/new
echo 2. Name your repository: PowerPilot
echo 3. Leave "Add a README", ".gitignore", and "License" unchecked (we already made them)
echo 4. Click "Create repository"
echo.
echo ------------------------------------------------------------------------------
set /p REPO_URL="Paste your GitHub repository URL here (e.g. https://github.com/username/PowerPilot.git): "
if "%REPO_URL%"=="" (
    echo.
    echo [ERROR] No repository URL entered.
    pause
    exit /b 1
)

echo.
echo [1/2] Linking local repository to %REPO_URL%...
git remote remove origin 2>nul
git remote add origin %REPO_URL%
git branch -M main

echo.
echo [2/2] Pushing to GitHub (a sign-in window may appear to authorize GitHub)...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ==============================================================================
    echo [SUCCESS] Your code is now uploaded to GitHub!
    echo.
    echo Next step to make the website live on GitHub Pages:
    echo 1. Open your repository on GitHub
    echo 2. Go to "Settings" (top tab) -> "Pages" (left sidebar)
    echo 3. Under "Build and deployment", set:
    echo      Branch: main
    echo      Folder: /docs
    echo 4. Click "Save"
    echo.
    echo Your presentation site will be live at:
    echo   https://^<your-username^>.github.io/PowerPilot/
    echo ==============================================================================
) else (
    echo.
    echo [!] Push did not complete. If it asked for authentication, please sign in.
)

pause
