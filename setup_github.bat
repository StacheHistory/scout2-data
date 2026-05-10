@echo off
:: ============================================================
::  Scout-2 GitHub One-Time Setup
::  Run this ONCE to connect your Scout2 folder to GitHub
::  GitHub: https://github.com/StacheHistory/scout2-data
:: ============================================================

title Scout-2 GitHub Setup

echo.
echo ============================================================
echo  Scout-2 GitHub One-Time Setup
echo ============================================================
echo.
echo This will connect C:\InvestingWithSPACE\Scout2 to:
echo https://github.com/StacheHistory/scout2-data
echo.
echo Make sure you have already created the repo on GitHub.com
echo before running this script.
echo.
pause

:: ── Navigate to Scout2 folder ────────────────────────────────
cd C:\InvestingWithSPACE\Scout2

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Could not find C:\InvestingWithSPACE\Scout2
    pause
    exit /b 1
)

:: ── Configure Git identity (required for commits) ────────────
echo.
echo [1/5] Configuring Git identity...
git config --global user.name "StacheHistory"
git config --global user.email "your@email.com"
echo       Done. Edit your email above if needed.

:: ── Initialize git repo in Scout2 folder ─────────────────────
echo.
echo [2/5] Initializing local git repository...
git init
git branch -M main

:: ── Create .gitignore to exclude raw XML audit files ─────────
echo.
echo [3/5] Creating .gitignore...
(
echo # Scout-2 gitignore
echo xml_audit/
echo __pycache__/
echo *.pyc
echo *.log
) > .gitignore

:: ── Add all Scout2 files and make first commit ───────────────
echo.
echo [4/5] Adding files and making first commit...
git add scout2_dump.json scout2_dump.txt scout2_fetcher_v3.py requirements.txt .gitignore
git commit -m "Initial Scout-2 setup"

:: ── Connect to GitHub and push ───────────────────────────────
echo.
echo [5/5] Connecting to GitHub and pushing...
echo.
echo NOTE: A browser window or credential prompt may open.
echo       Sign in with your GitHub account when asked.
echo.
git remote add origin https://github.com/StacheHistory/scout2-data.git
git push -u origin main

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Push failed. Most likely cause: authentication.
    echo.
    echo Fix: Go to https://github.com/settings/tokens
    echo      Generate a new token ^(classic^)
    echo      Scopes: check 'repo'
    echo      Copy the token
    echo      Re-run this script and paste token as password when prompted
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Setup complete. Your live URLs are:
echo.
echo  JSON:
echo  https://raw.githubusercontent.com/StacheHistory/scout2-data/main/scout2_dump.json
echo.
echo  TEXT:
echo  https://raw.githubusercontent.com/StacheHistory/scout2-data/main/scout2_dump.txt
echo.
echo  Now run run_scout2.bat to fetch and push data.
echo ============================================================
echo.
pause
