@echo off
setlocal
set PATH=%LOCALAPPDATA%\Programs\Git\cmd;%PATH%
title Push PowerPilot to GitHub
color 0B
echo ==============================================================================
echo             PowerPilot -- Pushing to GitHub & GitHub Pages
echo ==============================================================================
echo.
echo Target Repository:
echo   https://github.com/Ekzarmfs/PowerPilot.git
echo.
echo Linking remote and pushing to 'main' branch...
echo (If a GitHub sign-in window appears, please authorize your account)
echo.

git remote remove origin 2>nul
git remote add origin https://github.com/Ekzarmfs/PowerPilot.git
git branch -M main
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ==============================================================================
    echo [SUCCESS] Your repository has been pushed to GitHub!
    echo.
    echo Final step to turn on GitHub Pages:
    echo 1. Open: https://github.com/Ekzarmfs/PowerPilot/settings/pages
    echo 2. Under "Build and deployment":
    echo      Source: Deploy from a branch
    echo      Branch: main
    echo      Folder: /docs
    echo 3. Click "Save"
    echo.
    echo Your presentation site will be live at:
    echo   https://Ekzarmfs.github.io/PowerPilot/
    echo ==============================================================================
) else (
    echo.
    echo [!] Push encountered an issue. If you were prompted to sign in, please verify your credentials.
)

pause
