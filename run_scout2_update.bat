@echo off
:: ============================================================
::  Scout-2 Full Update Pipeline — Phase 2
::  Investing with SPACE System
::
::  Runs: fetcher → phase2 processor → git push → notify
::  Logs: logs\scout2_run_log.txt
:: ============================================================

cd C:\InvestingWithSPACE\Scout2

:: ── Setup log folder ─────────────────────────────────────────
if not exist logs mkdir logs
set LOGFILE=logs\scout2_run_log.txt
set TIMESTAMP=%DATE% %TIME%

echo. >> %LOGFILE%
echo ============================================================ >> %LOGFILE%
echo Scout-2 Run Start: %TIMESTAMP% >> %LOGFILE%
echo ============================================================ >> %LOGFILE%

:: ── Step 1: Run the RSS fetcher ───────────────────────────────
echo [1/5] Running Scout-2 RSS fetcher...
echo [1/5] Fetcher started: %TIME% >> %LOGFILE%

py scout2_fetcher_v3.py --days 3 >> %LOGFILE% 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Fetcher failed. Check logs\scout2_run_log.txt
    echo [ERROR] Fetcher failed at %TIME% >> %LOGFILE%
    goto notify_error
)
echo [OK] Fetcher complete >> %LOGFILE%

:: ── Step 2: Run Phase 2 processor ────────────────────────────
echo [2/5] Running Phase 2 processor...
echo [2/5] Phase 2 started: %TIME% >> %LOGFILE%

py scout2_phase2.py >> %LOGFILE% 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Phase 2 processor failed. Check logs\scout2_run_log.txt
    echo [ERROR] Phase 2 failed at %TIME% >> %LOGFILE%
    goto notify_error
)
echo [OK] Phase 2 complete >> %LOGFILE%

:: ── Step 3: Check for immediate alerts and notify ─────────────
echo [3/5] Checking for immediate alerts...
py scout2_notify.py >> %LOGFILE% 2>&1
echo [OK] Notifications checked >> %LOGFILE%

:: ── Step 4: Git add, commit, push ────────────────────────────
echo [4/5] Pushing to GitHub...
echo [4/5] Git push started: %TIME% >> %LOGFILE%

git add . >> %LOGFILE% 2>&1

:: Check if there is anything to commit
git diff --cached --quiet
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Nothing new to commit - data unchanged since last run.
    echo [INFO] Nothing to commit at %TIME% >> %LOGFILE%
    goto done
)

git commit -m "Scout-2 automated update %DATE% %TIME%" >> %LOGFILE% 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Git commit failed. Check logs.
    echo [ERROR] Git commit failed at %TIME% >> %LOGFILE%
    goto done
)

git push >> %LOGFILE% 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Git push failed. Check internet connection.
    echo [ERROR] Git push failed at %TIME% >> %LOGFILE%
    goto done
)

echo [OK] GitHub updated >> %LOGFILE%

:: ── Step 5: Write log summary ────────────────────────────────
echo [5/5] Writing run summary...

:done
echo [OK] Scout-2 run complete: %TIME% >> %LOGFILE%
echo Run complete: %TIMESTAMP%
goto end

:notify_error
echo [ERROR] Scout-2 run failed: %TIMESTAMP%
echo [ERROR] Run failed at: %TIME% >> %LOGFILE%
:: Show Windows desktop error notification
powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Scout-2 run FAILED at %TIME%. Check logs\scout2_run_log.txt', 'Scout-2 Error', 'OK', 'Error')" 2>nul

:end
echo ============================================================ >> %LOGFILE%
